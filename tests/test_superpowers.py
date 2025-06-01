"""Tests for the skill framework."""

import pytest

from nanobricks import (
    NanobrickEnhanced,
    NanobrickSimple,
    Skill,
    register_skill,
    skill,
    with_skill,
)
from nanobricks.skill import _registry


class TestSkill:
    """Test the Skill base class."""

    def test_basic_skill(self):
        """Test creating a basic skill."""

        class LoggingSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                class LoggingEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        print(f"[LOG] Input: {input}")
                        result = await self._wrapped.invoke(input, deps=deps)
                        print(f"[LOG] Output: {result}")
                        return result

                return LoggingEnhanced(brick, self)

        # Create brick and skill
        class TestNanobrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        brick = TestNanobrick(name="test")

        sp = LoggingSkill()
        enhanced = sp.enhance(brick)

        assert enhanced.name == "test+logging"
        assert str(enhanced) == "test+logging v0.1.0"

    def test_skill_config(self):
        """Test skill with configuration."""

        class ConfigurableSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                prefix = self.config.get("prefix", ">>")

                class ConfiguredEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return f"{prefix} {result}"

                return ConfiguredEnhanced(brick, self)

        class TestNanobrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        brick = TestNanobrick()

        sp = ConfigurableSkill(config={"prefix": "***"})
        enhanced = sp.enhance(brick)

        import asyncio

        result = asyncio.run(enhanced.invoke("test"))
        assert result == "*** test"


class TestSkillRegistry:
    """Test the skill registry."""

    def test_register_and_get(self):
        """Test registering and retrieving skills."""
        # Clear registry first
        _registry._skills.clear()

        @register_skill("test")
        class TestSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                return brick

        # Should be registered
        assert "test" in _registry.list()

        # Should be retrievable
        sp_class = _registry.get("test")
        assert sp_class == TestSkill

        # Should create instance
        sp = _registry.create("test", {"key": "value"})
        assert isinstance(sp, TestSkill)
        assert sp.config["key"] == "value"

    def test_duplicate_registration(self):
        """Test that duplicate registration raises error."""
        _registry._skills.clear()

        @register_skill("duplicate")
        class DuplicateSkill1(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                return brick

        with pytest.raises(ValueError, match="already registered"):

            @register_skill("duplicate")
            class DuplicateSkill2(Skill[str, str, None]):
                def _create_enhanced_brick(self, brick):
                    return brick

    def test_missing_skill(self):
        """Test retrieving non-existent skill."""
        with pytest.raises(KeyError, match="not found"):
            _registry.get("nonexistent")


class TestWithSkill:
    """Test the with_skill function and method."""

    def test_with_skill_function(self):
        """Test enhancing a brick with with_skill function."""
        _registry._skills.clear()

        @register_skill("uppercase")
        class UppercaseSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                class UppercaseEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return result.upper()

                return UppercaseEnhanced(brick, self)

        class TestNanobrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return f"hello {input}"

        brick = TestNanobrick()

        enhanced = with_skill(brick, "uppercase")

        import asyncio

        result = asyncio.run(enhanced.invoke("world"))
        assert result == "HELLO WORLD"

    def test_with_skill_method(self):
        """Test the with_skill method on bricks."""
        _registry._skills.clear()

        @register_skill("reverse")
        class ReverseSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                class ReverseEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return result[::-1]

                return ReverseEnhanced(brick, self)

        # Create a brick
        class MyNanobrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return f"processed: {input}"

        brick = MyNanobrick()
        enhanced = brick.with_skill("reverse")

        import asyncio

        result = asyncio.run(enhanced.invoke("test"))
        assert result == "tset :dessecorp"

    def test_chain_skills(self):
        """Test chaining multiple skills."""
        _registry._skills.clear()

        @register_skill("brackets")
        class BracketsSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                class BracketsEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return f"[{result}]"

                return BracketsEnhanced(brick, self)

        @register_skill("exclaim")
        class ExclaimSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                class ExclaimEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return f"{result}!"

                return ExclaimEnhanced(brick, self)

        class TestNanobrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        brick = TestNanobrick()

        # Chain skills
        enhanced = brick.with_skill("brackets").with_skill("exclaim")

        import asyncio

        result = asyncio.run(enhanced.invoke("test"))
        assert result == "[test]!"


class TestSkillDecorator:
    """Test the @skill decorator."""

    def test_skill_decorator(self):
        """Test decorating a class with @skill."""
        _registry._skills.clear()

        @register_skill("shout")
        class ShoutSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                class ShoutEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return result.upper() + "!!!"

                return ShoutEnhanced(brick, self)

        @skill("shout")
        class MyNanobrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return f"saying: {input}"

        brick = MyNanobrick()

        import asyncio

        result = asyncio.run(brick.invoke("hello"))
        assert result == "SAYING: HELLO!!!"
        assert brick.name == "MyNanobrick+shout"

    def test_multiple_decorators(self):
        """Test multiple skill decorators."""
        _registry._skills.clear()

        @register_skill("wrap")
        class WrapSkill(Skill[str, str, None]):
            def _create_enhanced_brick(self, brick):
                wrapper = self.config.get("wrapper", "*")

                class WrapEnhanced(NanobrickEnhanced[str, str, None]):
                    async def invoke(self, input: str, *, deps=None) -> str:
                        result = await self._wrapped.invoke(input, deps=deps)
                        return f"{wrapper}{result}{wrapper}"

                return WrapEnhanced(brick, self)

        # Note: Multiple decorators would be applied in reverse order
        @skill("wrap", wrapper=">>>")
        @skill("wrap", wrapper="***")
        class MultiBrick(NanobrickSimple[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        brick = MultiBrick()

        import asyncio

        result = asyncio.run(brick.invoke("test"))
        # Inner decorator (***) applies first, then outer (>>>)
        assert result == ">>>***test***>>>"
