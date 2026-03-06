from pathlib import Path


def test_tool_modules_do_not_call_preflight_directly():
    tools_dir = Path(__file__).resolve().parents[1] / "src" / "services" / "tools"
    offenders: list[str] = []

    for path in tools_dir.rglob("*.py"):
        if path.name in {"action_policy.py", "preflight.py"}:
            continue

        text = path.read_text(encoding="utf-8")
        if "from services.tools.preflight import preflight" in text:
            offenders.append(str(path.relative_to(tools_dir.parent.parent.parent)))
            continue
        if "await preflight(" in text:
            offenders.append(str(path.relative_to(tools_dir.parent.parent.parent)))

    assert offenders == [], f"Direct preflight usage found: {offenders}"
