"""
Manage project memory and rules for Unity MCP.

This tool provides project-specific conventions, naming rules, and validation
guidelines stored in a rules file (.unity-mcp-rules or UnityMCPRules.md).

Actions:
- load_rules: Load project rules from file
- save_rules: Save rules to file
- summarize_conventions: Get summary of working conventions
- get_active_rules: Get currently active rules by category
- validate_against_rules: Check content against rules (advisory)
"""
from typing import Annotated, Any, Literal
from pathlib import Path
import re

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from services.registry import mcp_for_unity_tool
from services.tools import get_unity_instance_from_context
from transport.unity_transport import send_with_unity_instance
from transport.legacy.unity_connection import async_send_command_with_retry


# Default rules file names
DEFAULT_RULES_FILENAME = ".unity-mcp-rules"
ALT_RULES_FILENAME = "UnityMCPRules.md"


class ProjectRules(BaseModel):
    """Schema for project rules."""
    version: str = "1.0"
    naming_conventions: dict[str, str] = {}
    scene_organization: list[str] = []
    code_style: list[str] = []
    validation_rules: list[str] = []
    custom_rules: dict[str, Any] = {}


def _get_default_rules_content() -> str:
    """Return the default rules file content."""
    return """# Unity MCP Project Rules

## Naming Conventions
- Prefabs: PascalCase with "Prefab" suffix (e.g., "PlayerPrefab")
- Scripts: PascalCase, noun-first (e.g., "PlayerController")
- Materials: Category_Purpose (e.g., "Env_Grass", "Char_Skin")
- Textures: Type_Description_Size (e.g., "Tex_Grass_512")
- Animations: Action_Layer (e.g., "Run_Layer1", "Attack_Base")

## Scene Organization
- Use empty GameObjects as folders (e.g., "Environment", "Lighting", "UI")
- Main camera at origin or designated position
- Lights in "Lighting" folder
- UI elements in "UI" folder with Canvas as parent
- Keep hierarchy depth reasonable (max 5-6 levels)

## Code Style
- Use [SerializeField] for inspector fields instead of public
- Avoid FindObjectOfType in Update - cache in Awake/Start
- Cache component references in private fields
- Use PascalCase for public methods, camelCase for private
- Add XML documentation for public APIs

## Validation Rules
- No missing script references on GameObjects
- All materials should be assigned
- No unnamed GameObjects (should have descriptive names)
- No duplicate GameObject names at same hierarchy level
- Check for unused using statements
- Ensure all scenes in build settings exist

## Custom Rules
Add your project-specific rules here.
"""


def _parse_rules_file(content: str) -> ProjectRules:
    """Parse rules from markdown content."""
    rules = ProjectRules()
    
    # Extract naming conventions
    naming_match = re.search(
        r'##\s*Naming Conventions(.*?)##', content, re.DOTALL | re.IGNORECASE
    )
    if naming_match:
        section = naming_match.group(1)
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                # Remove bullet and extract key-value
                clean = line[1:].strip()
                if ':' in clean:
                    key, val = clean.split(':', 1)
                    rules.naming_conventions[key.strip()] = val.strip()
    
    # Extract scene organization
    org_match = re.search(
        r'##\s*Scene Organization(.*?)##', content, re.DOTALL | re.IGNORECASE
    )
    if org_match:
        section = org_match.group(1)
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                rules.scene_organization.append(line[1:].strip())
    
    # Extract code style
    code_match = re.search(
        r'##\s*Code Style(.*?)##', content, re.DOTALL | re.IGNORECASE
    )
    if code_match:
        section = code_match.group(1)
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                rules.code_style.append(line[1:].strip())
    
    # Extract validation rules
    val_match = re.search(
        r'##\s*Validation Rules(.*?)(?:##|$)', content, re.DOTALL | re.IGNORECASE
    )
    if val_match:
        section = val_match.group(1)
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                rules.validation_rules.append(line[1:].strip())
    
    return rules


