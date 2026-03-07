"""Tests for V2 spatial tools.

Covers 2 tools:
- manage_transform
- spatial_queries
"""

import inspect
from unittest.mock import AsyncMock

import pytest

from services.tools.manage_transform import manage_transform
from services.tools.spatial_queries import spatial_queries
from tests.integration.test_helpers import DummyContext


# =============================================================================
# manage_transform Tests
# =============================================================================
class TestManageTransformInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The manage_transform tool should have required parameters."""
        sig = inspect.signature(manage_transform)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "target" in sig.parameters

    def test_action_parameter_values(self):
        """action parameter should accept correct Literal values."""
        sig = inspect.signature(manage_transform)
        action_annotation = str(sig.parameters["action"].annotation)
        expected_actions = [
            "get_world_transform",
            "get_local_transform",
            "set_world_transform",
            "set_local_transform",
            "get_bounds",
            "snap_to_grid",
            "align_to_object",
            "distribute_objects",
            "place_relative",
            "validate_placement",
        ]
        for action in expected_actions:
            assert action in action_annotation

    def test_optional_parameters_exist(self):
        """All optional parameters should be present."""
        sig = inspect.signature(manage_transform)
        optional_params = [
            "search_method",
            "position",
            "rotation",
            "scale",
            "grid_size",
            "snap_position",
            "snap_rotation",
            "reference_object",
            "align_axis",
            "align_mode",
            "targets",
            "distribute_axis",
            "distribute_spacing",
            "offset",
            "direction",
            "distance",
            "use_world_space",
            "check_overlap",
            "check_off_grid",
            "check_invalid_scale",
            "min_spacing",
        ]
        for param in optional_params:
            assert param in sig.parameters


class TestGetWorldTransform:
    """Tests for get_world_transform action."""

    @pytest.mark.asyncio
    async def test_get_world_transform(self, monkeypatch):
        """Test getting world transform."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "position": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "rotation": {"x": 0.0, "y": 90.0, "z": 0.0},
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="get_world_transform",
            target="Player",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_world_transform"
        assert captured["params"]["target"] == "Player"

    @pytest.mark.asyncio
    async def test_get_world_transform_by_id(self, monkeypatch):
        """Test getting world transform by instance ID."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "data": {"position": {"x": 0, "y": 0, "z": 0}}}

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="get_world_transform",
            target=12345,
            search_method="by_id",
        )

        assert resp["success"] is True
        assert captured["params"]["searchMethod"] == "by_id"


class TestSetWorldTransform:
    """Tests for set_world_transform action."""

    @pytest.mark.asyncio
    async def test_set_world_transform_with_list(self, monkeypatch):
        """Test setting world transform with list position."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Transform updated"}

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="set_world_transform",
            target="Player",
            position=[10.0, 5.0, 0.0],
            rotation=[0.0, 45.0, 0.0],
        )

        assert resp["success"] is True
        assert captured["params"]["position"] == [10.0, 5.0, 0.0]
        assert captured["params"]["rotation"] == [0.0, 45.0, 0.0]

    @pytest.mark.asyncio
    async def test_set_world_transform_with_dict(self, monkeypatch):
        """Test setting world transform with dict position (normalized to list)."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Transform updated"}

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="set_world_transform",
            target="Player",
            position={"x": 1.0, "y": 2.0, "z": 3.0},
        )

        assert resp["success"] is True
        # Dict position gets normalized to list by normalize_vector3
        assert captured["params"]["position"] == [1.0, 2.0, 3.0]

    @pytest.mark.asyncio
    async def test_set_world_transform_invalid_vector(self, monkeypatch):
        """Test error handling for invalid vector format."""
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="set_world_transform",
            target="Player",
            position="invalid",
        )

        assert resp["success"] is False
        assert "position" in resp["message"].lower()


class TestGetLocalTransform:
    """Tests for get_local_transform action."""

    @pytest.mark.asyncio
    async def test_get_local_transform(self, monkeypatch):
        """Test getting local transform."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "localPosition": {"x": 0.0, "y": 1.0, "z": 0.0},
                    "localRotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "localScale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="get_local_transform",
            target="Player/Child",
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "get_local_transform"


