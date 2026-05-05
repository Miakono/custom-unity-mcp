"""Tool for executing playbooks."""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


# Built-in playbook templates directory
BUILT_IN_PLAYBOOKS_DIR = Path(__file__).parent / "playbooks"


def _ensure_built_in_playbooks() -> None:
    try:
        from services.tools import create_playbook as cp_module

        cp_module._ensure_built_in_playbooks()
    except Exception:
        pass


def _find_playbook(name: str) -> tuple[dict[str, Any] | None, Path | None]:
    """Find a playbook by name."""
    _ensure_built_in_playbooks()

    # Check built-in first
    built_in_path = BUILT_IN_PLAYBOOKS_DIR / f"{name}.json"
    if built_in_path.exists():
        try:
            with open(built_in_path, "r", encoding="utf-8") as f:
                return json.load(f), built_in_path
        except (json.JSONDecodeError, IOError):
            pass

    # Check user playbooks
    from services.tools.list_pipelines import _get_pipelines_directories

    for pipelines_dir in _get_pipelines_directories():
        playbooks_subdir = pipelines_dir / "playbooks"
        user_path = playbooks_subdir / f"{name}.json"
        if user_path.exists():
            try:
                with open(user_path, "r", encoding="utf-8") as f:
                    return json.load(f), user_path
            except (json.JSONDecodeError, IOError):
                continue

    return None, None


# ---------------------------------------------------------------------------
# Playbook v2 templating engine
#
# Backwards-compatible with the v1 `{{param}}` syntax: any v1 playbook continues
# to work unchanged. New features layer on top:
#
#   - {{step_output.<name>.<json.path>}}  — pull from a captured step result
#   - {{prev.<json.path>}}                — same, but from the most recent step
#   - {{guid_of("Assets/Foo.prefab")}}    — registered helper functions
#   - per-step `when: "<expr>"`           — skip step if expr evaluates falsy
#   - per-step `for_each: "<param>"`      — repeat step over a list parameter
#   - per-step `output_as: "<name>"`      — capture result for later use
#
# Type-preservation: when a string value is *exactly* one `{{...}}` expression,
# the resolved value is inserted as its native type (int / dict / list) instead
# of being stringified — so `{ "value": "{{count}}" }` with count=5 produces
# `{ "value": 5 }` not `{ "value": "5" }`. Mixed strings still get stringified.
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class _PlaybookContext:
    """Bag of variables visible to the templating engine inside a playbook run."""

    def __init__(self, parameters: dict[str, Any]):
        self.parameters: dict[str, Any] = dict(parameters)
        # Captured step results keyed by `output_as` name. Values are the raw
        # response dict so playbooks can pull arbitrary nested fields.
        self.step_outputs: dict[str, Any] = {}
        # Most recent step result, regardless of whether it was named.
        self.prev: dict[str, Any] | None = None
        # Per-iteration locals (set inside for_each loops). Reset between iterations.
        self.locals: dict[str, Any] = {}

    def lookup(self, dotted_path: str) -> Any:
        """Resolve a dotted path against the context. Returns _NOT_FOUND on miss."""
        parts = dotted_path.split(".")
        head, *tail = parts

        if head == "step_output" or head == "steps":
            if not tail:
                return self.step_outputs
            name, *rest = tail
            current = self.step_outputs.get(name, _NOT_FOUND)
            return _walk(current, rest)
        if head == "prev":
            if self.prev is None:
                return _NOT_FOUND
            return _walk(self.prev, tail)
        if head in self.locals:
            return _walk(self.locals[head], tail)
        if head in self.parameters:
            return _walk(self.parameters[head], tail)
        return _NOT_FOUND


_NOT_FOUND = object()


def _walk(obj: Any, path_parts: list[str]) -> Any:
    cur = obj
    for part in path_parts:
        if cur is _NOT_FOUND or cur is None:
            return _NOT_FOUND
        if isinstance(cur, dict):
            if part in cur:
                cur = cur[part]
                continue
            return _NOT_FOUND
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
                continue
            except (ValueError, IndexError):
                return _NOT_FOUND
        # Attribute fallback for objects (rare in dict-based responses)
        if hasattr(cur, part):
            cur = getattr(cur, part)
            continue
        return _NOT_FOUND
    return cur


