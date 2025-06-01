"""Skill framework for Nanobricks.

Skills are optional capabilities that can be added to any nanobrick
without modifying its core logic. They wrap the brick to add features
like logging, API endpoints, CLI interfaces, etc.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from nanobricks.protocol import NanobrickBase, NanobrickProtocol, T_deps, T_in, T_out


class Skill(ABC, Generic[T_in, T_out, T_deps]):
    """Base class for all skills.

    A skill wraps a nanobrick to add capabilities without
    modifying the brick's core behavior.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the skill with optional configuration."""
        self.config = config or {}
        self._wrapped: NanobrickProtocol[T_in, T_out, T_deps] | None = None

    @property
    def name(self) -> str:
        """Return the skill name."""
        return self.__class__.__name__.replace("Skill", "").lower()

    def enhance(
        self, brick: NanobrickProtocol[T_in, T_out, T_deps]
    ) -> NanobrickProtocol[T_in, T_out, T_deps]:
        """Enhance a brick with this skill.

        Args:
            brick: The nanobrick to enhance

        Returns:
            An enhanced version of the brick
        """
        self._wrapped = brick
        return self._create_enhanced_brick(brick)

    @abstractmethod
    def _create_enhanced_brick(
        self, brick: NanobrickProtocol[T_in, T_out, T_deps]
    ) -> NanobrickProtocol[T_in, T_out, T_deps]:
        """Create the enhanced version of the brick.

        Subclasses must implement this to define how they enhance bricks.
        """
        pass

    def _get_wrapped(self) -> NanobrickProtocol[T_in, T_out, T_deps]:
        """Get the wrapped brick, raising error if not set."""
        if self._wrapped is None:
            raise RuntimeError(f"{self.name} skill not attached to a brick")
        return self._wrapped


class NanobrickEnhanced(NanobrickBase[T_in, T_out, T_deps]):
    """Base class for enhanced bricks created by skills."""

    def __init__(
        self,
        wrapped: NanobrickProtocol[T_in, T_out, T_deps],
        skill: Skill[T_in, T_out, T_deps],
    ):
        """Initialize with the wrapped brick and skill."""
        self._wrapped = wrapped
        self._skill = skill
        # Inherit properties from wrapped brick
        self.name = f"{wrapped.name}+{skill.name}"
        self.version = wrapped.version

    def __repr__(self) -> str:
        return f"{self._wrapped!r}+{self._skill.name}"

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


# Type for the registry
T_Skill = TypeVar("T_Skill", bound=Skill)


class SkillRegistry:
    """Registry for available skills."""

    def __init__(self):
        self._skills: dict[str, type[Skill]] = {}

    def register(self, name: str, skill_class: type[T_Skill]) -> None:
        """Register a skill class.

        Args:
            name: The name to register under
            skill_class: The skill class
        """
        if name in self._skills:
            import warnings

            warnings.warn(
                f"Skill '{name}' already registered, replacing with {skill_class.__name__}",
                UserWarning,
                stacklevel=3,
            )
        self._skills[name] = skill_class

    def get(self, name: str) -> type[Skill]:
        """Get a skill class by name.

        Args:
            name: The skill name

        Returns:
            The skill class

        Raises:
            KeyError: If skill not found
        """
        if name not in self._skills:
            raise KeyError(
                f"Skill '{name}' not found. Available: {list(self._skills.keys())}"
            )
        return self._skills[name]

    def create(self, name: str, config: dict[str, Any] | None = None) -> Skill:
        """Create a skill instance.

        Args:
            name: The skill name
            config: Optional configuration

        Returns:
            A skill instance
        """
        skill_class = self.get(name)
        return skill_class(config=config)

    def list(self) -> list[str]:
        """List all registered skill names."""
        return list(self._skills.keys())


# Global registry instance
_registry = SkillRegistry()


def register_skill(name: str | None = None):
    """Decorator to register a skill class.

    Args:
        name: Optional name to register under (defaults to class name)

    Returns:
        Decorator function
    """

    def decorator(cls: type[T_Skill]) -> type[T_Skill]:
        skill_name = name or cls.__name__.replace("Skill", "").lower()
        _registry.register(skill_name, cls)
        return cls

    return decorator


def with_skill(
    brick: NanobrickProtocol[T_in, T_out, T_deps],
    skill: str | Skill[T_in, T_out, T_deps],
    **config: Any,
) -> NanobrickProtocol[T_in, T_out, T_deps]:
    """Add a skill to a brick.

    Args:
        brick: The brick to enhance
        skill: Skill name or instance
        **config: Configuration for the skill

    Returns:
        Enhanced brick
    """
    if isinstance(skill, str):
        skill = _registry.create(skill, config)

    return skill.enhance(brick)


def skill(name: str | type[Skill], **config: Any):
    """Decorator to add a skill to a brick class.

    Args:
        name: Skill name or class
        **config: Configuration for the skill

    Returns:
        Decorator function
    """

    def decorator(cls: type[NanobrickProtocol]) -> type[NanobrickProtocol]:
        # Create a new class that wraps the original
        class EnhancedClass(cls):
            def __init__(self, *args, **kwargs):
                # Call parent init
                super().__init__(*args, **kwargs)

                # Create skill instance
                if isinstance(name, str):
                    sp = _registry.create(name, config)
                else:
                    sp = name(config)

                # Create a temporary instance to get enhanced methods
                temp_instance = type(self).__bases__[0](*args, **kwargs)
                enhanced = sp.enhance(temp_instance)

                # Replace our methods with enhanced ones
                self.invoke = enhanced.invoke
                self.invoke_sync = enhanced.invoke_sync
                self.name = enhanced.name

                # Copy all methods from enhanced instance
                for attr_name in dir(enhanced):
                    if not attr_name.startswith("_"):
                        attr = getattr(enhanced, attr_name)
                        if callable(attr) and not hasattr(self, attr_name):
                            setattr(self, attr_name, attr)

        # Copy class metadata
        EnhancedClass.__name__ = cls.__name__
        EnhancedClass.__module__ = cls.__module__
        EnhancedClass.__qualname__ = cls.__qualname__

        return EnhancedClass

    return decorator


# Extension point for nanobricks
def add_with_skill_method():
    """Add with_skill method to NanobrickBase."""

    def with_skill(
        self: NanobrickProtocol[T_in, T_out, T_deps],
        name: str | Skill[T_in, T_out, T_deps],
        **config: Any,
    ) -> NanobrickProtocol[T_in, T_out, T_deps]:
        """Add a skill to this brick.

        Args:
            name: Skill name or instance
            **config: Configuration for the skill

        Returns:
            Enhanced version of this brick
        """
        # Use the global with_skill function directly
        if isinstance(name, str):
            sp = _registry.create(name, config)
        else:
            sp = name

        return sp.enhance(self)

    # Add method to NanobrickBase
    NanobrickBase.with_skill = with_skill


# Install the method when module is imported
add_with_skill_method()