class TestSnapToGrid:
    """Tests for snap_to_grid action."""

    @pytest.mark.asyncio
    async def test_snap_to_grid(self, monkeypatch):
        """Test snapping to grid."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "originalPosition": {"x": 1.3, "y": 2.7, "z": 3.1},
                    "snappedPosition": {"x": 1.0, "y": 3.0, "z": 3.0},
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="snap_to_grid",
            target="Player",
            grid_size=1.0,
            snap_position=True,
            snap_rotation=False,
        )

        assert resp["success"] is True
        assert captured["params"]["gridSize"] == 1.0
        assert captured["params"]["snapPosition"] is True
        assert captured["params"]["snapRotation"] is False


class TestAlignToObject:
    """Tests for align_to_object action."""

    @pytest.mark.asyncio
    async def test_align_to_object(self, monkeypatch):
        """Test aligning to another object."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "message": "Aligned to target"}

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="align_to_object",
            target="ObjectA",
            reference_object="ObjectB",
            align_axis="x",
            align_mode="center",
        )

        assert resp["success"] is True
        assert captured["params"]["referenceObject"] == "ObjectB"
        assert captured["params"]["alignAxis"] == "x"
        assert captured["params"]["alignMode"] == "center"


class TestValidatePlacement:
    """Tests for validate_placement action."""

    @pytest.mark.asyncio
    async def test_validate_placement(self, monkeypatch):
        """Test validating placement."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "isValid": True,
                    "checks": {
                        "offGrid": False,
                        "overlap": False,
                        "invalidScale": False,
                    },
                },
            }

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="validate_placement",
            target="NewObject",
            check_overlap=True,
            check_off_grid=True,
            check_invalid_scale=True,
            min_spacing=0.5,
        )

        assert resp["success"] is True
        assert captured["params"]["checkOverlap"] is True
        assert captured["params"]["minSpacing"] == 0.5


class TestManageTransformErrors:
    """Tests for error handling in manage_transform."""

    @pytest.mark.asyncio
    async def test_error_handling(self, monkeypatch):
        """Test general error handling."""

        async def fake_send(*args, **kwargs):
            raise RuntimeError("Unity error")

        monkeypatch.setattr(
            "services.tools.manage_transform.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.manage_transform.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await manage_transform(
            DummyContext(),
            action="get_world_transform",
            target="Player",
        )

        assert resp["success"] is False
        assert "Python error in manage_transform" in resp["message"]


# =============================================================================
# spatial_queries Tests
# =============================================================================
class TestSpatialQueriesInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The spatial_queries tool should have required parameters."""
        sig = inspect.signature(spatial_queries)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters

    def test_action_parameter_values(self):
        """action parameter should accept correct Literal values."""
        sig = inspect.signature(spatial_queries)
        action_annotation = str(sig.parameters["action"].annotation)
        expected_actions = [
            "nearest_object",
            "objects_in_radius",
            "objects_in_box",
            "overlap_check",
            "raycast",
            "get_distance",
            "get_direction",
            "get_relative_offset",
        ]
        for action in expected_actions:
            assert action in action_annotation


class TestObjectsInRadius:
    """Tests for objects_in_radius action."""

    @pytest.mark.asyncio
    async def test_objects_in_radius(self, monkeypatch):
        """Test finding objects within radius."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "objects": [
                        {"name": "Enemy1", "distance": 5.0},
                        {"name": "Enemy2", "distance": 8.0},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="objects_in_radius",
            source="Player",
            radius=10.0,
            max_results=50,
        )

        assert resp["success"] is True
        assert captured["params"]["action"] == "objects_in_radius"
        assert captured["params"]["source"] == "Player"
        assert captured["params"]["radius"] == 10.0

    @pytest.mark.asyncio
    async def test_objects_in_radius_with_filters(self, monkeypatch):
        """Test finding objects with filters."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {"success": True, "data": {"objects": []}}

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="objects_in_radius",
            point=[0.0, 0.0, 0.0],
            radius=15.0,
            filter_by_tag="Enemy",
            filter_by_layer="Default",
            exclude_inactive=True,
        )

        assert resp["success"] is True
        assert captured["params"]["filterByTag"] == "Enemy"
        assert captured["params"]["filterByLayer"] == "Default"
        assert captured["params"]["excludeInactive"] is True


