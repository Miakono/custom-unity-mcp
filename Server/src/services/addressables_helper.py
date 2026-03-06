"""
Addressables Helper Service

Provides utilities for parsing Unity Addressables configuration files,
building group/asset mappings, reading build reports, and analyzing dependencies.

This service operates on the server side and helps process Addressables data
returned from Unity or read from configuration files.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("mcp-for-unity-server")


@dataclass
class AddressableAssetEntry:
    """Represents a single asset entry in an Addressable group."""
    guid: str
    asset_path: str
    address: str
    labels: list[str] = field(default_factory=list)
    bundle_file_id: str | None = None
    size_bytes: int = 0


@dataclass
class AddressableGroup:
    """Represents an Addressable asset group."""
    name: str
    guid: str
    settings_asset_path: str
    bundle_naming_mode: str = "Filename"
    bundle_mode: str = "PackTogether"
    assets: list[AddressableAssetEntry] = field(default_factory=list)
    schema_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuildBundleInfo:
    """Information about a built asset bundle."""
    name: str
    file_path: str
    size_bytes: int
    compression: str
    crc: str | None = None
    hash: str | None = None


@dataclass
class BuildReportSummary:
    """Summary of an Addressables build."""
    build_path: str
    build_target: str
    build_date: str
    total_bundles: int
    total_size_bytes: int
    bundles: list[BuildBundleInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class DependencyInfo:
    """Dependency analysis result for an asset."""
    asset_path: str
    guid: str
    direct_dependencies: list[str] = field(default_factory=list)
    implicit_dependencies: list[str] = field(default_factory=list)
    circular_dependencies: list[str] = field(default_factory=list)
    total_size_with_dependencies: int = 0


class AddressablesHelper:
    """
    Helper class for working with Unity Addressables data.
    
    Provides methods to parse configuration, analyze build reports,
    and understand asset dependencies.
    """

    # Known bundle naming modes
    BUNDLE_NAMING_MODES = {
        0: "Filename",
        1: "FilenameHash",
        2: "NoHash",
        3: "OnlyHash",
    }

    # Known bundle modes
    BUNDLE_MODES = {
        0: "PackTogether",
        1: "PackSeparately",
        2: "PackByLabel",
    }

    def __init__(self, project_path: str | None = None):
        """
        Initialize the Addressables helper.
        
        Args:
            project_path: Path to the Unity project (optional).
        """
        self.project_path = Path(project_path) if project_path else None
        self._groups_cache: dict[str, AddressableGroup] = {}
        self._labels_cache: set[str] = set()

    def parse_build_report(self, report_data: dict[str, Any] | str) -> BuildReportSummary | None:
        """
        Parse Addressables build report data.
        
        Args:
            report_data: Build report as dict or JSON string.
            
        Returns:
            Parsed BuildReportSummary or None if parsing fails.
        """
        try:
            if isinstance(report_data, str):
                report_data = json.loads(report_data)

            if not isinstance(report_data, dict):
                logger.warning("Invalid build report format: expected dict")
                return None

            summary = report_data.get("summary", {})
            bundles_data = report_data.get("bundles", [])
            errors = report_data.get("errors", [])
            warnings = report_data.get("warnings", [])

            bundles = []
            for bundle_data in bundles_data:
                bundle = BuildBundleInfo(
                    name=bundle_data.get("name", "unknown"),
                    file_path=bundle_data.get("filePath", ""),
                    size_bytes=bundle_data.get("sizeBytes", 0),
                    compression=bundle_data.get("compression", "Unknown"),
                    crc=bundle_data.get("crc"),
                    hash=bundle_data.get("hash"),
                )
                bundles.append(bundle)

            return BuildReportSummary(
                build_path=summary.get("buildPath", ""),
                build_target=summary.get("buildTarget", "Unknown"),
                build_date=summary.get("buildDate", ""),
                total_bundles=summary.get("totalBundles", len(bundles)),
                total_size_bytes=summary.get("totalSizeBytes", 
                                              sum(b.size_bytes for b in bundles)),
                bundles=bundles,
                errors=errors if isinstance(errors, list) else [],
                warnings=warnings if isinstance(warnings, list) else [],
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse build report JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing build report: {e}")
            return None

    def analyze_dependencies(
        self,
        asset_guid: str,
        group_data: list[dict[str, Any]]
    ) -> DependencyInfo:
        """
        Analyze dependencies for a specific asset.
        
        Args:
            asset_guid: GUID of the asset to analyze.
            group_data: List of group dictionaries containing asset entries.
            
        Returns:
            DependencyInfo with dependency analysis.
        """
        result = DependencyInfo(asset_path="", guid=asset_guid)

        # Build a lookup of all assets
        all_assets: dict[str, AddressableAssetEntry] = {}
        for group in group_data:
            for asset_data in group.get("assets", []):
                entry = AddressableAssetEntry(
                    guid=asset_data.get("guid", ""),
                    asset_path=asset_data.get("assetPath", ""),
                    address=asset_data.get("address", ""),
                    labels=asset_data.get("labels", []),
                )
                all_assets[entry.guid] = entry

        # Find the target asset
        if asset_guid in all_assets:
            target = all_assets[asset_guid]
            result.asset_path = target.asset_path

        # Analyze dependencies (simplified - would need actual dependency tree)
        # This is a placeholder that could be enhanced with actual Unity dependency data
        result.direct_dependencies = []
        result.implicit_dependencies = []
        result.circular_dependencies = []

        return result

    def calculate_bundle_efficiency(
        self,
        build_report: BuildReportSummary
    ) -> dict[str, Any]:
        """
        Calculate bundle efficiency metrics.
        
        Args:
            build_report: Parsed build report summary.
            
        Returns:
            Dictionary with efficiency metrics.
        """
        if not build_report.bundles:
            return {
                "average_bundle_size": 0,
                "largest_bundle": None,
                "smallest_bundle": None,
                "total_bundles": 0,
            }

        sizes = [b.size_bytes for b in build_report.bundles]
        largest = max(build_report.bundles, key=lambda b: b.size_bytes)
        smallest = min(build_report.bundles, key=lambda b: b.size_bytes)

        return {
            "average_bundle_size": sum(sizes) // len(sizes),
            "largest_bundle": {
                "name": largest.name,
                "size_bytes": largest.size_bytes,
                "size_mb": round(largest.size_bytes / (1024 * 1024), 2),
            },
            "smallest_bundle": {
                "name": smallest.name,
                "size_bytes": smallest.size_bytes,
                "size_kb": round(smallest.size_bytes / 1024, 2),
            },
            "total_bundles": len(build_report.bundles),
            "total_size_mb": round(build_report.total_size_bytes / (1024 * 1024), 2),
        }

    def validate_address_configuration(
        self,
        groups: list[AddressableGroup]
    ) -> dict[str, Any]:
        """
        Validate Addressables configuration for common issues.
        
        Args:
            groups: List of Addressable groups to validate.
            
        Returns:
            Validation results with issues found.
        """
        issues = {
            "errors": [],
            "warnings": [],
            "info": [],
        }

        all_addresses: dict[str, str] = {}  # address -> guid
        all_guids: set[str] = set()

        for group in groups:
            if not group.assets:
                issues["warnings"].append(
                    f"Group '{group.name}' is empty (no assets)"
                )

            for asset in group.assets:
                # Check for duplicate GUIDs
                if asset.guid in all_guids:
                    issues["errors"].append(
                        f"Duplicate GUID '{asset.guid}' found in group '{group.name}'"
                    )
                all_guids.add(asset.guid)

                # Check for duplicate addresses
                if asset.address in all_addresses:
                    issues["errors"].append(
                        f"Duplicate address '{asset.address}' - "
                        f"GUIDs: {all_addresses[asset.address]} and {asset.guid}"
                    )
                else:
                    all_addresses[asset.address] = asset.guid

                # Check for missing labels
                if not asset.labels:
                    issues["info"].append(
                        f"Asset '{asset.address}' has no labels assigned"
                    )

                # Validate address format
                if asset.address.startswith("Assets/"):
                    issues["warnings"].append(
                        f"Asset '{asset.guid}' uses path as address - "
                        "consider using a simplified address"
                    )

        return {
            "valid": len(issues["errors"]) == 0,
            "issue_count": len(issues["errors"]) + len(issues["warnings"]),
            **issues,
        }

    def format_size(self, size_bytes: int) -> str:
        """
        Format byte size to human-readable string.
        
        Args:
            size_bytes: Size in bytes.
            
        Returns:
            Human-readable size string.
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def parse_platform_from_path(self, path: str) -> str | None:
        """
        Try to determine platform from a build path.
        
        Args:
            path: Build output path.
            
        Returns:
            Detected platform name or None.
        """
        path_lower = path.lower()
        platform_patterns = {
            "StandaloneWindows64": ["windows", "win64", "standalonewindows"],
            "StandaloneOSX": ["osx", "macos", "mac", "standaloneosx"],
            "StandaloneLinux64": ["linux", "linux64", "standalonelinux"],
            "iOS": ["ios", "iphone"],
            "Android": ["android"],
            "WebGL": ["webgl"],
            "PS5": ["ps5", "playstation5"],
            "XboxSeriesX": ["xbox", "xboxseries"],
        }

        for platform, patterns in platform_patterns.items():
            if any(pattern in path_lower for pattern in patterns):
                return platform

        return None

    def generate_build_summary(
        self,
        build_report: BuildReportSummary
    ) -> dict[str, Any]:
        """
        Generate a comprehensive build summary.
        
        Args:
            build_report: Parsed build report.
            
        Returns:
            Dictionary with formatted summary data.
        """
        efficiency = self.calculate_bundle_efficiency(build_report)

        return {
            "build_info": {
                "path": build_report.build_path,
                "target": build_report.build_target,
                "date": build_report.build_date,
            },
            "statistics": {
                "total_bundles": build_report.total_bundles,
                "total_size": self.format_size(build_report.total_size_bytes),
                "total_size_bytes": build_report.total_size_bytes,
            },
            "efficiency": efficiency,
            "bundles": [
                {
                    "name": b.name,
                    "size": self.format_size(b.size_bytes),
                    "size_bytes": b.size_bytes,
                    "compression": b.compression,
                }
                for b in build_report.bundles
            ],
            "issues": {
                "errors": build_report.errors,
                "warnings": build_report.warnings,
                "error_count": len(build_report.errors),
                "warning_count": len(build_report.warnings),
            },
        }


# Global helper instance
_addressables_helper: AddressablesHelper | None = None


def get_addressables_helper(project_path: str | None = None) -> AddressablesHelper:
    """
    Get or create the global Addressables helper instance.
    
    Args:
        project_path: Optional project path for the helper.
        
    Returns:
        AddressablesHelper instance.
    """
    global _addressables_helper
    if _addressables_helper is None:
        _addressables_helper = AddressablesHelper(project_path)
    return _addressables_helper
