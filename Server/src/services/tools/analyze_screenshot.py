"""
Screenshot analysis tool for visual verification and AI-powered image analysis.

Works in conjunction with manage_video_capture to provide a complete visual QA workflow:
1. Capture screenshot using manage_video_capture
2. Analyze the captured image using analyze_screenshot
3. Receive structured analysis results

This is a server-only tool that performs analysis locally without requiring Unity connection.
"""
import base64
import hashlib
import io
import os
from typing import Annotated, Any, Literal

from fastmcp import Context
from mcp.types import ToolAnnotations
from PIL import Image

from services.registry import mcp_for_unity_tool


@mcp_for_unity_tool(
    unity_target=None,
    group="visual_qa",
    description=(
        "Analyze screenshots and images for visual verification. "
        "Works with manage_video_capture to provide a complete capture → analyze workflow. "
        "Actions: analyze (perform image analysis), compare_screenshots (deterministic pixel diff). "
        "\n\nAnalysis Types:\n"
        "- ui_validation: Verify UI elements are present and correctly positioned\n"
        "- scene_composition: Analyze overall scene layout and visual balance\n"
        "- object_presence: Check for expected objects in the scene\n"
        "- color_check: Validate color schemes and visual consistency\n"
        "- custom: Use natural language query for specific analysis\n"
        "\n\nWorkflow:\n"
        "1. Use manage_video_capture to capture a screenshot\n"
        "2. Pass the screenshot path or data to analyze_screenshot\n"
        "3. Specify analysis_type and optional expected_elements\n"
        "4. Review structured analysis results"
    ),
    annotations=ToolAnnotations(
        title="Analyze Screenshot",
        readOnlyHint=True,
        openWorldHint=False,
    ),
)
async def analyze_screenshot(
    ctx: Context,
    action: Annotated[
        Literal["analyze", "compare_screenshots"],
        "Action to perform: analyze or compare_screenshots."
    ],
    analysis_type: Annotated[
        Literal["ui_validation", "scene_composition", "object_presence", "color_check", "custom"],
        "Type of analysis to perform on the image."
    ],
    screenshot_path: Annotated[
        str | None,
        "Path to the screenshot file to analyze. Either screenshot_path or screenshot_data must be provided."
    ] = None,
    screenshot_data: Annotated[
        str | None,
        "Base64-encoded image data. Either screenshot_path or screenshot_data must be provided."
    ] = None,
    screenshot_path_b: Annotated[
        str | None,
        "For compare_screenshots: path to the second screenshot file."
    ] = None,
    screenshot_data_b: Annotated[
        str | None,
        "For compare_screenshots: base64-encoded data for the second screenshot."
    ] = None,
    query: Annotated[
        str | None,
        "Natural language query for custom analysis type. Describe what to look for in the image."
    ] = None,
    expected_elements: Annotated[
        list[str] | None,
        "List of elements expected to be visible in the image. Used for validation."
    ] = None,
    regions_of_interest: Annotated[
        list[dict[str, int]] | None,
        "Specific regions to focus on, as list of {x, y, width, height} in pixels."
    ] = None,
) -> dict[str, Any]:
    """
    Analyze a screenshot or image for visual verification.
    
    This tool provides AI-powered image analysis capabilities for Unity game development
    workflows. It works alongside manage_video_capture to enable a complete visual QA
    pipeline: capture → analyze → act.
    
    For the initial implementation, this tool returns basic image metadata and performs
    simple validation. Future enhancements will integrate with vision-capable LLM APIs
    for advanced AI analysis.
    """
    action_lower = action.lower()
    
    if action_lower not in ("analyze", "compare_screenshots"):
        return {
            "success": False,
            "error": f"Unknown action '{action}'. Supported actions: analyze, compare_screenshots"
        }
    
    if action_lower == "analyze":
        # Validate input - must have either path or data
        if not screenshot_path and not screenshot_data:
            return {
                "success": False,
                "error": "Either screenshot_path or screenshot_data must be provided."
            }

        if screenshot_path and screenshot_data:
            return {
                "success": False,
                "error": "Provide either screenshot_path or screenshot_data, not both."
            }

    if action_lower == "compare_screenshots":
        if not (screenshot_path or screenshot_data):
            return {
                "success": False,
                "error": "compare_screenshots requires screenshot A via screenshot_path or screenshot_data."
            }
        if screenshot_path and screenshot_data:
            return {
                "success": False,
                "error": "For screenshot A provide either screenshot_path or screenshot_data, not both."
            }

        if not (screenshot_path_b or screenshot_data_b):
            return {
                "success": False,
                "error": "compare_screenshots requires screenshot B via screenshot_path_b or screenshot_data_b."
            }
        if screenshot_path_b and screenshot_data_b:
            return {
                "success": False,
                "error": "For screenshot B provide either screenshot_path_b or screenshot_data_b, not both."
            }
    
    # Validate custom query is provided when analysis_type is custom
    if analysis_type == "custom" and not query:
        return {
            "success": False,
            "error": "A natural language query is required when analysis_type is 'custom'."
        }
    
    try:
        if action_lower == "compare_screenshots":
            image_a, source_a = await _load_image(screenshot_path, screenshot_data)
            if image_a is None:
                return {
                    "success": False,
                    "error": f"Failed to load screenshot A: {source_a}"
                }

            image_b, source_b = await _load_image(screenshot_path_b, screenshot_data_b)
            if image_b is None:
                return {
                    "success": False,
                    "error": f"Failed to load screenshot B: {source_b}"
                }

            comparison = _compare_images(image_a, image_b)
            return {
                "success": True,
                "action": action_lower,
                "source_a": source_a,
                "source_b": source_b,
                "comparison": comparison,
            }

        # Load the image for analyze
        image, source_info = await _load_image(screenshot_path, screenshot_data)
        if image is None:
            return {
                "success": False,
                "error": f"Failed to load image: {source_info}"
            }
        
        # Extract basic metadata
        metadata = _extract_metadata(image)
        
        # Perform basic validation checks
        validation_results = _perform_basic_validation(
            image, expected_elements, regions_of_interest
        )
        
        # Build analysis result
        result = {
            "success": True,
            "action": action_lower,
            "analysis_type": analysis_type,
            "metadata": metadata,
            "source": source_info,
            "validation": validation_results,
            "analysis": {
                "status": "completed",
                "note": (
                    "Basic image analysis completed. "
                    "Advanced AI analysis will be available in a future update."
                ),
                "query": query if query else None,
            }
        }
        
        # Add placeholder for future AI analysis
        if analysis_type != "custom":
            result["analysis"]["detected_elements"] = _placeholder_detect_elements(
                image, analysis_type, expected_elements
            )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis failed: {str(e)}"
        }