def _rules_to_markdown(rules: ProjectRules) -> str:
    """Convert rules to markdown format."""
    lines = ["# Unity MCP Project Rules\n"]
    
    lines.append("## Naming Conventions")
    if rules.naming_conventions:
        for key, val in rules.naming_conventions.items():
            lines.append(f"- {key}: {val}")
    else:
        lines.append("- Prefabs: PascalCase with \"Prefab\" suffix")
        lines.append("- Scripts: PascalCase, noun-first")
        lines.append("- Materials: Category_Purpose")
    lines.append("")
    
    lines.append("## Scene Organization")
    if rules.scene_organization:
        for item in rules.scene_organization:
            lines.append(f"- {item}")
    else:
        lines.append("- Use empty GameObjects as folders")
        lines.append("- Main camera at origin")
        lines.append("- Lights in \"Lighting\" folder")
    lines.append("")
    
    lines.append("## Code Style")
    if rules.code_style:
        for item in rules.code_style:
            lines.append(f"- {item}")
    else:
        lines.append("- Use [SerializeField] for inspector fields")
        lines.append("- Avoid FindObjectOfType in Update")
        lines.append("- Cache component references")
    lines.append("")
    
    lines.append("## Validation Rules")
    if rules.validation_rules:
        for item in rules.validation_rules:
            lines.append(f"- {item}")
    else:
        lines.append("- No missing script references")
        lines.append("- All materials assigned")
        lines.append("- No unnamed GameObjects")
    lines.append("")
    
    if rules.custom_rules:
        lines.append("## Custom Rules")
        for key, val in rules.custom_rules.items():
            if isinstance(val, list):
                lines.append(f"- {key}:")
                for v in val:
                    lines.append(f"  - {v}")
            else:
                lines.append(f"- {key}: {val}")
    
    return "\n".join(lines)


async def _get_project_root(unity_instance: str | None) -> str | None:
    """Get the project root path from Unity."""
    try:
        response = await send_with_unity_instance(
            async_send_command_with_retry,
            unity_instance,
            "get_project_info",
            {},
        )
        if isinstance(response, dict) and response.get("success"):
            data = response.get("data", {})
            return data.get("projectRoot")
        return None
    except Exception:
        return None


def _find_rules_file(project_root: str) -> Path | None:
    """Find the rules file in project root."""
    root = Path(project_root)
    
    # Check for default filename first
    rules_path = root / DEFAULT_RULES_FILENAME
    if rules_path.exists():
        return rules_path
    
    # Check alternative filename
    alt_path = root / ALT_RULES_FILENAME
    if alt_path.exists():
        return alt_path
    
    return None


def _get_rules_path(project_root: str, custom_path: str | None = None) -> Path:
    """Get the path for rules file."""
    root = Path(project_root)
    
    if custom_path:
        # If relative, resolve against project root
        path = Path(custom_path)
        if not path.is_absolute():
            path = root / path
        return path
    
    # Default to hidden file
    return root / DEFAULT_RULES_FILENAME


@mcp_for_unity_tool(
    unity_target=None,
    group="project_config",
    description=(
        "Manage project memory and rules for Unity MCP. "
        "Actions: load_rules (read rules file), save_rules (write rules), "
        "summarize_conventions (get conventions summary), get_active_rules (rules by category), "
        "validate_against_rules (check content - advisory only). "
        "Rules stored in .unity-mcp-rules or UnityMCPRules.md in project root."
    ),
    annotations=ToolAnnotations(
        title="Manage Project Memory",
        readOnlyHint=False,
    ),
)
async def manage_project_memory(
    ctx: Context,
    action: Annotated[
        Literal["load_rules", "save_rules", "summarize_conventions", "get_active_rules", "validate_against_rules"],
        "Action to perform: load_rules, save_rules, summarize_conventions, get_active_rules, validate_against_rules"
    ],
    path: Annotated[
        str | None,
        "Path to rules file (optional, uses default .unity-mcp-rules if not specified)"
    ] = None,
    rules: Annotated[
        dict[str, Any] | None,
        "Rules content for save_rules action (naming_conventions, scene_organization, code_style, validation_rules, custom_rules)"
    ] = None,
    format: Annotated[
        Literal["markdown", "json", "yaml"],
        "Output format for summarize_conventions (default: markdown)"
    ] = "markdown",
    category: Annotated[
        Literal["naming", "organization", "code_style", "validation", "all"],
        "Category filter for get_active_rules"
    ] = "all",
    content_type: Annotated[
        Literal["script", "prefab", "scene", "asset"],
        "Content type for validate_against_rules"
    ] | None = None,
    content_path: Annotated[
        str | None,
        "Path to content for validate_against_rules"
    ] = None,
) -> dict[str, Any]:
    """
    Manage project memory and rules for Unity MCP.
    
    This tool provides project-specific conventions, naming rules, and validation
    guidelines. Rules are stored in a markdown file (.unity-mcp-rules or 
    UnityMCPRules.md) in the project root.
    
    Examples:
    - Load rules: action="load_rules"
    - Save rules: action="save_rules", rules={"naming_conventions": {"Prefabs": "PascalCase"}}
    - Get conventions summary: action="summarize_conventions", format="json"
    - Get rules by category: action="get_active_rules", category="naming"
    """
    unity_instance = await get_unity_instance_from_context(ctx)
    
    # Get project root from Unity
    project_root = await _get_project_root(unity_instance)
    if not project_root:
        return {
            "success": False,
            "message": "Could not determine project root. Is Unity running?"
        }
    
    try:
        if action == "load_rules":
            return await _load_rules(project_root, path)
        
        elif action == "save_rules":
            return await _save_rules(project_root, path, rules)
        
        elif action == "summarize_conventions":
            return await _summarize_conventions(project_root, path, format)
        
        elif action == "get_active_rules":
            return await _get_active_rules(project_root, path, category)
        
        elif action == "validate_against_rules":
            return await _validate_against_rules(project_root, path, content_type, content_path)
        
        else:
            return {"success": False, "message": f"Unknown action: {action}"}
            
    except Exception as e:
        return {"success": False, "message": f"Error managing project memory: {e!s}"}