# Registered helper functions, callable as `{{name(arg)}}`. Each receives a
# single string argument (literal). Keep these intentionally narrow — the
# templating engine is not a general-purpose evaluator.
def _helper_guid_of(asset_path: str) -> str:
    """Return the GUID of an asset by path, or empty string if not found.

    Resolved at the *server* side rather than Unity-side because this runs
    during playbook templating, before any tool dispatch. Most projects keep
    the .meta files in sync with their git checkout, so we read the GUID
    directly from <asset_path>.meta.
    """
    try:
        meta = Path(asset_path + ".meta")
        if not meta.exists():
            return ""
        for line in meta.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("guid:"):
                return stripped.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""


_HELPERS: dict[str, callable] = {
    "guid_of": _helper_guid_of,
}


_FUNC_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(\s*\"([^\"]*)\"\s*\)$")


def _evaluate_expression(expr: str, ctx: _PlaybookContext) -> Any:
    """Evaluate a single template expression: identifier, dotted path, or helper(\"arg\").

    Returns the resolved value or the original expression text on miss (so the
    user sees `{{whatever}}` literal in the output and can debug it).
    """
    expr = expr.strip()

    # Helper function call?
    match = _FUNC_CALL_RE.match(expr)
    if match:
        fn_name, arg = match.group(1), match.group(2)
        helper = _HELPERS.get(fn_name)
        if helper is None:
            return f"{{{{{expr}}}}}"  # unknown helper; pass through
        try:
            return helper(arg)
        except Exception as e:
            return f"<{fn_name}() error: {e}>"

    # Dotted path / bare identifier
    value = ctx.lookup(expr)
    if value is _NOT_FOUND:
        return f"{{{{{expr}}}}}"
    return value


def _evaluate_template(value: Any, ctx: _PlaybookContext) -> Any:
    """Recursively substitute `{{expr}}` placeholders inside any JSON-shaped value."""
    if isinstance(value, str):
        # Check for a "whole-string is a single expression" case so we can preserve
        # the resolved value's native type (int / dict / list / None).
        match = _PLACEHOLDER_RE.fullmatch(value)
        if match is not None:
            return _evaluate_expression(match.group(1), ctx)

        # Otherwise, do in-place substitution and stringify the resolved values.
        def _replace(m: re.Match[str]) -> str:
            resolved = _evaluate_expression(m.group(1), ctx)
            if isinstance(resolved, (dict, list)):
                return json.dumps(resolved)
            return "" if resolved is None else str(resolved)

        return _PLACEHOLDER_RE.sub(_replace, value)

    if isinstance(value, list):
        return [_evaluate_template(item, ctx) for item in value]
    if isinstance(value, dict):
        return {k: _evaluate_template(v, ctx) for k, v in value.items()}
    return value


_WHEN_OP_RE = re.compile(r"^\s*(.+?)\s*(==|!=)\s*(.+?)\s*$")