async def _load_image(
    screenshot_path: str | None,
    screenshot_data: str | None
) -> tuple[Image.Image | None, str]:
    """
    Load an image from file path or base64 data.
    
    Returns:
        Tuple of (PIL Image, source description) or (None, error message)
    """
    try:
        if screenshot_path:
            # Validate path exists
            if not os.path.exists(screenshot_path):
                return None, f"File not found: {screenshot_path}"
            
            # Validate it's a file
            if not os.path.isfile(screenshot_path):
                return None, f"Path is not a file: {screenshot_path}"
            
            # Load image from file
            image = Image.open(screenshot_path)
            return image, f"file:{screenshot_path}"
        
        elif screenshot_data:
            # Decode base64 data
            try:
                # Handle both standard base64 and data URI format
                data = screenshot_data
                if "," in data:
                    # Remove data URI prefix (e.g., "data:image/png;base64,")
                    data = data.split(",", 1)[1]
                
                image_bytes = base64.b64decode(data)
                image = Image.open(io.BytesIO(image_bytes))
                return image, "data:base64"
            except base64.binascii.Error as e:
                return None, f"Invalid base64 data: {str(e)}"
            except Exception as e:
                return None, f"Failed to decode image data: {str(e)}"
        
        return None, "No image source provided"
        
    except Image.UnidentifiedImageError:
        return None, "Unsupported image format or corrupted image file"
    except Exception as e:
        return None, f"Error loading image: {str(e)}"


def _extract_metadata(image: Image.Image) -> dict[str, Any]:
    """
    Extract basic metadata from a PIL Image.
    
    Returns:
        Dictionary containing image metadata
    """
    metadata = {
        "width": image.width,
        "height": image.height,
        "dimensions": f"{image.width}x{image.height}",
        "aspect_ratio": round(image.width / image.height, 4) if image.height > 0 else None,
        "format": image.format if image.format else "Unknown",
        "mode": image.mode,
        "has_transparency": image.mode in ("RGBA", "P", "LA") or (
            image.mode == "P" and "transparency" in image.info
        ),
    }
    
    # Add file format specific info
    if image.format:
        metadata["format_description"] = Image.MIME.get(image.format, "Unknown")
    
    # Add color depth info based on mode
    mode_bits = {
        "1": 1, "L": 8, "P": 8, "RGB": 24, "RGBA": 32,
        "CMYK": 32, "YCbCr": 24, "LAB": 24, "HSV": 24,
        "I": 32, "F": 32, "LA": 16, "RGBX": 32, "RGBa": 32
    }
    metadata["bits_per_pixel"] = mode_bits.get(image.mode, "Unknown")
    
    return metadata


