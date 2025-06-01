"""Map transformation nanobricks for applying functions to collections."""

from collections.abc import Callable, Iterable
from typing import TypeVar, Union

from nanobricks.transformers.base import TransformerBrick

T = TypeVar("T")
U = TypeVar("U")


class MapTransformer(TransformerBrick[Iterable[T], list[U], None]):
    """Apply a function to each element in a collection."""

    def __init__(self, func: Callable[[T], U], name: str = None):
        """Initialize with mapping function.

        Args:
            func: Function to apply to each element
            name: Optional custom name
        """
        super().__init__(name)
        self.func = func

    async def transform(self, input: Iterable[T]) -> list[U]:
        """Apply function to each element.

        Args:
            input: Collection to map over

        Returns:
            List of transformed elements
        """
        if not input:
            return []

        try:
            return [self.func(item) for item in input]
        except Exception as e:
            raise ValueError(f"Error mapping collection: {e}")


class SelectTransformer(TransformerBrick[Iterable[dict[str, T]], list[T], None]):
    """Select a specific field from dictionaries in a collection."""

    def __init__(self, field: str, default: T = None, name: str = None):
        """Initialize with field to select.

        Args:
            field: Field name to select from each dictionary
            default: Default value if field is missing
            name: Optional custom name
        """
        super().__init__(name)
        self.field = field
        self.default = default

    async def transform(self, input: Iterable[dict[str, T]]) -> list[T]:
        """Select field from each dictionary.

        Args:
            input: Collection of dictionaries

        Returns:
            List of selected field values
        """
        if not input:
            return []

        result = []
        for item in input:
            if isinstance(item, dict):
                result.append(item.get(self.field, self.default))
            else:
                raise ValueError(f"Expected dict, got {type(item).__name__}")

        return result


class FlatMapTransformer(TransformerBrick[Iterable[T], list[U], None]):
    """Apply a function that returns an iterable and flatten the results."""

    def __init__(self, func: Callable[[T], Iterable[U]], name: str = None):
        """Initialize with mapping function.

        Args:
            func: Function that returns an iterable for each element
            name: Optional custom name
        """
        super().__init__(name)
        self.func = func

    async def transform(self, input: Iterable[T]) -> list[U]:
        """Apply function and flatten results.

        Args:
            input: Collection to flat map over

        Returns:
            Flattened list of all results
        """
        if not input:
            return []

        result = []
        try:
            for item in input:
                sub_results = self.func(item)
                if sub_results:
                    result.extend(sub_results)
        except Exception as e:
            raise ValueError(f"Error flat mapping collection: {e}")

        return result


class GroupByTransformer(TransformerBrick[Iterable[T], dict[str, list[T]], None]):
    """Group elements by a key function."""

    def __init__(self, key_func: Callable[[T], str], name: str = None):
        """Initialize with key function.

        Args:
            key_func: Function to extract grouping key from each element
            name: Optional custom name
        """
        super().__init__(name)
        self.key_func = key_func

    async def transform(self, input: Iterable[T]) -> dict[str, list[T]]:
        """Group elements by key function.

        Args:
            input: Collection to group

        Returns:
            Dictionary mapping keys to lists of elements
        """
        if not input:
            return {}

        groups: dict[str, list[T]] = {}

        try:
            for item in input:
                key = self.key_func(item)
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)
        except Exception as e:
            raise ValueError(f"Error grouping collection: {e}")

        return groups


class ZipTransformer(
    TransformerBrick[Union[list[Iterable[T]], Iterable[T]], list[tuple], None]
):
    """Zip multiple iterables together."""

    def __init__(self, *additional_iterables: Iterable[T], name: str = None):
        """Initialize with optional additional iterables.

        Args:
            additional_iterables: Additional iterables to zip with input
            name: Optional custom name
        """
        super().__init__(name)
        self.additional_iterables = additional_iterables

    async def transform(self, input: list[Iterable[T]] | Iterable[T]) -> list[tuple]:
        """Zip iterables together.

        Args:
            input: Single iterable or list of iterables to zip

        Returns:
            List of tuples from zipped iterables
        """
        if not input:
            return []

        # Handle different input types
        if isinstance(input, list) and all(hasattr(item, "__iter__") for item in input):
            # Input is already a list of iterables
            iterables = input
        else:
            # Input is a single iterable
            iterables = [input]

        # Add any additional iterables
        if self.additional_iterables:
            iterables.extend(self.additional_iterables)

        try:
            return list(zip(*iterables, strict=False))
        except Exception as e:
            raise ValueError(f"Error zipping iterables: {e}")
