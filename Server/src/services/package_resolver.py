"""
Service for resolving Unity Package Manager packages.

Reads and parses Packages/manifest.json and Packages/packages-lock.json
to provide information about installed packages and their dependencies.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass


class PackageSource(Enum):
    """Source of a Unity package."""
    REGISTRY = "registry"
    GIT = "git"
    LOCAL = "local"
    TARBALL = "tarball"
    BUILT_IN = "built-in"
    UNKNOWN = "unknown"


@dataclass
class PackageInfo:
    """Information about a Unity package."""
    name: str
    version: str
    source: PackageSource
    display_name: str | None = None
    description: str | None = None
    author: dict[str, Any] | None = None
    dependencies: dict[str, str] = field(default_factory=dict)
    resolved_path: str | None = None
    # For git packages
    git_url: str | None = None
    git_hash: str | None = None
    # For tarball packages
    tarball_path: str | None = None
    # For local packages
    local_path: str | None = None
    # For registry packages
    registry_url: str | None = None
    is_test_package: bool = False
    is_optional: bool = False


@dataclass
class ScopedRegistry:
    """Information about a scoped registry."""
    name: str
    url: str
    scopes: list[str]


@dataclass
class PackageManifest:
    """Parsed Unity package manifest."""
    dependencies: dict[str, PackageInfo]
    scoped_registries: list[ScopedRegistry]
    testables: list[str]
    lock_info: dict[str, Any]
    raw_manifest: dict[str, Any]
    raw_lock: dict[str, Any] | None = None


class PackageResolver:
    """
    Resolves Unity Package Manager packages from manifest files.
    
    This class provides methods to read and parse:
    - Packages/manifest.json - Main package manifest
    - Packages/packages-lock.json - Lock file with resolved versions
    """

    def __init__(self, project_root: str | Path | None = None):
        """
        Initialize the package resolver.
        
        Args:
            project_root: Path to the Unity project root. If None, attempts to
                         find it from the current working directory.
        """
        if project_root is None:
            project_root = self._find_project_root()
        
        self.project_root = Path(project_root)
        self.packages_path = self.project_root / "Packages"
        self.manifest_path = self.packages_path / "manifest.json"
        self.lock_path = self.packages_path / "packages-lock.json"

    def _find_project_root(self) -> Path:
        """Find the Unity project root from the current directory."""
        cwd = Path.cwd()
        
        # Check if current directory has Assets and Packages folders
        if (cwd / "Assets").exists() and (cwd / "Packages").exists():
            return cwd
        
        # Check parent directories
        for parent in cwd.parents:
            if (parent / "Assets").exists() and (parent / "Packages").exists():
                return parent
        
        # Default to current directory if not found
        return cwd

    def _detect_package_source(self, version_spec: str) -> tuple[PackageSource, dict[str, Any]]:
        """
        Detect the source of a package from its version specification.
        
        Args:
            version_spec: Version string from manifest (e.g., "1.0.0", "https://...", "file:...")
            
        Returns:
            Tuple of (PackageSource, extra_info dict)
        """
        extra_info: dict[str, Any] = {}
        
        if version_spec.startswith("https://") or version_spec.startswith("http://"):
            # Git URL format: https://... or https://...#branch
            extra_info["git_url"] = version_spec
            return PackageSource.GIT, extra_info
        
        if version_spec.startswith("git:") or version_spec.startswith("git+"):
            extra_info["git_url"] = version_spec
            return PackageSource.GIT, extra_info
        
        if version_spec.startswith("file:"):
            local_path = version_spec[5:]  # Remove 'file:' prefix
            extra_info["local_path"] = local_path
            
            # Check if it's a tarball
            if local_path.endswith(".tgz") or local_path.endswith(".tar.gz"):
                extra_info["tarball_path"] = local_path
                return PackageSource.TARBALL, extra_info
            
            return PackageSource.LOCAL, extra_info
        
        if version_spec.startswith("com.unity"):
            return PackageSource.BUILT_IN, extra_info
        
        # Version number like "1.0.0" or "1.0.0-preview.1"
        if version_spec[0].isdigit():
            return PackageSource.REGISTRY, extra_info
        
        return PackageSource.UNKNOWN, extra_info

    def _parse_manifest(self) -> dict[str, Any] | None:
        """Parse the manifest.json file."""
        if not self.manifest_path.exists():
            return None
        
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return None

    def _parse_lock_file(self) -> dict[str, Any] | None:
        """Parse the packages-lock.json file."""
        if not self.lock_path.exists():
            return None
        
        try:
            with open(self.lock_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return None

    def _parse_scoped_registries(self, manifest: dict[str, Any]) -> list[ScopedRegistry]:
        """Parse scoped registries from manifest."""
        registries: list[ScopedRegistry] = []
        
        scoped_registries = manifest.get("scopedRegistries", [])
        for registry in scoped_registries:
            registries.append(ScopedRegistry(
                name=registry.get("name", ""),
                url=registry.get("url", ""),
                scopes=registry.get("scopes", [])
            ))
        
        return registries

    def get_manifest(self) -> PackageManifest | None:
        """
        Get the parsed package manifest.
        
        Returns:
            PackageManifest object or None if manifest not found/invalid.
        """
        manifest_data = self._parse_manifest()
        if manifest_data is None:
            return None
        
        lock_data = self._parse_lock_file()
        
        dependencies: dict[str, PackageInfo] = {}
        manifest_deps = manifest_data.get("dependencies", {})
        lock_deps = lock_data.get("dependencies", {}) if lock_data else {}
        
        for pkg_name, version_spec in manifest_deps.items():
            source, extra_info = self._detect_package_source(version_spec)
            
            # Get lock file info if available
            lock_info = lock_deps.get(pkg_name, {})
            resolved_version = lock_info.get("version", version_spec)
            resolved_path = lock_info.get("path")
            
            # Override source based on lock file
            lock_source = lock_info.get("source")
            if lock_source:
                source = PackageSource(lock_source) if lock_source in [s.value for s in PackageSource] else source
            
            # Check if it's a test package
            is_test = pkg_name in manifest_data.get("testables", [])
            
            package_info = PackageInfo(
                name=pkg_name,
                version=resolved_version,
                source=source,
                resolved_path=resolved_path,
                dependencies=lock_info.get("dependencies", {}),
                is_test_package=is_test,
                **extra_info
            )
            
            dependencies[pkg_name] = package_info
        
        scoped_registries = self._parse_scoped_registries(manifest_data)
        testables = manifest_data.get("testables", [])
        
        return PackageManifest(
            dependencies=dependencies,
            scoped_registries=scoped_registries,
            testables=testables,
            lock_info=lock_data or {},
            raw_manifest=manifest_data,
            raw_lock=lock_data
        )

    def get_package_info(self, package_name: str) -> PackageInfo | None:
        """
        Get information about a specific package.
        
        Args:
            package_name: Name of the package (e.g., "com.unity.entities")
            
        Returns:
            PackageInfo object or None if not found.
        """
        manifest = self.get_manifest()
        if manifest is None:
            return None
        
        return manifest.dependencies.get(package_name)

    def list_installed_packages(self) -> list[PackageInfo]:
        """
        List all installed packages.
        
        Returns:
            List of PackageInfo objects.
        """
        manifest = self.get_manifest()
        if manifest is None:
            return []
        
        return list(manifest.dependencies.values())

    def list_registries(self) -> list[ScopedRegistry]:
        """
        List all configured scoped registries.
        
        Returns:
            List of ScopedRegistry objects.
        """
        manifest = self.get_manifest()
        if manifest is None:
            return []
        
        return manifest.scoped_registries

    def add_package(self, package_name: str, version_spec: str) -> bool:
        """
        Add a package to the manifest.
        
        Args:
            package_name: Name of the package to add
            version_spec: Version specification (e.g., "1.0.0", git URL, etc.)
            
        Returns:
            True if successful, False otherwise.
        """
        manifest_data = self._parse_manifest()
        if manifest_data is None:
            return False
        
        if "dependencies" not in manifest_data:
            manifest_data["dependencies"] = {}
        
        manifest_data["dependencies"][package_name] = version_spec
        
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
            return True
        except IOError:
            return False

    def remove_package(self, package_name: str) -> bool:
        """
        Remove a package from the manifest.
        
        Args:
            package_name: Name of the package to remove
            
        Returns:
            True if successful, False otherwise.
        """
        manifest_data = self._parse_manifest()
        if manifest_data is None:
            return False
        
        deps = manifest_data.get("dependencies", {})
        if package_name not in deps:
            return False
        
        del deps[package_name]
        
        # Also remove from testables if present
        testables = manifest_data.get("testables", [])
        if package_name in testables:
            testables.remove(package_name)
            manifest_data["testables"] = testables
        
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
            return True
        except IOError:
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert package info to dictionary for JSON serialization."""
        manifest = self.get_manifest()
        if manifest is None:
            return {"error": "Could not parse manifest"}
        
        return {
            "dependencies": {
                name: {
                    "name": pkg.name,
                    "version": pkg.version,
                    "source": pkg.source.value,
                    "dependencies": pkg.dependencies,
                    **({"gitUrl": pkg.git_url} if pkg.git_url else {}),
                    **({"localPath": pkg.local_path} if pkg.local_path else {}),
                    **({"tarballPath": pkg.tarball_path} if pkg.tarball_path else {}),
                    **({"resolvedPath": pkg.resolved_path} if pkg.resolved_path else {}),
                    **({"isTestPackage": True} if pkg.is_test_package else {}),
                }
                for name, pkg in manifest.dependencies.items()
            },
            "scopedRegistries": [
                {
                    "name": reg.name,
                    "url": reg.url,
                    "scopes": reg.scopes
                }
                for reg in manifest.scoped_registries
            ],
            "testables": manifest.testables,
        }
