"""
Helper service for Unity Input System management.

Provides functionality to:
- Parse and modify Input Action asset files (YAML format)
- Track input state
- Manage action maps, actions, bindings, and control schemes
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

logger = logging.getLogger("mcp-for-unity-server")


@dataclass
class InputBinding:
    """Represents an input binding."""
    name: str
    path: str
    interactions: str = ""
    processors: str = ""
    groups: str = ""
    action: str = ""
    is_composite: bool = False
    is_part_of_composite: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "interactions": self.interactions,
            "processors": self.processors,
            "groups": self.groups,
            "action": self.action,
            "isComposite": self.is_composite,
            "isPartOfComposite": self.is_part_of_composite,
        }


@dataclass
class InputAction:
    """Represents an input action."""
    name: str
    type: str = "Button"  # Button, Value, PassThrough
    id: str = ""
    expected_control_type: str = ""
    processors: str = ""
    interactions: str = ""
    bindings: list[InputBinding] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "id": self.id,
            "expectedControlType": self.expected_control_type,
            "processors": self.processors,
            "interactions": self.interactions,
            "bindings": [b.to_dict() for b in self.bindings],
        }


@dataclass
class ActionMap:
    """Represents an action map."""
    name: str
    id: str = ""
    actions: list[InputAction] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "actions": [a.to_dict() for a in self.actions],
        }


@dataclass
class ControlScheme:
    """Represents a control scheme."""
    name: str
    binding_group: str = ""
    devices: list[dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "bindingGroup": self.binding_group,
            "devices": self.devices,
        }


@dataclass
class InputActionAsset:
    """Represents an Input Action Asset file."""
    name: str
    file_path: Path
    action_maps: list[ActionMap] = field(default_factory=list)
    control_schemes: list[ControlScheme] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "filePath": str(self.file_path),
            "actionMaps": [m.to_dict() for m in self.action_maps],
            "controlSchemes": [c.to_dict() for c in self.control_schemes],
        }


class InputSystemHelper:
    """Helper class for managing Unity Input System assets."""
    
    # Valid action types
    ACTION_TYPES = {"Button", "Value", "PassThrough"}
    
    # Valid value types for actions
    VALUE_TYPES = {
        "Axis", "Button", "Vector2", "Vector3", "Quaternion",
        "Integer", "Float", "Touch", "Color", "Bone", "Eyes", "Pose"
    }
    
    def __init__(self, project_root: Path | str | None = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self._cached_assets: dict[str, InputActionAsset] = {}
    
    def find_input_assets(self, assets_folder: str = "Assets") -> list[dict[str, str]]:
        """Find all .inputactions files in the project."""
        assets_path = self.project_root / assets_folder
        if not assets_path.exists():
            logger.warning(f"Assets folder not found: {assets_path}")
            return []
        
        assets = []
        for file_path in assets_path.rglob("*.inputactions"):
            assets.append({
                "name": file_path.stem,
                "path": str(file_path.relative_to(self.project_root)).replace("\\", "/"),
                "fullPath": str(file_path),
            })
        
        return assets
    
    def parse_input_asset(self, file_path: str | Path) -> InputActionAsset | None:
        """Parse an Input Action asset file."""
        path = Path(file_path)
        if not path.is_absolute():
            path = self.project_root / path
        
        if not path.exists():
            logger.error(f"Input asset file not found: {path}")
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Parse YAML
            data = yaml.safe_load(content)
            
            asset = InputActionAsset(
                name=path.stem,
                file_path=path,
            )
            
            # Parse action maps
            maps_data = data.get("m_ActionMaps", [])
            for map_data in maps_data:
                action_map = self._parse_action_map(map_data)
                asset.action_maps.append(action_map)
            
            # Parse control schemes
            schemes_data = data.get("m_ControlSchemes", [])
            for scheme_data in schemes_data:
                control_scheme = self._parse_control_scheme(scheme_data)
                asset.control_schemes.append(control_scheme)
            
            # Cache the parsed asset
            self._cached_assets[str(path)] = asset
            
            return asset
            
        except Exception as e:
            logger.error(f"Failed to parse input asset {path}: {e}")
            return None
    
    def _parse_action_map(self, data: dict[str, Any]) -> ActionMap:
        """Parse an action map from YAML data."""
        action_map = ActionMap(
            name=data.get("m_Name", ""),
            id=data.get("m_Id", ""),
        )
        
        # Parse actions
        actions_data = data.get("m_Actions", [])
        for action_data in actions_data:
            action = self._parse_action(action_data)
            action_map.actions.append(action)
        
        # Parse bindings
        bindings_data = data.get("m_Bindings", [])
        for binding_data in bindings_data:
            binding = self._parse_binding(binding_data)
            # Associate binding with action
            if binding.action:
                for action in action_map.actions:
                    if action.id == binding.action or action.name == binding.action:
                        action.bindings.append(binding)
                        break
        
        return action_map
    
    def _parse_action(self, data: dict[str, Any]) -> InputAction:
        """Parse an action from YAML data."""
        return InputAction(
            name=data.get("m_Name", ""),
            type=data.get("m_Type", "Button"),
            id=data.get("m_Id", ""),
            expected_control_type=data.get("m_ExpectedControlType", ""),
            processors=data.get("m_Processors", ""),
            interactions=data.get("m_Interactions", ""),
        )
    
    def _parse_binding(self, data: dict[str, Any]) -> InputBinding:
        """Parse a binding from YAML data."""
        return InputBinding(
            name=data.get("m_Name", ""),
            path=data.get("m_Path", ""),
            interactions=data.get("m_Interactions", ""),
            processors=data.get("m_Processors", ""),
            groups=data.get("m_Groups", ""),
            action=data.get("m_Action", ""),
            is_composite=data.get("m_Flags", 0) & 1 != 0,  # Composite bit flag
            is_part_of_composite=data.get("m_Flags", 0) & 2 != 0,  # PartOfComposite bit flag
        )
    
    def _parse_control_scheme(self, data: dict[str, Any]) -> ControlScheme:
        """Parse a control scheme from YAML data."""
        scheme = ControlScheme(
            name=data.get("m_Name", ""),
            binding_group=data.get("m_BindingGroup", ""),
        )
        
        devices_data = data.get("m_DeviceRequirements", [])
        for device_data in devices_data:
            scheme.devices.append({
                "devicePath": device_data.get("m_ControlPath", ""),
                "isOptional": str(device_data.get("m_Flags", 0) & 1 != 0).lower(),
            })
        
        return scheme
    
    def get_action_map(self, asset_path: str, map_name: str) -> ActionMap | None:
        """Get a specific action map from an asset."""
        asset = self._get_cached_or_parse(asset_path)
        if not asset:
            return None
        
        for map in asset.action_maps:
            if map.name == map_name:
                return map
        
        return None
    
    def get_action(self, asset_path: str, map_name: str, action_name: str) -> InputAction | None:
        """Get a specific action from an asset."""
        action_map = self.get_action_map(asset_path, map_name)
        if not action_map:
            return None
        
        for action in action_map.actions:
            if action.name == action_name:
                return action
        
        return None
    
    def _get_cached_or_parse(self, asset_path: str) -> InputActionAsset | None:
        """Get cached asset or parse if not cached."""
        path = str(Path(asset_path))
        if path in self._cached_assets:
            return self._cached_assets[path]
        
        return self.parse_input_asset(asset_path)
    
    def create_action_map_yaml(self, name: str) -> dict[str, Any]:
        """Create a new action map structure."""
        import uuid
        return {
            "m_Name": name,
            "m_Id": str(uuid.uuid4()),
            "m_Actions": [],
            "m_Bindings": [],
        }
    
    def create_action_yaml(self, name: str, action_type: str, expected_control_type: str = "") -> dict[str, Any]:
        """Create a new action structure."""
        import uuid
        return {
            "m_Name": name,
            "m_Type": action_type,
            "m_ExpectedControlType": expected_control_type,
            "m_Id": str(uuid.uuid4()),
            "m_Processors": "",
            "m_Interactions": "",
            "m_SingletonActionBindings": [],
            "m_Flags": 0,
        }
    
    def create_binding_yaml(
        self,
        name: str,
        path: str,
        action_id: str = "",
        groups: str = "",
        interactions: str = "",
        processors: str = "",
        is_composite: bool = False,
        is_part_of_composite: bool = False,
    ) -> dict[str, Any]:
        """Create a new binding structure."""
        flags = 0
        if is_composite:
            flags |= 1
        if is_part_of_composite:
            flags |= 2
        
        return {
            "m_Name": name,
            "m_Id": str(__import__('uuid').uuid4()),
            "m_Path": path,
            "m_Interactions": interactions,
            "m_Processors": processors,
            "m_Groups": groups,
            "m_Action": action_id,
            "m_Flags": flags,
        }
    
    def create_control_scheme_yaml(
        self,
        name: str,
        devices: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new control scheme structure."""
        import uuid
        device_requirements = []
        if devices:
            for device in devices:
                flags = 0
                if device.get("isOptional", False):
                    flags |= 1
                device_requirements.append({
                    "m_ControlPath": device.get("devicePath", ""),
                    "m_Flags": flags,
                })
        
        return {
            "m_Name": name,
            "m_BindingGroup": name,
            "m_DeviceRequirements": device_requirements,
        }
    
    def validate_action_type(self, action_type: str) -> tuple[bool, str]:
        """Validate an action type."""
        if action_type not in self.ACTION_TYPES:
            return False, f"Invalid action type '{action_type}'. Valid types: {', '.join(sorted(self.ACTION_TYPES))}"
        return True, ""
    
    def validate_control_path(self, path: str) -> tuple[bool, str]:
        """Validate a control path."""
        if not path:
            return False, "Control path cannot be empty"
        
        # Basic validation - check for common patterns
        valid_prefixes = [
            "<",  # Device path like <Keyboard>/space
            "*/",  # Wildcard like */{Submit}
        ]
        
        has_prefix = any(path.startswith(prefix) for prefix in valid_prefixes)
        if not has_prefix and "/" not in path:
            return False, f"Invalid control path '{path}'. Expected format: <Device>/button or */action"
        
        return True, ""
    
    def get_binding_path_examples(self) -> dict[str, list[str]]:
        """Get examples of common binding paths."""
        return {
            "Keyboard": [
                "<Keyboard>/space",
                "<Keyboard>/w",
                "<Keyboard>/escape",
                "<Keyboard>/leftShift",
                "<Keyboard>/anyKey",
            ],
            "Mouse": [
                "<Mouse>/leftButton",
                "<Mouse>/rightButton",
                "<Mouse>/middleButton",
                "<Mouse>/position",
                "<Mouse>/delta",
                "<Mouse>/scroll",
            ],
            "Gamepad": [
                "<Gamepad>/buttonSouth",
                "<Gamepad>/buttonNorth",
                "<Gamepad>/buttonEast",
                "<Gamepad>/buttonWest",
                "<Gamepad>/leftStick",
                "<Gamepad>/rightStick",
                "<Gamepad>/dpad",
                "<Gamepad>/leftTrigger",
                "<Gamepad>/rightTrigger",
            ],
            "Touch": [
                "<Touchscreen>/primaryTouch/position",
                "<Touchscreen>/primaryTouch/delta",
                "<Touchscreen>/primaryTouch/press",
            ],
            "XR": [
                "<XRController>/trigger",
                "<XRController>/grip",
                "<XRController>/devicePosition",
                "<XRController>/deviceRotation",
            ],
            "Composite": [
                "2DVector",
                "1DAxis",
                "ButtonWithOneModifier",
                "ButtonWithTwoModifiers",
            ],
        }


# Global helper instance
_input_system_helper: InputSystemHelper | None = None


def get_input_system_helper(project_root: Path | str | None = None) -> InputSystemHelper:
    """Get or create the global InputSystemHelper instance."""
    global _input_system_helper
    if _input_system_helper is None:
        _input_system_helper = InputSystemHelper(project_root)
    return _input_system_helper