def _coerce_for_comparison(value: Any) -> Any:
    """Best-effort string→typed coercion so `{{count}} == 5` works regardless of whether
    `count` resolves to int 5 or string "5". Coerces only string inputs; non-strings pass through.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() in ("null", "none"):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _evaluate_when(expr: str, ctx: _PlaybookContext) -> bool:
    """Evaluate a `when:` condition. Supports a single comparison or a truthy expression."""
    if not expr or not isinstance(expr, str):
        return True

    op_match = _WHEN_OP_RE.match(expr)
    if op_match:
        lhs_text, op, rhs_text = op_match.group(1), op_match.group(2), op_match.group(3)
        lhs = _coerce_for_comparison(_evaluate_template(lhs_text, ctx))
        rhs = _coerce_for_comparison(_evaluate_template(rhs_text, ctx))
        return (lhs == rhs) if op == "==" else (lhs != rhs)

    # Truthy evaluation
    resolved = _evaluate_template(expr, ctx)
    if isinstance(resolved, str) and _PLACEHOLDER_RE.fullmatch(expr.strip()) is not None:
        # Unresolved placeholder — treat as falsy so missing data short-circuits cleanly.
        if resolved.startswith("{{") and resolved.endswith("}}"):
            return False
    return bool(resolved)


def _build_initial_parameters(
    playbook_params: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    effective: dict[str, Any] = {}
    if playbook_params:
        for key, param_def in playbook_params.items():
            if isinstance(param_def, dict):
                effective[key] = param_def.get("default")
            else:
                effective[key] = param_def
    if overrides:
        effective.update(overrides)
    return effective


# Kept for backwards compatibility: any external caller importing this name still
# gets the v1 behaviour (literal {{param}} substitution).
def _apply_parameter_overrides(
    steps: list[dict[str, Any]],
    parameters: dict[str, Any] | None,
    playbook_params: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    effective_params = _build_initial_parameters(playbook_params, parameters)
    ctx = _PlaybookContext(effective_params)
    return _evaluate_template(copy.deepcopy(steps), ctx)


@mcp_for_unity_tool(
    name="run_playbook",
    unity_target=None,
    description=(
        "Execute a playbook (reusable template for Unity workflows). "
        "Playbooks contain predefined steps that automate common tasks. "
        "Built-in playbooks: basic_player_controller, ui_canvas_setup, scene_lighting_setup. "
        "Supports parameter overrides for customization. "
        "v2 features: per-step `when` (skip on condition), `for_each` (loop over an array), "
        "`output_as` (capture step result), and `{{step_output.NAME.path}}` / `{{guid_of('...')}}` templating."
    ),
    annotations=ToolAnnotations(
        title="Run Playbook",
        destructiveHint=True,
    ),
    group="pipeline",
)
async def run_playbook(
    ctx: Context,
    playbook_id: Annotated[str, "ID/name of the playbook to execute"],
    context: Annotated[dict[str, Any] | None, "Context variables and parameter overrides"] = None,
    dry_run: Annotated[bool, "Preview playbook without executing"] = False,
    stop_on_error: Annotated[bool, "Stop execution if a step fails"] = True,
) -> dict[str, Any]:
    """Execute a playbook."""
    try:
        # Find the playbook
        playbook_data, file_path = _find_playbook(playbook_id)

        if not playbook_data:
            return {
                "success": False,
                "message": f"Playbook '{playbook_id}' not found. Use list_playbooks to see available playbooks.",
            }

        metadata = playbook_data.get("metadata", {})
        steps = playbook_data.get("steps", [])
        playbook_params = playbook_data.get("parameters", {})

        if not steps:
            return {
                "success": False,
                "message": f"Playbook '{playbook_id}' has no steps",
            }

        # Get parameter overrides from context
        parameters = context.get("parameters", {}) if context else None
        effective_params = _build_initial_parameters(playbook_params, parameters)
        playbook_ctx = _PlaybookContext(effective_params)

        # Dry run - just return what would be executed (with substitution applied so
        # the operator can see the literal payloads).
        if dry_run:
            previewed = []
            for i, step in enumerate(steps):
                rendered = _evaluate_template(copy.deepcopy(step), playbook_ctx)
                previewed.append({
                    "step": i + 1,
                    "tool": rendered.get("tool"),
                    "action": rendered.get("action"),
                    "when": rendered.get("when"),
                    "for_each": rendered.get("for_each"),
                    "output_as": rendered.get("output_as"),
                    "params_preview": list(rendered.get("params", {}).keys()) if rendered.get("params") else None,
                })
            return {
                "success": True,
                "message": f"Playbook '{playbook_id}' dry run - would execute {len(steps)} step(s)",
                "playbook_name": metadata.get("name", playbook_id),
                "description": metadata.get("description"),
                "steps_preview": previewed,
                "parameter_overrides": parameters,
                "available_parameters": list(playbook_params.keys()) if playbook_params else None,
            }

        unity_instance = await get_unity_instance_from_context(ctx)

        results: list[dict[str, Any]] = []
        executed = 0
        failed = 0
        skipped = 0
        stopped_early = False

        for i, raw_step in enumerate(steps):
            step_num = i + 1
            for_each_expr = raw_step.get("for_each")

            # Resolve the iteration list (or [None] for non-loop steps).
            if for_each_expr is not None:
                # Evaluate ONLY the for_each expression first, against the parent ctx.
                resolved_iter = _evaluate_template(for_each_expr, playbook_ctx)
                if not isinstance(resolved_iter, list):
                    results.append({
                        "step": step_num,
                        "tool": raw_step.get("tool"),
                        "success": False,
                        "error": f"for_each '{for_each_expr}' did not resolve to a list (got {type(resolved_iter).__name__}).",
                    })
                    failed += 1
                    if stop_on_error:
                        stopped_early = True
                        break
                    continue
                iteration_items = list(enumerate(resolved_iter))
            else:
                iteration_items = [(0, None)]

            step_iteration_results: list[dict[str, Any]] = []
            step_failed = False

            for index, item in iteration_items:
                if for_each_expr is not None:
                    playbook_ctx.locals = {"item": item, "index": index}
                else:
                    playbook_ctx.locals = {}

                # Substitute templates in the step body using current context.
                rendered = _evaluate_template(copy.deepcopy(raw_step), playbook_ctx)

                # Honour `when`.
                when_expr = rendered.get("when")
                if when_expr is not None:
                    if not _evaluate_when(when_expr, playbook_ctx):
                        skipped += 1
                        step_iteration_results.append({
                            "iteration": index if for_each_expr is not None else None,
                            "skipped": True,
                            "reason": f"when='{when_expr}' evaluated false",
                        })
                        continue

                tool_name = rendered.get("tool")
                action = rendered.get("action")
                step_params = rendered.get("params", {}) or {}
                if not tool_name:
                    step_iteration_results.append({
                        "iteration": index if for_each_expr is not None else None,
                        "success": False,
                        "error": "Step has no 'tool' field.",
                    })
                    step_failed = True
                    if stop_on_error:
                        break
                    continue

                payload = {"action": action, **step_params} if action else step_params

                try:
                    response = await send_with_unity_instance(
                        async_send_command_with_retry,
                        unity_instance,
                        tool_name,
                        payload,
                    )
                    success = isinstance(response, dict) and response.get("success", True)
                    response_dict = response if isinstance(response, dict) else {"data": str(response)}

                    step_iteration_results.append({
                        "iteration": index if for_each_expr is not None else None,
                        "tool": tool_name,
                        "success": success,
                        "response": response_dict,
                    })

                    # Capture into context regardless of success — the next step might
                    # legitimately want to inspect a failure response.
                    playbook_ctx.prev = response_dict
                    output_as = rendered.get("output_as")
                    if isinstance(output_as, str) and output_as:
                        playbook_ctx.step_outputs[output_as] = response_dict

                    if not success:
                        step_failed = True
                        if stop_on_error:
                            break

                except Exception as e:
                    step_iteration_results.append({
                        "iteration": index if for_each_expr is not None else None,
                        "tool": tool_name,
                        "success": False,
                        "error": str(e),
                    })
                    step_failed = True
                    if stop_on_error:
                        break

            # Reset per-iteration locals after the step completes.
            playbook_ctx.locals = {}

            executed += 1
            if step_failed:
                failed += 1

            results.append({
                "step": step_num,
                "tool": raw_step.get("tool"),
                "for_each": for_each_expr,
                "iterations": step_iteration_results,
                "success": not step_failed,
            })

            if step_failed and stop_on_error:
                stopped_early = True
                break

        return {
            "success": failed == 0,
            "message": f"Playbook '{playbook_id}' execution complete: {executed} executed, {failed} failed, {skipped} skipped",
            "executed_steps": executed,
            "failed_steps": failed,
            "skipped_steps": skipped,
            "total_steps": len(steps),
            "stopped_early": stopped_early,
            "results": results,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to run playbook: {str(e)}",
        }
