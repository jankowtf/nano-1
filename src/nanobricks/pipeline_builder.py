"""Pipeline Builder for fluent composition of nanobricks.

This module provides a fluent interface for building complex pipelines
with branching, merging, type adaptation, and error handling.
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from functools import reduce
import asyncio

from beartype import beartype

from nanobricks.protocol import NanobrickBase, NanobrickProtocol, Nanobrick
from nanobricks.composition import NanobrickComposite
from nanobricks.typing import TypeAdapter, auto_adapter, check_type_compatibility

T_in = TypeVar("T_in")
T_out = TypeVar("T_out")
T_deps = TypeVar("T_deps")
T_branch = TypeVar("T_branch")


class BranchCondition(NanobrickBase[T_in, Tuple[str, T_in], None]):
    """A nanobrick that evaluates conditions for branching."""

    def __init__(
        self,
        name: str,
        conditions: List[Tuple[str, Callable[[T_in], bool]]],
        default: str = "default",
    ):
        self.name = name
        self.version = "1.0.0"
        self.conditions = conditions
        self.default = default

    async def invoke(
        self, input: T_in, *, deps: None = None
    ) -> Tuple[str, T_in]:
        """Evaluate conditions and return branch name with input."""
        for branch_name, condition in self.conditions:
            if condition(input):
                return branch_name, input
        return self.default, input


class BranchExecutor(NanobrickBase[Tuple[str, T_in], T_out, T_deps]):
    """A nanobrick that executes different branches based on condition."""

    def __init__(
        self,
        name: str,
        branches: Dict[str, NanobrickProtocol[T_in, T_out, T_deps]],
    ):
        self.name = name
        self.version = "1.0.0"
        self.branches = branches

    async def invoke(
        self, input: Tuple[str, T_in], *, deps: T_deps | None = None
    ) -> T_out:
        """Execute the appropriate branch based on input."""
        branch_name, value = input
        if branch_name not in self.branches:
            raise ValueError(f"No branch defined for: {branch_name}")
        return await self.branches[branch_name].invoke(value, deps=deps)


class ParallelExecutor(NanobrickBase[T_in, List[Any], T_deps]):
    """A nanobrick that executes multiple bricks in parallel."""

    def __init__(
        self,
        name: str,
        bricks: List[NanobrickProtocol[T_in, Any, T_deps]],
    ):
        self.name = name
        self.version = "1.0.0"
        self.bricks = bricks

    async def invoke(
        self, input: T_in, *, deps: T_deps | None = None
    ) -> List[Any]:
        """Execute all bricks in parallel and collect results."""
        tasks = [brick.invoke(input, deps=deps) for brick in self.bricks]
        results = await asyncio.gather(*tasks)
        return list(results)


class ErrorCatcher(NanobrickBase[T_in, Union[T_out, Any], T_deps]):
    """A nanobrick that catches errors and handles them."""

    def __init__(
        self,
        name: str,
        brick: NanobrickProtocol[T_in, T_out, T_deps],
        error_handler: NanobrickProtocol[Exception, Any, T_deps],
        catch_types: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.version = "1.0.0"
        self.brick = brick
        self.error_handler = error_handler
        self.catch_types = catch_types

    async def invoke(
        self, input: T_in, *, deps: T_deps | None = None
    ) -> Union[T_out, Any]:
        """Execute brick with error catching."""
        try:
            return await self.brick.invoke(input, deps=deps)
        except self.catch_types as e:
            return await self.error_handler.invoke(e, deps=deps)


class PipelineBuilder:
    """Fluent interface for building complex nanobrick pipelines.
    
    Examples:
        Basic pipeline:
        ```python
        pipeline = (
            Pipeline()
            .start_with(Parser())
            .then(Validator())
            .then(Formatter())
            .build()
        )
        ```
        
        With type adaptation:
        ```python
        pipeline = (
            Pipeline()
            .start_with(LoadJSON())
            .adapt(json_to_dict())
            .then(ProcessDict())
            .build()
        )
        ```
        
        With branching:
        ```python
        pipeline = (
            Pipeline()
            .start_with(Parser())
            .branch(
                ("email", EmailValidator() >> EmailFormatter()),
                ("phone", PhoneValidator() >> PhoneFormatter()),
                ("default", PassthroughValidator())
            )
            .build()
        )
        ```
    """

    def __init__(self):
        """Initialize a new pipeline builder."""
        self._steps: List[NanobrickProtocol[Any, Any, Any]] = []
        self._name: Optional[str] = None

    def start_with(
        self, brick: NanobrickProtocol[T_in, T_out, T_deps]
    ) -> "PipelineBuilder":
        """Start the pipeline with a nanobrick.
        
        Args:
            brick: The first brick in the pipeline
            
        Returns:
            Self for chaining
        """
        if self._steps:
            raise ValueError("Pipeline already started. Use 'then' to add more steps.")
        self._steps.append(brick)
        return self

    def then(
        self, brick: NanobrickProtocol[Any, Any, Any]
    ) -> "PipelineBuilder":
        """Add a nanobrick to the pipeline.
        
        Args:
            brick: The next brick in the pipeline
            
        Returns:
            Self for chaining
        """
        if not self._steps:
            raise ValueError("Pipeline not started. Use 'start_with' first.")
        self._steps.append(brick)
        return self

    def adapt(
        self,
        adapter: Union[TypeAdapter[Any, Any], Callable[[Any], Any]],
        name: Optional[str] = None,
    ) -> "PipelineBuilder":
        """Add a type adapter to the pipeline.
        
        Args:
            adapter: Either a TypeAdapter or a conversion function
            name: Optional name for the adapter
            
        Returns:
            Self for chaining
        """
        if not self._steps:
            raise ValueError("Pipeline not started. Use 'start_with' first.")
            
        if isinstance(adapter, TypeAdapter):
            self._steps.append(adapter)
        else:
            # Create a simple adapter brick from the function
            adapter_brick = TypeAdapter(
                name=name or "custom_adapter",
                converter=adapter,
                input_type=Any,
                output_type=Any,
            )
            self._steps.append(adapter_brick)
        return self

    def branch(
        self,
        *branches: Tuple[str, NanobrickProtocol[Any, Any, Any]],
        condition_func: Optional[Callable[[Any], str]] = None,
    ) -> "PipelineBuilder":
        """Add conditional branching to the pipeline.
        
        Args:
            *branches: Tuples of (branch_name, brick) for each branch
            condition_func: Optional function to determine branch (defaults to checking 'type' field)
            
        Returns:
            Self for chaining
        """
        if not self._steps:
            raise ValueError("Pipeline not started. Use 'start_with' first.")
            
        if not branches:
            raise ValueError("At least one branch must be provided.")
            
        # Create branch dictionary
        branch_dict = dict(branches)
        
        # Default condition function
        if condition_func is None:
            def default_condition(input: Any) -> str:
                if hasattr(input, "type"):
                    return input.type
                elif isinstance(input, dict) and "type" in input:
                    return input["type"]
                return "default"
            condition_func = default_condition
            
        # Create conditions for BranchCondition
        conditions = [
            (name, lambda x, n=name: condition_func(x) == n)
            for name in branch_dict.keys()
            if name != "default"
        ]
        
        # Add branching bricks
        condition_brick = BranchCondition(
            name="branch_condition",
            conditions=conditions,
            default="default" if "default" in branch_dict else list(branch_dict.keys())[0],
        )
        executor_brick = BranchExecutor(
            name="branch_executor",
            branches=branch_dict,
        )
        
        self._steps.extend([condition_brick, executor_brick])
        return self

    def parallel(
        self, *bricks: NanobrickProtocol[Any, Any, Any]
    ) -> "PipelineBuilder":
        """Execute multiple bricks in parallel.
        
        Args:
            *bricks: Bricks to execute in parallel
            
        Returns:
            Self for chaining
        """
        if not self._steps:
            raise ValueError("Pipeline not started. Use 'start_with' first.")
            
        if not bricks:
            raise ValueError("At least one brick must be provided for parallel execution.")
            
        parallel_brick = ParallelExecutor(
            name="parallel_executor",
            bricks=list(bricks),
        )
        self._steps.append(parallel_brick)
        return self

    def merge_with(
        self, merger: NanobrickProtocol[List[Any], Any, Any]
    ) -> "PipelineBuilder":
        """Merge results from parallel execution or branching.
        
        Args:
            merger: Brick that combines multiple results into one
            
        Returns:
            Self for chaining
        """
        if not self._steps:
            raise ValueError("Pipeline not started. Use 'start_with' first.")
        self._steps.append(merger)
        return self

    def catch_errors(
        self,
        error_handler: NanobrickProtocol[Exception, Any, Any],
        catch_types: Tuple[Type[Exception], ...] = (Exception,),
    ) -> "PipelineBuilder":
        """Add error catching to the previous step.
        
        Args:
            error_handler: Brick that handles caught exceptions
            catch_types: Types of exceptions to catch
            
        Returns:
            Self for chaining
        """
        if not self._steps:
            raise ValueError("Pipeline not started. Use 'start_with' first.")
            
        if len(self._steps) < 1:
            raise ValueError("No previous step to add error catching to.")
            
        # Wrap the last step with error catching
        last_step = self._steps.pop()
        error_catcher = ErrorCatcher(
            name=f"{last_step.name}_with_error_catching",
            brick=last_step,
            error_handler=error_handler,
            catch_types=catch_types,
        )
        self._steps.append(error_catcher)
        return self

    def auto_adapt(self) -> "PipelineBuilder":
        """Automatically insert type adapters where needed.
        
        This will analyze the pipeline and insert adapters between
        incompatible types where possible.
        
        Returns:
            Self for chaining
        """
        if len(self._steps) < 2:
            return self
            
        # Build new steps with auto-adapters
        new_steps = [self._steps[0]]
        
        for i in range(1, len(self._steps)):
            prev_step = new_steps[-1]
            next_step = self._steps[i]
            
            # Try to determine types (this is simplified, real implementation would be more robust)
            # For now, we'll skip auto-adaptation and let users be explicit
            # TODO: Implement proper type introspection
            
            new_steps.append(next_step)
            
        self._steps = new_steps
        return self

    def name(self, name: str) -> "PipelineBuilder":
        """Set a custom name for the pipeline.
        
        Args:
            name: The name for the built pipeline
            
        Returns:
            Self for chaining
        """
        self._name = name
        return self

    def build(self) -> NanobrickProtocol[Any, Any, Any]:
        """Build the final pipeline.
        
        Returns:
            A nanobrick representing the complete pipeline
        """
        if not self._steps:
            raise ValueError("Cannot build empty pipeline.")
            
        if len(self._steps) == 1:
            return self._steps[0]
            
        # Compose all steps using the >> operator
        pipeline = reduce(lambda a, b: a >> b, self._steps)
        
        # Set custom name if provided
        if self._name and hasattr(pipeline, "name"):
            pipeline.name = self._name
            
        return pipeline

    def visualize(self) -> str:
        """Generate a text visualization of the pipeline.
        
        Returns:
            A string representation of the pipeline structure
        """
        if not self._steps:
            return "Empty pipeline"
            
        lines = ["Pipeline Visualization:", "=" * 50]
        
        for i, step in enumerate(self._steps):
            prefix = "┌─" if i == 0 else "├─"
            if i == len(self._steps) - 1:
                prefix = "└─"
                
            if isinstance(step, BranchCondition):
                lines.append(f"{prefix} [Branch Condition]")
            elif isinstance(step, BranchExecutor):
                lines.append(f"{prefix} [Branch Executor]")
                for branch_name in step.branches:
                    lines.append(f"   ├─ {branch_name}: {step.branches[branch_name].name}")
            elif isinstance(step, ParallelExecutor):
                lines.append(f"{prefix} [Parallel Execution]")
                for brick in step.bricks:
                    lines.append(f"   ├─ {brick.name}")
            elif isinstance(step, ErrorCatcher):
                lines.append(f"{prefix} {step.brick.name} [with error catching]")
            else:
                lines.append(f"{prefix} {step.name}")
                
        return "\n".join(lines)

    def explain(self) -> str:
        """Generate a detailed explanation of the pipeline.
        
        Returns:
            A string explaining each step and type transformations
        """
        if not self._steps:
            return "Empty pipeline - no steps to explain"
            
        lines = ["Pipeline Explanation:", "=" * 50]
        
        for i, step in enumerate(self._steps):
            lines.append(f"\nStep {i + 1}: {step.name}")
            lines.append("-" * 30)
            
            if isinstance(step, TypeAdapter):
                lines.append(f"Type adapter: {step.input_type.__name__} → {step.output_type.__name__}")
            elif isinstance(step, BranchCondition):
                lines.append("Evaluates conditions to determine execution branch")
            elif isinstance(step, BranchExecutor):
                lines.append("Executes the appropriate branch based on condition")
                lines.append("Branches:")
                for branch_name in step.branches:
                    lines.append(f"  - {branch_name}: {step.branches[branch_name].name}")
            elif isinstance(step, ParallelExecutor):
                lines.append("Executes multiple bricks in parallel")
                lines.append("Parallel bricks:")
                for brick in step.bricks:
                    lines.append(f"  - {brick.name}")
            elif isinstance(step, ErrorCatcher):
                lines.append(f"Executes {step.brick.name} with error catching")
                lines.append(f"Error handler: {step.error_handler.name}")
            else:
                lines.append(f"Executes: {step.name}")
                if hasattr(step, "__doc__") and step.__doc__:
                    lines.append(f"Description: {step.__doc__.strip().split('.')[0]}")
                    
        return "\n".join(lines)


# Convenience function
def Pipeline() -> PipelineBuilder:
    """Create a new pipeline builder.
    
    Returns:
        A new PipelineBuilder instance
    """
    return PipelineBuilder()