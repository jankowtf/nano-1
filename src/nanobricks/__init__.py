"""
Nanobricks: Antifragile code components that compose like Lego bricks.

A revolutionary framework for building composable, resilient software components
that gain strength from stress and complexity.
"""

__version__ = "0.2.3"

# Export main protocol and base classes
# Import built-in skills to register them
import nanobricks.skills  # noqa: F401
from nanobricks.composition import NanobrickComposite, Pipeline
from nanobricks.pipeline_builder import PipelineBuilder
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
from nanobricks.protocol import (
    Nanobrick,
    NanobrickBase,
    NanobrickProtocol,
    NanobrickSimple,  # Deprecated - kept for backwards compatibility
)
from nanobricks.typing import (
    Result,
    TypeAdapter,
    TypeMismatchError,
    auto_adapter,
    check_type_compatibility,
    dict_to_json,
    dict_to_string,
    json_to_dict,
    list_to_tuple,
    string_to_dict,
    tuple_to_list,
)
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
    "Nanobrick",  # Primary class
    "NanobrickProtocol",
    "NanobrickBase",
    "NanobrickSimple",  # Deprecated
    # Composition
    "NanobrickComposite",
    "Pipeline",
    "PipelineBuilder",
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
    # Type utilities
    "Result",
    "TypeAdapter",
    "TypeMismatchError",
    "auto_adapter",
    "check_type_compatibility",
    "string_to_dict",
    "dict_to_string",
    "list_to_tuple",
    "tuple_to_list",
    "json_to_dict",
    "dict_to_json",
]
