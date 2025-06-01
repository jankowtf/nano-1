"""Nanobricks package registry."""

from nanobricks.registry.api import (
    LocalRegistry,
    PackageInfo,
    RegistryBackend,
    RegistryClient,
    SearchResult,
    get_registry,
)
from nanobricks.registry.package import (
    Package,
    PackageFile,
    PackageMetadata,
    create_package_from_brick,
)
from nanobricks.registry.version import (
    Version,
    VersionPart,
    VersionRange,
    find_best_version,
    resolve_dependencies,
)

__all__ = [
    # Package
    "Package",
    "PackageFile",
    "PackageMetadata",
    "create_package_from_brick",
    # Version
    "Version",
    "VersionPart",
    "VersionRange",
    "find_best_version",
    "resolve_dependencies",
    # API
    "SearchResult",
    "PackageInfo",
    "RegistryBackend",
    "LocalRegistry",
    "RegistryClient",
    "get_registry",
]
