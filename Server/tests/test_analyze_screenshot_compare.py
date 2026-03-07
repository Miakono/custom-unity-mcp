import io

import pytest

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

if PIL_AVAILABLE:
    from services.tools.analyze_screenshot import analyze_screenshot
else:
    analyze_screenshot = None

from tests.integration.test_helpers import DummyContext


pytestmark = pytest.mark.skipif(not PIL_AVAILABLE, reason="PIL not installed")


def _png_base64(rgb: tuple[int, int, int]) -> str:
    import base64

    img = Image.new("RGB", (64, 64), color=rgb)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.mark.asyncio
async def test_compare_screenshots_exact_match():
    data = _png_base64((30, 60, 90))

    result = await analyze_screenshot(
        DummyContext(),
        action="compare_screenshots",
        analysis_type="scene_composition",
        screenshot_data=data,
        screenshot_data_b=data,
    )

    assert result["success"] is True
    assert result["comparison"]["exact_match"] is True
    assert result["comparison"]["changed_pixels"] == 0


@pytest.mark.asyncio
async def test_compare_screenshots_detects_difference():
    data_a = _png_base64((0, 0, 0))
    data_b = _png_base64((255, 255, 255))

    result = await analyze_screenshot(
        DummyContext(),
        action="compare_screenshots",
        analysis_type="scene_composition",
        screenshot_data=data_a,
        screenshot_data_b=data_b,
    )

    assert result["success"] is True
    assert result["comparison"]["exact_match"] is False
    assert result["comparison"]["changed_pixels"] > 0
    assert result["comparison"]["mean_abs_diff"] > 0
