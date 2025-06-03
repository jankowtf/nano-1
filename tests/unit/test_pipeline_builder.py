"""Unit tests for the PipelineBuilder fluent interface."""

import pytest
from typing import Dict, List, Any

from nanobricks import Nanobrick, PipelineBuilder
from nanobricks.pipeline_builder import (
    Pipeline as PipelineFunction,
    BranchCondition,
    BranchExecutor,
    ParallelExecutor,
    ErrorCatcher,
)
from nanobricks.typing import TypeAdapter, string_to_dict


class TestPipelineBuilder:
    """Test the PipelineBuilder fluent interface."""

    @pytest.fixture
    def parser_brick(self):
        """A brick that parses input."""
        class Parser(Nanobrick[str, Dict[str, str]]):
            async def invoke(self, input: str, *, deps=None) -> Dict[str, str]:
                parts = input.split(",")
                return {"type": parts[0], "content": parts[1] if len(parts) > 1 else ""}
        return Parser(name="parser")

    @pytest.fixture
    def validator_brick(self):
        """A brick that validates input."""
        class Validator(Nanobrick[Dict[str, str], Dict[str, str]]):
            async def invoke(self, input: Dict[str, str], *, deps=None) -> Dict[str, str]:
                if not input.get("type"):
                    raise ValueError("Missing type field")
                return {**input, "validated": "true"}
        return Validator(name="validator")

    @pytest.fixture
    def formatter_brick(self):
        """A brick that formats output."""
        class Formatter(Nanobrick[Dict[str, str], str]):
            async def invoke(self, input: Dict[str, str], *, deps=None) -> str:
                return f"{input['type']}: {input.get('content', 'N/A')}"
        return Formatter(name="formatter")

    async def test_basic_pipeline(self, parser_brick, validator_brick, formatter_brick):
        """Test building a basic linear pipeline."""
        pipeline = (
            PipelineFunction()
            .start_with(parser_brick)
            .then(validator_brick)
            .then(formatter_brick)
            .build()
        )

        result = await pipeline.invoke("email,test@example.com")
        assert result == "email: test@example.com"

    async def test_pipeline_with_adapter(self):
        """Test pipeline with type adapter."""
        class StringProcessor(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        class DictProcessor(Nanobrick[Dict[str, str], str]):
            async def invoke(self, input: Dict[str, str], *, deps=None) -> str:
                return f"Processed: {input}"

        pipeline = (
            PipelineFunction()
            .start_with(StringProcessor(name="string_proc"))
            .adapt(string_to_dict())
            .then(DictProcessor(name="dict_proc"))
            .build()
        )

        result = await pipeline.invoke("key1=value1,key2=value2")
        # The string processor makes it uppercase, so we need to check for uppercase keys
        assert "KEY1" in result
        assert "VALUE1" in result

    async def test_pipeline_with_custom_adapter(self):
        """Test pipeline with custom adapter function."""
        class NumberBrick(Nanobrick[int, int]):
            async def invoke(self, input: int, *, deps=None) -> int:
                return input * 2

        class StringBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return f"Result: {input}"

        pipeline = (
            PipelineFunction()
            .start_with(NumberBrick(name="doubler"))
            .adapt(lambda x: str(x), name="int_to_str")
            .then(StringBrick(name="formatter"))
            .build()
        )

        result = await pipeline.invoke(5)
        assert result == "Result: 10"

    async def test_branching_pipeline(self, parser_brick):
        """Test pipeline with conditional branching."""
        class EmailProcessor(Nanobrick[Dict[str, str], str]):
            async def invoke(self, input: Dict[str, str], *, deps=None) -> str:
                return f"Email processed: {input['content']}"

        class PhoneProcessor(Nanobrick[Dict[str, str], str]):
            async def invoke(self, input: Dict[str, str], *, deps=None) -> str:
                return f"Phone processed: {input['content']}"

        class DefaultProcessor(Nanobrick[Dict[str, str], str]):
            async def invoke(self, input: Dict[str, str], *, deps=None) -> str:
                return f"Default processed: {input['content']}"

        pipeline = (
            PipelineFunction()
            .start_with(parser_brick)
            .branch(
                ("email", EmailProcessor(name="email_proc")),
                ("phone", PhoneProcessor(name="phone_proc")),
                ("default", DefaultProcessor(name="default_proc"))
            )
            .build()
        )

        # Test email branch
        result = await pipeline.invoke("email,test@example.com")
        assert result == "Email processed: test@example.com"

        # Test phone branch
        result = await pipeline.invoke("phone,555-1234")
        assert result == "Phone processed: 555-1234"

        # Test default branch
        result = await pipeline.invoke("other,some data")
        assert result == "Default processed: some data"

    async def test_parallel_execution(self):
        """Test pipeline with parallel execution."""
        class Analyzer1(Nanobrick[str, int]):
            async def invoke(self, input: str, *, deps=None) -> int:
                return len(input)

        class Analyzer2(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        class Analyzer3(Nanobrick[str, bool]):
            async def invoke(self, input: str, *, deps=None) -> bool:
                return "test" in input.lower()

        class ResultMerger(Nanobrick[List[Any], Dict[str, Any]]):
            async def invoke(self, input: List[Any], *, deps=None) -> Dict[str, Any]:
                return {
                    "length": input[0],
                    "uppercase": input[1],
                    "has_test": input[2]
                }

        class IdentityBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input

        pipeline = (
            PipelineFunction()
            .start_with(IdentityBrick(name="identity"))
            .parallel(
                Analyzer1(name="length_analyzer"),
                Analyzer2(name="case_analyzer"),
                Analyzer3(name="content_analyzer")
            )
            .merge_with(ResultMerger(name="merger"))
            .build()
        )

        result = await pipeline.invoke("This is a test string")
        assert result["length"] == 21
        assert result["uppercase"] == "THIS IS A TEST STRING"
        assert result["has_test"] is True

    async def test_error_handling(self):
        """Test pipeline with error catching."""
        class FaultyBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                if input == "error":
                    raise ValueError("Intentional error")
                return input.upper()

        class ErrorHandler(Nanobrick[Exception, str]):
            async def invoke(self, input: Exception, *, deps=None) -> str:
                return f"Error caught: {str(input)}"

        pipeline = (
            PipelineFunction()
            .start_with(FaultyBrick(name="faulty"))
            .catch_errors(ErrorHandler(name="error_handler"), catch_types=(ValueError,))
            .build()
        )

        # Test normal case
        result = await pipeline.invoke("hello")
        assert result == "HELLO"

        # Test error case
        result = await pipeline.invoke("error")
        assert result == "Error caught: Intentional error"

    def test_pipeline_name(self, parser_brick, formatter_brick):
        """Test setting custom pipeline name."""
        pipeline = (
            PipelineFunction()
            .start_with(parser_brick)
            .then(formatter_brick)
            .name("MyCustomPipeline")
            .build()
        )

        assert pipeline.name == "MyCustomPipeline"

    def test_visualize(self, parser_brick, validator_brick, formatter_brick):
        """Test pipeline visualization."""
        builder = (
            PipelineFunction()
            .start_with(parser_brick)
            .then(validator_brick)
            .then(formatter_brick)
        )

        viz = builder.visualize()
        assert "Pipeline Visualization:" in viz
        assert "parser" in viz
        assert "validator" in viz
        assert "formatter" in viz

    def test_explain(self, parser_brick, validator_brick):
        """Test pipeline explanation."""
        builder = (
            PipelineFunction()
            .start_with(parser_brick)
            .adapt(lambda x: x, name="identity")
            .then(validator_brick)
        )

        explanation = builder.explain()
        assert "Pipeline Explanation:" in explanation
        assert "Step 1: parser" in explanation
        assert "Step 2: identity" in explanation
        assert "Step 3: validator" in explanation

    def test_empty_pipeline_error(self):
        """Test that empty pipeline cannot be built."""
        builder = PipelineFunction()
        
        with pytest.raises(ValueError, match="Cannot build empty pipeline"):
            builder.build()

    def test_start_with_required(self, parser_brick):
        """Test that start_with must be called first."""
        builder = PipelineFunction()
        
        with pytest.raises(ValueError, match="Pipeline not started"):
            builder.then(parser_brick)

    def test_already_started_error(self, parser_brick):
        """Test that start_with cannot be called twice."""
        builder = PipelineFunction().start_with(parser_brick)
        
        with pytest.raises(ValueError, match="Pipeline already started"):
            builder.start_with(parser_brick)

    async def test_complex_pipeline(self):
        """Test a complex pipeline with multiple features."""
        # Define bricks
        class InputParser(Nanobrick[str, Dict[str, Any]]):
            async def invoke(self, input: str, *, deps=None) -> Dict[str, Any]:
                import json
                return json.loads(input)

        class TypeValidator(Nanobrick[Dict[str, Any], Dict[str, Any]]):
            async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
                if "type" not in input:
                    raise ValueError("Missing type field")
                return input

        class EmailEnricher(Nanobrick[Dict[str, Any], Dict[str, Any]]):
            async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
                if isinstance(input, str):
                    # Handle the case where we get a string from error handler
                    return {"error": input}
                return {**input, "domain": input["email"].split("@")[1]}

        class PhoneEnricher(Nanobrick[Dict[str, Any], Dict[str, Any]]):
            async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
                return {**input, "country_code": "+1"}

        class OutputFormatter(Nanobrick[Dict[str, Any], str]):
            async def invoke(self, input: Dict[str, Any], *, deps=None) -> str:
                import json
                return json.dumps(input, indent=2)

        class ErrorFormatter(Nanobrick[Exception, str]):
            async def invoke(self, input: Exception, *, deps=None) -> str:
                return f"ERROR: {str(input)}"

        # Build complex pipeline
        pipeline = (
            PipelineFunction()
            .start_with(InputParser(name="json_parser"))
            .then(TypeValidator(name="type_validator"))
            .branch(
                ("email", EmailEnricher(name="email_enricher")),
                ("phone", PhoneEnricher(name="phone_enricher"))
            )
            .then(OutputFormatter(name="json_formatter"))
            .name("ComplexDataPipeline")
            .build()
        )

        # Test email path
        email_input = '{"type": "email", "email": "user@example.com"}'
        result = await pipeline.invoke(email_input)
        assert "domain" in result
        assert "example.com" in result

        # Test phone path
        phone_input = '{"type": "phone", "phone": "555-1234"}'
        result = await pipeline.invoke(phone_input)
        assert "country_code" in result
        assert "+1" in result

        # Test error handling - missing type field will raise ValueError
        invalid_input = '{"no_type": "here"}'
        with pytest.raises(ValueError, match="Missing type field"):
            result = await pipeline.invoke(invalid_input)


class TestPipelineBuilderComponents:
    """Test individual PipelineBuilder components."""

    async def test_branch_condition(self):
        """Test BranchCondition component."""
        conditions = [
            ("email", lambda x: x.get("type") == "email"),
            ("phone", lambda x: x.get("type") == "phone"),
        ]
        
        brick = BranchCondition(
            name="branch_test",
            conditions=conditions,
            default="other"
        )

        # Test email condition
        branch, value = await brick.invoke({"type": "email", "data": "test"})
        assert branch == "email"
        assert value["data"] == "test"

        # Test default condition
        branch, value = await brick.invoke({"type": "unknown", "data": "test"})
        assert branch == "other"

    async def test_branch_executor(self):
        """Test BranchExecutor component."""
        class UpperBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.upper()

        class LowerBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input.lower()

        branches = {
            "upper": UpperBrick(name="upper"),
            "lower": LowerBrick(name="lower"),
        }
        
        executor = BranchExecutor(name="executor_test", branches=branches)

        # Test upper branch
        result = await executor.invoke(("upper", "Hello World"))
        assert result == "HELLO WORLD"

        # Test lower branch
        result = await executor.invoke(("lower", "Hello World"))
        assert result == "hello world"

        # Test missing branch
        with pytest.raises(ValueError, match="No branch defined for: missing"):
            await executor.invoke(("missing", "test"))

    async def test_parallel_executor(self):
        """Test ParallelExecutor component."""
        class CountBrick(Nanobrick[str, int]):
            async def invoke(self, input: str, *, deps=None) -> int:
                return len(input)

        class ReverseBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                return input[::-1]

        executor = ParallelExecutor(
            name="parallel_test",
            bricks=[CountBrick(name="count"), ReverseBrick(name="reverse")]
        )

        results = await executor.invoke("hello")
        assert results == [5, "olleh"]

    async def test_error_catcher(self):
        """Test ErrorCatcher component."""
        class FaultyBrick(Nanobrick[int, int]):
            async def invoke(self, input: int, *, deps=None) -> int:
                if input < 0:
                    raise ValueError("Negative not allowed")
                return input * 2

        class ErrorBrick(Nanobrick[Exception, str]):
            async def invoke(self, input: Exception, *, deps=None) -> str:
                return f"Handled: {input}"

        catcher = ErrorCatcher(
            name="catcher_test",
            brick=FaultyBrick(name="faulty"),
            error_handler=ErrorBrick(name="handler"),
            catch_types=(ValueError,)
        )

        # Test normal case
        result = await catcher.invoke(5)
        assert result == 10

        # Test error case
        result = await catcher.invoke(-5)
        assert result == "Handled: Negative not allowed"