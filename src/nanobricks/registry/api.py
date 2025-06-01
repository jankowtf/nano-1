"""Registry API for discovering and managing nanobrick packages."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nanobricks.registry.package import Package, PackageMetadata
from nanobricks.registry.version import Version, VersionRange, find_best_version


@dataclass
class SearchResult:
    """Search result from registry."""

    name: str
    version: str
    description: str
    author: str
    downloads: int = 0
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "downloads": self.downloads,
            "score": self.score,
        }


@dataclass
class PackageInfo:
    """Detailed package information."""

    metadata: PackageMetadata
    versions: list[Version] = field(default_factory=list)
    downloads: dict[str, int] = field(default_factory=dict)  # version -> count
    total_downloads: int = 0
    latest_version: Version | None = None
    latest_stable: Version | None = None

    def __post_init__(self):
        """Calculate derived fields."""
        if self.versions:
            self.versions.sort(reverse=True)
            self.latest_version = self.versions[0]

            stable = [v for v in self.versions if not v.is_prerelease()]
            if stable:
                self.latest_stable = stable[0]

        self.total_downloads = sum(self.downloads.values())


class RegistryBackend(ABC):
    """Abstract base class for registry backends."""

    @abstractmethod
    async def search(
        self, query: str, *, limit: int = 50, offset: int = 0, **filters
    ) -> list[SearchResult]:
        """Search for packages."""
        pass

    @abstractmethod
    async def get_package_info(self, name: str) -> PackageInfo | None:
        """Get detailed package information."""
        pass

    @abstractmethod
    async def get_package(self, name: str, version: str) -> Package | None:
        """Download a specific package version."""
        pass

    @abstractmethod
    async def publish_package(self, package: Package, api_key: str) -> bool:
        """Publish a package to the registry."""
        pass

    @abstractmethod
    async def list_versions(self, name: str) -> list[Version]:
        """List all versions of a package."""
        pass


class LocalRegistry(RegistryBackend):
    """Local file-based registry for development."""

    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.path / "index.json"
        self._load_index()

    def _load_index(self):
        """Load package index."""
        if self.index_path.exists():
            with open(self.index_path) as f:
                self.index = json.load(f)
        else:
            self.index = {"packages": {}, "updated": datetime.now().isoformat()}

    def _save_index(self):
        """Save package index."""
        self.index["updated"] = datetime.now().isoformat()
        with open(self.index_path, "w") as f:
            json.dump(self.index, f, indent=2)

    async def search(
        self, query: str, *, limit: int = 50, offset: int = 0, **filters
    ) -> list[SearchResult]:
        """Search for packages."""
        results = []
        query_lower = query.lower()

        for name, info in self.index["packages"].items():
            # Simple text search
            if (
                query_lower in name.lower()
                or query_lower in info.get("description", "").lower()
                or any(query_lower in kw.lower() for kw in info.get("keywords", []))
            ):
                # Apply filters
                if filters:
                    skip = False
                    for key, value in filters.items():
                        if key == "author" and info.get("author") != value:
                            skip = True
                            break
                        elif key == "skill" and value not in info.get("skills", []):
                            skip = True
                            break

                    if skip:
                        continue

                # Calculate simple relevance score
                score = 0.0
                if query_lower in name.lower():
                    score += 10.0
                if query_lower in info.get("description", "").lower():
                    score += 5.0
                score += len(
                    [kw for kw in info.get("keywords", []) if query_lower in kw.lower()]
                )

                results.append(
                    SearchResult(
                        name=name,
                        version=info.get("latest_version", "0.0.0"),
                        description=info.get("description", ""),
                        author=info.get("author", ""),
                        downloads=info.get("total_downloads", 0),
                        score=score,
                    )
                )

        # Sort by score and apply pagination
        results.sort(key=lambda x: (-x.score, -x.downloads, x.name))
        return results[offset : offset + limit]

    async def get_package_info(self, name: str) -> PackageInfo | None:
        """Get detailed package information."""
        if name not in self.index["packages"]:
            return None

        info = self.index["packages"][name]

        # Load metadata
        metadata = PackageMetadata.from_dict(info["metadata"])

        # Parse versions
        versions = [Version.parse(v) for v in info.get("versions", [])]

        return PackageInfo(
            metadata=metadata,
            versions=versions,
            downloads=info.get("downloads", {}),
        )

    async def get_package(self, name: str, version: str) -> Package | None:
        """Download a specific package version."""
        package_path = self.path / name / f"{name}-{version}.nbp"

        if not package_path.exists():
            return None

        # Load package
        with open(package_path, "rb") as f:
            return Package.from_archive(f.read())

    async def publish_package(self, package: Package, api_key: str) -> bool:
        """Publish a package to the registry."""
        # Simple API key check for local registry
        if api_key != "local-dev-key":
            return False

        name = package.metadata.name
        version = str(package.metadata.version)

        # Create package directory
        package_dir = self.path / name
        package_dir.mkdir(parents=True, exist_ok=True)

        # Save package file
        package_path = package_dir / f"{name}-{version}.nbp"
        with open(package_path, "wb") as f:
            f.write(package.to_archive())

        # Update index
        if name not in self.index["packages"]:
            self.index["packages"][name] = {
                "metadata": package.metadata.to_dict(),
                "versions": [],
                "downloads": {},
                "total_downloads": 0,
                "created_at": datetime.now().isoformat(),
            }

        pkg_info = self.index["packages"][name]

        # Add version if not exists
        if version not in pkg_info["versions"]:
            pkg_info["versions"].append(version)
            pkg_info["downloads"][version] = 0

        # Update metadata to latest
        pkg_info["metadata"] = package.metadata.to_dict()
        pkg_info["updated"] = datetime.now().isoformat()

        # Sort versions and update latest
        versions = [Version.parse(v) for v in pkg_info["versions"]]
        versions.sort(reverse=True)
        pkg_info["latest_version"] = str(versions[0])

        stable = [v for v in versions if not v.is_prerelease()]
        if stable:
            pkg_info["latest_stable"] = str(stable[0])

        self._save_index()
        return True

    async def list_versions(self, name: str) -> list[Version]:
        """List all versions of a package."""
        if name not in self.index["packages"]:
            return []

        version_strings = self.index["packages"][name].get("versions", [])
        versions = [Version.parse(v) for v in version_strings]
        versions.sort(reverse=True)
        return versions

    def record_download(self, name: str, version: str):
        """Record a package download."""
        if name in self.index["packages"]:
            pkg_info = self.index["packages"][name]
            downloads = pkg_info.setdefault("downloads", {})
            downloads[version] = downloads.get(version, 0) + 1
            pkg_info["total_downloads"] = sum(downloads.values())
            self._save_index()


class RegistryClient:
    """Client for interacting with package registries."""

    def __init__(self, backend: RegistryBackend):
        self.backend = backend
        self._cache: dict[str, Any] = {}

    async def search(
        self,
        query: str,
        *,
        limit: int = 50,
        author: str | None = None,
        skill: str | None = None,
    ) -> list[SearchResult]:
        """Search for packages.

        Args:
            query: Search query
            limit: Maximum results
            author: Filter by author
            skill: Filter by skill

        Returns:
            List of search results
        """
        filters = {}
        if author:
            filters["author"] = author
        if skill:
            filters["skill"] = skill

        return await self.backend.search(query, limit=limit, **filters)

    async def info(self, name: str) -> PackageInfo | None:
        """Get package information.

        Args:
            name: Package name

        Returns:
            Package info or None
        """
        return await self.backend.get_package_info(name)

    async def install(
        self,
        name: str,
        version_spec: str | None = None,
        target_dir: Path | None = None,
    ) -> Package | None:
        """Install a package.

        Args:
            name: Package name
            version_spec: Version specification (e.g., ">=1.0.0")
            target_dir: Target directory (defaults to current)

        Returns:
            Installed package or None
        """
        # Get available versions
        versions = await self.backend.list_versions(name)
        if not versions:
            return None

        # Find best version
        if version_spec:
            constraint = VersionRange.parse(version_spec)
            best_version = find_best_version(versions, constraint)
            if not best_version:
                return None
        else:
            # Use latest stable or latest
            stable = [v for v in versions if not v.is_prerelease()]
            best_version = stable[0] if stable else versions[0]

        # Download package
        package = await self.backend.get_package(name, str(best_version))
        if not package:
            return None

        # Extract to target directory
        if target_dir is None:
            target_dir = Path.cwd() / "nanobricks" / name

        package.extract_to(target_dir)

        # Record download if local registry
        if isinstance(self.backend, LocalRegistry):
            self.backend.record_download(name, str(best_version))

        return package

    async def publish(self, package: Package, api_key: str) -> bool:
        """Publish a package.

        Args:
            package: Package to publish
            api_key: API key for authentication

        Returns:
            True if successful
        """
        return await self.backend.publish_package(package, api_key)

    async def list_installed(self, base_dir: Path | None = None) -> list[PackageInfo]:
        """List installed packages.

        Args:
            base_dir: Base directory to search (defaults to nanobricks/)

        Returns:
            List of installed packages
        """
        if base_dir is None:
            base_dir = Path.cwd() / "nanobricks"

        installed = []

        if base_dir.exists():
            for package_dir in base_dir.iterdir():
                if package_dir.is_dir():
                    metadata_path = package_dir / "nanobrick.toml"
                    if metadata_path.exists():
                        metadata = PackageMetadata.from_toml(metadata_path)
                        installed.append(
                            PackageInfo(
                                metadata=metadata,
                                versions=[Version.parse(metadata.version)],
                            )
                        )

        return installed


# Global registry client
_global_client: RegistryClient | None = None


def get_registry(registry_url: str | None = None) -> RegistryClient:
    """Get or create registry client.

    Args:
        registry_url: Registry URL (defaults to local)

    Returns:
        Registry client
    """
    global _global_client

    if _global_client is None:
        # Default to local registry
        local_path = Path.home() / ".nanobricks" / "registry"
        backend = LocalRegistry(local_path)
        _global_client = RegistryClient(backend)

    return _global_client


__all__ = [
    "SearchResult",
    "PackageInfo",
    "RegistryBackend",
    "LocalRegistry",
    "RegistryClient",
    "get_registry",
]
