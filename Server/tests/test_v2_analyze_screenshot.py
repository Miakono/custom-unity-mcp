"""Tests for analyze_screenshot V2 tool (Visual QA)."""

import base64
import inspect
import io
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Try to import PIL, skip tests if not available
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

# Import conditionally - tests will be skipped if PIL not available
if PIL_AVAILABLE:
    from services.tools.analyze_screenshot import analyze_screenshot, _load_image, _extract_metadata, _perform_basic_validation
else:
    analyze_screenshot = None
    _load_image = None
    _extract_metadata = None
    _perform_basic_validation = None

from tests.integration.test_helpers import DummyContext


pytestmark = pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")


class TestAnalyzeScreenshotInterface:
    """Tests for tool interface and parameter validation."""

    def test_tool_has_required_parameters(self):
        """The analyze_screenshot tool should have required parameters."""
        sig = inspect.signature(analyze_screenshot)
        assert "ctx" in sig.parameters
        assert "action" in sig.parameters
        assert "analysis_type" in sig.parameters

    def test_optional_parameters_exist(self):
        """All optional parameters should be present."""
        sig = inspect.signature(analyze_screenshot)
        optional_params = [
            "screenshot_path",
            "screenshot_data",
            "query",
            "expected_elements",
            "regions_of_interest",
        ]
        for param in optional_params:
            assert param in sig.parameters

    def test_analysis_type_values(self):
        """analysis_type parameter should accept correct Literal values."""
        sig = inspect.signature(analyze_screenshot)
        annotation = str(sig.parameters["analysis_type"].annotation)
        expected_types = [
            "ui_validation",
            "scene_composition",
            "object_presence",
            "color_check",
            "custom",
        ]
        for type_name in expected_types:
            assert type_name in annotation