async def _load_rules(project_root: str, custom_path: str | None = None) -> dict[str, Any]:
    """Load rules from file."""
    if custom_path:
        rules_path = _get_rules_path(project_root, custom_path)
    else:
        rules_path = _find_rules_file(project_root)
    
    if not rules_path or not rules_path.exists():
        # Return default rules
        return {
            "success": True,
            "message": "No rules file found. Returning default rules.",
            "data": {
                "rules": _parse_rules_file(_get_default_rules_content()).model_dump(),
                "source": "default",
                "path": str(_get_rules_path(project_root, custom_path))
            }
        }
    
    try:
        content = rules_path.read_text(encoding="utf-8")
        rules = _parse_rules_file(content)
        
        return {
            "success": True,
            "message": f"Rules loaded from {rules_path.name}",
            "data": {
                "rules": rules.model_dump(),
                "source": str(rules_path),
                "path": str(rules_path)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to load rules: {e!s}"
        }


async def _save_rules(
    project_root: str, 
    custom_path: str | None = None,
    rules_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Save rules to file."""
    rules_path = _get_rules_path(project_root, custom_path)
    
    try:
        # Create rules from provided data or use defaults
        if rules_data:
            rules = ProjectRules(**rules_data)
        else:
            rules = _parse_rules_file(_get_default_rules_content())
        
        content = _rules_to_markdown(rules)
        
        # Ensure parent directory exists
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        
        rules_path.write_text(content, encoding="utf-8")
        
        return {
            "success": True,
            "message": f"Rules saved to {rules_path.name}",
            "data": {
                "path": str(rules_path),
                "rules": rules.model_dump()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to save rules: {e!s}"
        }


async def _summarize_conventions(
    project_root: str, 
    custom_path: str | None = None,
    fmt: str = "markdown"
) -> dict[str, Any]:
    """Get a summary of working conventions."""
    result = await _load_rules(project_root, custom_path)
    
    if not result.get("success"):
        return result
    
    rules = ProjectRules(**result["data"]["rules"])
    
    if fmt == "json":
        return {
            "success": True,
            "message": "Conventions summary",
            "data": {
                "naming_conventions": rules.naming_conventions,
                "scene_organization": rules.scene_organization,
                "code_style": rules.code_style
            }
        }
    elif fmt == "yaml":
        lines = ["naming_conventions:"]
        for k, v in rules.naming_conventions.items():
            lines.append(f"  {k}: {v}")
        lines.append("scene_organization:")
        for item in rules.scene_organization:
            lines.append(f"  - {item}")
        lines.append("code_style:")
        for item in rules.code_style:
            lines.append(f"  - {item}")
        
        return {
            "success": True,
            "message": "Conventions summary (YAML)",
            "data": {"yaml": "\n".join(lines)}
        }
    else:
        # Markdown format
        lines = ["# Project Conventions Summary\n"]
        
        lines.append("## Naming Conventions")
        for k, v in rules.naming_conventions.items():
            lines.append(f"- **{k}**: {v}")
        if not rules.naming_conventions:
            lines.append("*No naming conventions defined*")
        lines.append("")
        
        lines.append("## Scene Organization")
        for item in rules.scene_organization:
            lines.append(f"- {item}")
        if not rules.scene_organization:
            lines.append("*No scene organization rules defined*")
        lines.append("")
        
        lines.append("## Code Style")
        for item in rules.code_style:
            lines.append(f"- {item}")
        if not rules.code_style:
            lines.append("*No code style rules defined*")
        
        return {
            "success": True,
            "message": "Conventions summary",
            "data": {"markdown": "\n".join(lines)}
        }


async def _get_active_rules(
    project_root: str, 
    custom_path: str | None = None,
    category: str = "all"
) -> dict[str, Any]:
    """Get currently active rules by category."""
    result = await _load_rules(project_root, custom_path)
    
    if not result.get("success"):
        return result
    
    rules = ProjectRules(**result["data"]["rules"])
    
    data = {}
    if category in ("naming", "all"):
        data["naming"] = rules.naming_conventions
    if category in ("organization", "all"):
        data["organization"] = rules.scene_organization
    if category in ("code_style", "all"):
        data["code_style"] = rules.code_style
    if category in ("validation", "all"):
        data["validation"] = rules.validation_rules
    
    return {
        "success": True,
        "message": f"Active rules for category: {category}",
        "data": {
            "category": category,
            "rules": data,
            "source": result["data"].get("source")
        }
    }


async def _validate_against_rules(
    project_root: str,
    custom_path: str | None = None,
    content_type: str | None = None,
    content_path: str | None = None
) -> dict[str, Any]:
    """
    Validate content against rules (advisory only).
    
    This performs basic validation checks based on the rules file.
    Results are advisory and not enforced.
    """
    result = await _load_rules(project_root, custom_path)
    
    if not result.get("success"):
        return result
    
    rules = ProjectRules(**result["data"]["rules"])
    issues = []
    suggestions = []
    
    # Basic validation based on content type
    if content_type == "script":
        # Check naming conventions for scripts
        if content_path:
            name = Path(content_path).stem
            if "Scripts" in rules.naming_conventions:
                conv = rules.naming_conventions["Scripts"]
                if "PascalCase" in conv and not name[0].isupper():
                    issues.append(f"Script name '{name}' should use PascalCase")
            
            # Check for common code style issues in file
            try:
                full_path = Path(project_root) / "Assets" / content_path
                if full_path.exists():
                    content = full_path.read_text(encoding="utf-8")
                    
                    # Check for FindObjectOfType in Update
                    if "FindObjectOfType" in content and "Update()" in content:
                        if any("FindObjectOfType" in rule for rule in rules.code_style):
                            suggestions.append("Consider caching FindObjectOfType results instead of calling in Update")
                    
                    # Check for public fields (should use SerializeField)
                    public_fields = re.findall(r'public\s+\w+\s+(\w+)\s*[=;]', content)
                    if public_fields and any("SerializeField" in rule for rule in rules.code_style):
                        suggestions.append(f"Consider using [SerializeField] private fields instead of public: {public_fields[:3]}")
            except Exception:
                pass
    
    elif content_type == "prefab" or content_type == "scene":
        # These would need Unity-side validation for full checks
        suggestions.append(f"For {content_type} validation, consider using Unity's built-in validation")
    
    elif content_type == "asset":
        # Check naming conventions
        if content_path:
            name = Path(content_path).stem
            for asset_type, convention in rules.naming_conventions.items():
                if asset_type.lower() in content_type.lower():
                    if "PascalCase" in convention and name[0].islower():
                        suggestions.append(f"{asset_type} '{name}' might use PascalCase per project conventions")
    
    # Build response
    response_data = {
        "content_type": content_type,
        "content_path": content_path,
        "validation_passed": len(issues) == 0,
        "issues": issues,
        "suggestions": suggestions,
        "rules_applied": list(rules.naming_conventions.keys()) if rules.naming_conventions else [],
        "note": "Validation is advisory only. Rules are not enforced."
    }
    
    return {
        "success": True,
        "message": "Validation complete" if not issues else f"Found {len(issues)} issues",
        "data": response_data
    }
