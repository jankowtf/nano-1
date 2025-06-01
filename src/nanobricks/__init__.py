"""
Nanobricks: Antifragile code components that compose like Lego bricks.

A revolutionary framework for building composable, resilient software components
that gain strength from stress and complexity.
"""

__version__ = "0.1.0"

# Export main protocol and base classes
# Import built-in skills to register them
import nanobricks.skills  # noqa: F401
from nanobricks.composition import NanobrickComposite, Pipeline
from nanobricks.dependencies import DependencyContainer, StandardDeps

# Performance utilities (optional import)
from nanobricks.performance import (
    NanobrickBatched,
    NanobrickCached,
    FusedPipeline,
    MemoryPool,
    fuse_pipeline,
    with_batching,
    with_cache,
)
from nanobricks.protocol import NanobrickBase, NanobrickProtocol, NanobrickSimple
from nanobricks.registry import (
    Package,
    PackageMetadata,
    RegistryClient,
    Version,
    create_package_from_brick,
    get_registry,
)
from nanobricks.skill import (
    NanobrickEnhanced,
    Skill,
    register_skill,
    skill,
    with_skill,
)

__all__ = [
    "__version__",
    # Core protocol
    "NanobrickProtocol",
    "NanobrickBase",
    "NanobrickSimple",
    # Composition
    "NanobrickComposite",
    "Pipeline",
    # Dependencies
    "DependencyContainer",
    "StandardDeps",
    # Skills
    "Skill",
    "NanobrickEnhanced",
    "with_skill",
    "skill",
    "register_skill",
    # Registry
    "Package",
    "PackageMetadata",
    "RegistryClient",
    "Version",
    "create_package_from_brick",
    "get_registry",
    # Performance
    "NanobrickCached",
    "NanobrickBatched",
    "FusedPipeline",
    "MemoryPool",
    "with_cache",
    "with_batching",
    "fuse_pipeline",
]