class TestAnalyzeFromPath:
    """Tests for analyze action with file path."""

    @pytest.fixture
    def sample_image(self, tmp_path):
        """Create a sample image file for testing."""
        img_path = tmp_path / "test_screenshot.png"
        img = Image.new("RGB", (800, 600), color="red")
        img.save(img_path)
        return str(img_path)

    @pytest.mark.asyncio
    async def test_analyze_from_path(self, sample_image):
        """Test analyzing screenshot from file path."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
            screenshot_path=sample_image,
        )

        assert resp["success"] is True
        assert resp["action"] == "analyze"
        assert resp["analysis_type"] == "ui_validation"
        assert "metadata" in resp
        assert "validation" in resp

    @pytest.mark.asyncio
    async def test_analyze_different_types(self, sample_image):
        """Test analyzing with different analysis types."""
        analysis_types = [
            "ui_validation",
            "scene_composition",
            "object_presence",
            "color_check",
        ]

        for analysis_type in analysis_types:
            resp = await analyze_screenshot(
                DummyContext(),
                action="analyze",
                analysis_type=analysis_type,
                screenshot_path=sample_image,
            )
            assert resp["success"] is True
            assert resp["analysis_type"] == analysis_type

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_path(self):
        """Test analyzing with non-existent file path."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
            screenshot_path="/nonexistent/path/screenshot.png",
        )

        assert resp["success"] is False
        assert "error" in resp

    @pytest.mark.asyncio
    async def test_analyze_with_expected_elements(self, sample_image):
        """Test analyzing with expected elements."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
            screenshot_path=sample_image,
            expected_elements=["Button", "Text", "Image"],
        )

        assert resp["success"] is True
        assert "validation" in resp
        assert "expected_elements" in resp["validation"]

    @pytest.mark.asyncio
    async def test_analyze_with_regions_of_interest(self, sample_image):
        """Test analyzing with regions of interest."""
        regions = [
            {"x": 0, "y": 0, "width": 100, "height": 100},
            {"x": 200, "y": 200, "width": 50, "height": 50},
        ]

        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
            screenshot_path=sample_image,
            regions_of_interest=regions,
        )

        assert resp["success"] is True
        assert "validation" in resp
        assert "regions_of_interest" in resp["validation"]


class TestAnalyzeFromBase64:
    """Tests for analyze action with base64 data."""

    @pytest.fixture
    def sample_base64_image(self):
        """Create a sample base64-encoded image."""
        img = Image.new("RGB", (400, 300), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return img_str

    @pytest.mark.asyncio
    async def test_analyze_from_base64(self, sample_base64_image):
        """Test analyzing screenshot from base64 data."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="scene_composition",
            screenshot_data=sample_base64_image,
        )

        assert resp["success"] is True
        assert resp["analysis_type"] == "scene_composition"
        assert "metadata" in resp

    @pytest.mark.asyncio
    async def test_analyze_from_base64_with_data_uri(self, sample_base64_image):
        """Test analyzing with data URI format."""
        data_uri = f"data:image/png;base64,{sample_base64_image}"

        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="scene_composition",
            screenshot_data=data_uri,
        )

        assert resp["success"] is True

    @pytest.mark.asyncio
    async def test_analyze_invalid_base64(self):
        """Test analyzing with invalid base64 data."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
            screenshot_data="invalid_base64!!!",
        )

        assert resp["success"] is False
        assert "error" in resp


class TestCustomAnalysis:
    """Tests for custom analysis type."""

    @pytest.fixture
    def sample_image(self, tmp_path):
        """Create a sample image file."""
        img_path = tmp_path / "test_screenshot.png"
        img = Image.new("RGB", (800, 600), color="green")
        img.save(img_path)
        return str(img_path)

    @pytest.mark.asyncio
    async def test_custom_analysis_requires_query(self, sample_image):
        """Test that custom analysis requires a query."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="custom",
            screenshot_path=sample_image,
        )

        assert resp["success"] is False
        assert "query is required" in resp["error"].lower()

    @pytest.mark.asyncio
    async def test_custom_analysis_with_query(self, sample_image):
        """Test custom analysis with query."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="custom",
            screenshot_path=sample_image,
            query="Count the number of red buttons in this UI",
        )

        assert resp["success"] is True
        assert resp["analysis"]["query"] == "Count the number of red buttons in this UI"


class TestInvalidInput:
    """Tests for invalid input handling."""

    @pytest.mark.asyncio
    async def test_no_image_source(self):
        """Test error when no image source provided."""
        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
        )

        assert resp["success"] is False
        assert "screenshot_path or screenshot_data" in resp["error"]

    @pytest.mark.asyncio
    async def test_both_sources_provided(self, tmp_path):
        """Test error when both sources provided."""
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100))
        img.save(img_path)

        resp = await analyze_screenshot(
            DummyContext(),
            action="analyze",
            analysis_type="ui_validation",
            screenshot_path=str(img_path),
            screenshot_data="base64data",
        )

        assert resp["success"] is False
        assert "not both" in resp["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tmp_path):
        """Test error for unknown action."""
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100))
        img.save(img_path)

        resp = await analyze_screenshot(
            DummyContext(),
            action="unknown_action",
            analysis_type="ui_validation",
            screenshot_path=str(img_path),
        )

        assert resp["success"] is False
        assert "Unknown action" in resp["error"]


class TestLoadImage:
    """Tests for _load_image helper function."""

    @pytest.fixture
    def sample_image_path(self, tmp_path):
        """Create a sample image file."""
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color="red")
        img.save(img_path)
        return str(img_path)

    @pytest.mark.asyncio
    async def test_load_from_path(self, sample_image_path):
        """Test loading image from file path."""
        image, source = await _load_image(sample_image_path, None)

        assert image is not None
        assert image.width == 100
        assert image.height == 100
        assert "file:" in source

    @pytest.mark.asyncio
    async def test_load_from_base64(self):
        """Test loading image from base64 data."""
        img = Image.new("RGB", (50, 50), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()

        image, source = await _load_image(None, img_str)

        assert image is not None
        assert image.width == 50
        assert image.height == 50
        assert "base64" in source

    @pytest.mark.asyncio
    async def test_load_nonexistent_path(self):
        """Test loading from non-existent path."""
        image, source = await _load_image("/nonexistent/file.png", None)

        assert image is None
        assert "not found" in source.lower()

    @pytest.mark.asyncio
    async def test_load_invalid_base64(self):
        """Test loading invalid base64 data."""
        image, source = await _load_image(None, "!!!invalid!!!")

        assert image is None
        assert "invalid" in source.lower()

    @pytest.mark.asyncio
    async def test_load_no_source(self):
        """Test loading with no source."""
        image, source = await _load_image(None, None)

        assert image is None
        assert "No image source" in source


class TestExtractMetadata:
    """Tests for _extract_metadata helper function."""

    def test_extract_basic_metadata(self):
        """Test extracting basic image metadata."""
        img = Image.new("RGB", (800, 600))
        metadata = _extract_metadata(img)

        assert metadata["width"] == 800
        assert metadata["height"] == 600
        assert metadata["dimensions"] == "800x600"
        assert metadata["aspect_ratio"] == pytest.approx(1.3333, 0.001)
        assert metadata["mode"] == "RGB"

    def test_extract_rgba_metadata(self):
        """Test extracting RGBA image metadata."""
        img = Image.new("RGBA", (1024, 768))
        metadata = _extract_metadata(img)

        assert metadata["width"] == 1024
        assert metadata["height"] == 768
        assert metadata["has_transparency"] is True
        assert metadata["bits_per_pixel"] == 32

    def test_extract_grayscale_metadata(self):
        """Test extracting grayscale image metadata."""
        img = Image.new("L", (512, 512))
        metadata = _extract_metadata(img)

        assert metadata["mode"] == "L"
        assert metadata["bits_per_pixel"] == 8


class TestPerformBasicValidation:
    """Tests for _perform_basic_validation helper function."""

    def test_validation_small_image(self):
        """Test validation warns for small images."""
        img = Image.new("RGB", (50, 50))
        result = _perform_basic_validation(img, None, None)

        assert result["image_valid"] is True
        assert len(result["warnings"]) > 0
        assert "small" in result["warnings"][0].lower()

    def test_validation_large_image(self):
        """Test validation warns for very large images."""
        img = Image.new("RGB", (5000, 5000))
        result = _perform_basic_validation(img, None, None)

        assert result["image_valid"] is True
        assert len(result["warnings"]) > 0
        assert "exceed" in result["warnings"][0].lower()

    def test_validation_expected_elements(self):
        """Test validation with expected elements."""
        img = Image.new("RGB", (800, 600))
        expected = ["Button", "Text"]
        result = _perform_basic_validation(img, expected, None)

        assert "expected_elements" in result
        assert result["expected_elements"]["provided"] == expected
        assert result["expected_elements"]["status"] == "pending"

    def test_validation_valid_regions(self):
        """Test validation with valid regions of interest."""
        img = Image.new("RGB", (800, 600))
        regions = [
            {"x": 0, "y": 0, "width": 100, "height": 100},
            {"x": 100, "y": 100, "width": 200, "height": 150},
        ]
        result = _perform_basic_validation(img, None, regions)

        assert "regions_of_interest" in result
        assert result["regions_of_interest"]["valid_count"] == 2
        assert result["regions_of_interest"]["invalid_count"] == 0

    def test_validation_invalid_regions_out_of_bounds(self):
        """Test validation with regions out of bounds."""
        img = Image.new("RGB", (100, 100))
        regions = [
            {"x": 50, "y": 50, "width": 100, "height": 100},  # Extends beyond
        ]
        result = _perform_basic_validation(img, None, regions)

        assert result["regions_of_interest"]["invalid_count"] == 1
        assert len(result["warnings"]) > 0

    def test_validation_invalid_regions_negative_values(self):
        """Test validation with negative region values."""
        img = Image.new("RGB", (800, 600))
        regions = [
            {"x": -10, "y": -10, "width": 100, "height": 100},
        ]
        result = _perform_basic_validation(img, None, regions)

        assert result["regions_of_interest"]["invalid_count"] == 1

    def test_validation_invalid_regions_missing_fields(self):
        """Test validation with regions missing required fields."""
        img = Image.new("RGB", (800, 600))
        regions = [
            {"x": 0, "y": 0, "width": 100},  # Missing height
        ]
        result = _perform_basic_validation(img, None, regions)

        assert result["regions_of_interest"]["invalid_count"] == 1