def _perform_basic_validation(
    image: Image.Image,
    expected_elements: list[str] | None,
    regions_of_interest: list[dict[str, int]] | None
) -> dict[str, Any]:
    """
    Perform basic validation checks on the image.
    
    Returns:
        Dictionary containing validation results
    """
    validation = {
        "image_valid": True,
        "checks_performed": [],
        "warnings": [],
    }
    
    # Check for very small images
    if image.width < 100 or image.height < 100:
        validation["warnings"].append(
            f"Image dimensions ({image.width}x{image.height}) are quite small for analysis"
        )
    
    # Check for very large images
    max_dimension = 4096
    if image.width > max_dimension or image.height > max_dimension:
        validation["warnings"].append(
            f"Image dimensions ({image.width}x{image.height}) exceed {max_dimension}px, "
            "may impact analysis performance"
        )
    
    # Validate expected elements (placeholder for future implementation)
    if expected_elements:
        validation["checks_performed"].append("expected_elements_validation")
        validation["expected_elements"] = {
            "provided": expected_elements,
            "status": "pending",
            "note": (
                "Expected elements validation is a placeholder. "
                "Full validation will be available with AI integration."
            ),
            "detected_count": 0,
            "missing_count": len(expected_elements),
        }
    
    # Validate regions of interest
    if regions_of_interest:
        validation["checks_performed"].append("regions_of_interest_validation")
        valid_regions = []
        invalid_regions = []
        
        for i, region in enumerate(regions_of_interest):
            # Check required fields
            required = {"x", "y", "width", "height"}
            if not all(k in region for k in required):
                invalid_regions.append({"index": i, "reason": "Missing required fields (x, y, width, height)"})
                continue
            
            x, y, w, h = region["x"], region["y"], region["width"], region["height"]
            
            # Validate region is within image bounds
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                invalid_regions.append({"index": i, "reason": "Invalid negative or zero values"})
                continue
            
            if x + w > image.width or y + h > image.height:
                invalid_regions.append({
                    "index": i,
                    "reason": f"Region extends beyond image bounds ({image.width}x{image.height})"
                })
                continue
            
            valid_regions.append({
                "index": i,
                "x": x, "y": y, "width": w, "height": h,
                "area_pixels": w * h
            })
        
        validation["regions_of_interest"] = {
            "provided_count": len(regions_of_interest),
            "valid_count": len(valid_regions),
            "invalid_count": len(invalid_regions),
            "valid_regions": valid_regions,
            "invalid_regions": invalid_regions,
        }
        
        if invalid_regions:
            validation["warnings"].append(
                f"{len(invalid_regions)} region(s) of interest are invalid or out of bounds"
            )
    
    return validation


def _placeholder_detect_elements(
    image: Image.Image,
    analysis_type: str,
    expected_elements: list[str] | None
) -> dict[str, Any]:
    """
    Placeholder function for element detection.
    
    This is a stub that will be replaced with actual AI-powered detection
    in a future update.
    
    Returns:
        Dictionary with placeholder detection results
    """
    return {
        "status": "placeholder",
        "note": (
            "Element detection is a placeholder for future AI integration. "
            "No actual detection is performed in this version."
        ),
        "analysis_type": analysis_type,
        "total_elements_found": 0,
        "confidence_threshold": None,
        "elements": [],
        "expected_elements": expected_elements if expected_elements else [],
    }


def _compare_images(image_a: Image.Image, image_b: Image.Image) -> dict[str, Any]:
    """Compare two screenshots and return deterministic diff metrics."""
    a = image_a.convert("RGB")
    b = image_b.convert("RGB")

    if a.size != b.size:
        b = b.resize(a.size, Image.Resampling.LANCZOS)

    data_a = a.tobytes()
    data_b = b.tobytes()

    total_channels = len(data_a)
    abs_diff_sum = 0
    changed_channels = 0
    for av, bv in zip(data_a, data_b):
        delta = abs(av - bv)
        abs_diff_sum += delta
        if delta > 0:
            changed_channels += 1

    total_pixels = a.size[0] * a.size[1]
    mean_abs_diff = abs_diff_sum / max(1, total_channels)

    changed_pixels = 0
    threshold = 8
    for idx in range(0, total_channels, 3):
        if (
            abs(data_a[idx] - data_b[idx]) > threshold
            or abs(data_a[idx + 1] - data_b[idx + 1]) > threshold
            or abs(data_a[idx + 2] - data_b[idx + 2]) > threshold
        ):
            changed_pixels += 1

    hash_a = hashlib.sha256(data_a).hexdigest()
    hash_b = hashlib.sha256(data_b).hexdigest()

    return {
        "width": a.size[0],
        "height": a.size[1],
        "mean_abs_diff": round(mean_abs_diff, 4),
        "changed_pixels": changed_pixels,
        "changed_pixels_pct": round((changed_pixels * 100.0) / max(1, total_pixels), 4),
        "changed_channels_pct": round((changed_channels * 100.0) / max(1, total_channels), 4),
        "hash_a": hash_a,
        "hash_b": hash_b,
        "exact_match": hash_a == hash_b,
        "note": "If dimensions differ, screenshot B is resized to screenshot A before comparison.",
    }
