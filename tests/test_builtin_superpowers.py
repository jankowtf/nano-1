"""Tests for built-in skills."""

import logging

import pytest

from nanobricks import Nanobrick, skill


class TestLoggingSkill:
    """Test the logging skill."""

    def test_basic_logging(self, caplog):
        """Test basic logging functionality."""

        # Create a simple brick
        class TestNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return f"Hello, {input}!"

        # Add logging skill
        brick = TestNanobrick()
        logged_brick = brick.with_skill("logging", level="INFO")

        # Use it
        import asyncio

        with caplog.at_level(logging.INFO):
            result = asyncio.run(logged_brick.invoke("World"))

        # Check result
        assert result == "Hello, World!"

        # Check logs
        assert any("Input: World" in record.message for record in caplog.records)
        assert any(
            "Output: Hello, World!" in record.message for record in caplog.records
        )

    def test_error_logging(self, caplog):
        """Test error logging."""

        class FailingNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                raise ValueError("Something went wrong!")

        brick = FailingNanobrick()
        logged_brick = brick.with_skill("logging")

        import asyncio

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ValueError):
                asyncio.run(logged_brick.invoke("test"))

        # Check error was logged
        assert any(
            "Error" in record.message and "ValueError" in record.message
            for record in caplog.records
        )

    def test_logging_config(self, caplog):
        """Test logging configuration options."""

        class TestNanobrick(Nanobrick[dict, dict]):
            async def invoke(self, input: dict, *, deps=None) -> dict:
                return {"result": input["value"] * 2}

        # Configure logging
        brick = TestNanobrick()
        logged_brick = brick.with_skill(
            "logging",
            level="DEBUG",
            log_inputs=True,
            log_outputs=False,  # Don't log outputs
            pretty=True,
        )

        import asyncio

        with caplog.at_level(logging.DEBUG):
            result = asyncio.run(logged_brick.invoke({"value": 5}))

        assert result == {"result": 10}

        # Should log input but not output
        assert any("Input:" in record.message for record in caplog.records)
        assert not any("Output:" in record.message for record in caplog.records)

    def test_truncation(self, caplog):
        """Test value truncation in logs."""

        class TestNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        # Create very long input
        long_input = "x" * 200

        brick = TestNanobrick()
        logged_brick = brick.with_skill("logging", truncate=50)

        import asyncio

        with caplog.at_level(logging.INFO):
            result = asyncio.run(logged_brick.invoke(long_input))

        # Check truncation in logs
        for record in caplog.records:
            if "Input:" in record.message:
                assert "..." in record.message
                assert len(record.message) < 100  # Reasonable length


class TestSkillApi:
    """Test the API skill."""

    def test_api_creation(self):
        """Test API app creation."""

        class TestNanobrick(Nanobrick[dict, dict]):
            async def invoke(self, input: dict, *, deps=None) -> dict:
                return {"doubled": input.get("value", 0) * 2}

        brick = TestNanobrick()
        api_brick = brick.with_skill("api", path="/double", port=8001)

        # Check that enhanced brick has API methods
        assert hasattr(api_brick, "create_app")
        assert hasattr(api_brick, "start_server")

    def test_api_server_config(self):
        """Test API server configuration."""

        class TestNanobrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        brick = TestNanobrick()
        api_brick = brick.with_skill(
            "api", path="/uppercase", host="localhost", port=9000, docs=True
        )

        # Check configuration was stored
        assert hasattr(api_brick, "_skill")
        assert api_brick._skill.config["path"] == "/uppercase"
        assert api_brick._skill.config["host"] == "localhost"
        assert api_brick._skill.config["port"] == 9000

        # Test that create_app method exists and works
        app = api_brick.create_app()
        assert app is not None

        # Check the app has expected properties
        assert hasattr(app, "routes")

    def test_api_normal_invocation(self):
        """Test that normal invocation still works."""

        class TestNanobrick(Nanobrick[int, int]):
            async def invoke(self, input: int, *, deps=None) -> int:
                return input * 3

        brick = TestNanobrick()
        api_brick = brick.with_skill("api")

        # Should still work normally
        import asyncio

        result = asyncio.run(api_brick.invoke(7))
        assert result == 21


class TestCliSkill:
    """Test the CLI skill."""

    def test_cli_creation(self):
        """Test CLI app creation."""

        class TestNanobrick(Nanobrick[str, str]):
            """A test brick that reverses strings."""

            async def invoke(self, input: str, *, deps=None) -> str:
                return input[::-1]

        brick = TestNanobrick()
        # Create without auto_create to avoid import issues in test
        cli_brick = brick.with_skill("cli", command="reverse", auto_create=False)

        # Check that enhanced brick has CLI methods
        assert hasattr(cli_brick, "create_cli")
        assert hasattr(cli_brick, "run_cli")

        # Now test creating the CLI
        app = cli_brick.create_cli()
        assert app is not None

    def test_cli_config(self):
        """Test CLI configuration."""

        class TestNanobrick(Nanobrick[dict, dict]):
            async def invoke(self, input: dict, *, deps=None) -> dict:
                return {"result": input}

        brick = TestNanobrick()
        cli_brick = brick.with_skill(
            "cli",
            command="process",
            description="Process data",
            input_type="json",
            output_format="pretty",
            auto_create=False,
        )

        # Check configuration
        assert cli_brick._skill.config["command"] == "process"
        assert cli_brick._skill.config["description"] == "Process data"
        assert cli_brick._skill.config["input_type"] == "json"
        assert cli_brick._skill.config["output_format"] == "pretty"

    def test_cli_normal_invocation(self):
        """Test that normal invocation still works."""

        class TestNanobrick(Nanobrick[list, int]):
            async def invoke(self, input: list, *, deps=None) -> int:
                return sum(input)

        brick = TestNanobrick()
        cli_brick = brick.with_skill("cli", auto_create=False)

        # Should still work normally
        import asyncio

        result = asyncio.run(cli_brick.invoke([1, 2, 3, 4, 5]))
        assert result == 15


class TestSkillIntegration:
    """Test multiple skills together."""

    def test_multiple_skills(self, caplog):
        """Test combining multiple skills."""

        @skill("logging", level="INFO")
        class ProcessBrick(Nanobrick[str, dict]):
            """Processes text into statistics."""

            async def invoke(self, input: str, *, deps=None) -> dict:
                return {
                    "length": len(input),
                    "words": len(input.split()),
                    "uppercase": input.upper(),
                }

        # Add more skills
        brick = ProcessBrick()
        enhanced = brick.with_skill("api", path="/process")

        # Test normal invocation with logging
        import asyncio

        with caplog.at_level(logging.INFO):
            result = asyncio.run(enhanced.invoke("hello world"))

        assert result["length"] == 11
        assert result["words"] == 2
        assert result["uppercase"] == "HELLO WORLD"

        # Check logging happened
        assert any("Input: hello world" in record.message for record in caplog.records)
        assert any(
            "Output:" in record.message and "HELLO WORLD" in record.message
            for record in caplog.records
        )