class TestObjectsInBox:
    """Tests for objects_in_box action."""

    @pytest.mark.asyncio
    async def test_objects_in_box(self, monkeypatch):
        """Test finding objects within a box."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "objects": [
                        {"name": "Box1"},
                        {"name": "Box2"},
                    ]
                },
            }

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="objects_in_box",
            box_center=[0.0, 0.0, 0.0],
            box_size=[10.0, 10.0, 10.0],
        )

        assert resp["success"] is True
        assert captured["params"]["boxCenter"] == [0.0, 0.0, 0.0]
        assert captured["params"]["boxSize"] == [10.0, 10.0, 10.0]


class TestRaycast:
    """Tests for raycast action."""

    @pytest.mark.asyncio
    async def test_raycast(self, monkeypatch):
        """Test raycasting."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "hit": True,
                    "hitPoint": {"x": 5.0, "y": 0.0, "z": 0.0},
                    "hitObject": "Wall",
                    "distance": 5.0,
                },
            }

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="raycast",
            origin=[0.0, 0.0, 0.0],
            direction=[1.0, 0.0, 0.0],
            max_distance=100.0,
            layer_mask="Default,Obstacles",
        )

        assert resp["success"] is True
        assert captured["params"]["origin"] == [0.0, 0.0, 0.0]
        assert captured["params"]["direction"] == [1.0, 0.0, 0.0]
        assert captured["params"]["maxDistance"] == 100.0


class TestGetDistance:
    """Tests for get_distance action."""

    @pytest.mark.asyncio
    async def test_get_distance(self, monkeypatch):
        """Test getting distance between objects."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "distance": 10.5,
                    "distanceSquared": 110.25,
                },
            }

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="get_distance",
            source="Player",
            target="Enemy",
        )

        assert resp["success"] is True
        assert captured["params"]["source"] == "Player"
        assert captured["params"]["target"] == "Enemy"


class TestOverlapCheck:
    """Tests for overlap_check action."""

    @pytest.mark.asyncio
    async def test_overlap_check(self, monkeypatch):
        """Test overlap checking."""
        captured = {}

        async def fake_send(*args, **kwargs):
            captured["params"] = args[3]
            return {
                "success": True,
                "data": {
                    "hasOverlap": True,
                    "overlappingObjects": ["Obstacle1"],
                },
            }

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="overlap_check",
            object_to_place="NewObject",
            placement_position=[5.0, 0.0, 5.0],
            min_clearance=0.5,
        )

        assert resp["success"] is True
        assert captured["params"]["objectToPlace"] == "NewObject"
        assert captured["params"]["placementPosition"] == [5.0, 0.0, 5.0]


class TestSpatialQueriesErrors:
    """Tests for error handling in spatial_queries."""

    @pytest.mark.asyncio
    async def test_invalid_vector_error(self, monkeypatch):
        """Test error handling for invalid vector format."""
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="objects_in_box",
            box_center="invalid",
        )

        assert resp["success"] is False
        assert "box_center" in resp["message"].lower()

    @pytest.mark.asyncio
    async def test_error_handling(self, monkeypatch):
        """Test general error handling."""

        async def fake_send(*args, **kwargs):
            raise RuntimeError("Unity error")

        monkeypatch.setattr(
            "services.tools.spatial_queries.send_with_unity_instance", fake_send
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.get_unity_instance_from_context",
            AsyncMock(return_value="Project@hash"),
        )
        monkeypatch.setattr(
            "services.tools.spatial_queries.maybe_run_tool_preflight",
            AsyncMock(return_value=None),
        )

        resp = await spatial_queries(
            DummyContext(),
            action="objects_in_radius",
            source="Player",
        )

        assert resp["success"] is False
        assert "Python error in spatial_queries" in resp["message"]
