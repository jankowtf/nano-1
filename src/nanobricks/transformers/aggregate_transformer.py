"""Aggregation transformation nanobricks for reducing collections."""

from collections.abc import Callable, Iterable
from typing import TypeVar, Union

from nanobricks.transformers.base import TransformerBrick

T = TypeVar("T")
U = TypeVar("U")


class SumTransformer(TransformerBrick[Iterable[int | float], Union[int, float], None]):
    """Calculate sum of numeric values."""

    async def transform(self, input: Iterable[int | float]) -> int | float:
        """Calculate sum of input values.

        Args:
            input: Collection of numeric values

        Returns:
            Sum of all values, 0 if empty
        """
        if not input:
            return 0

        try:
            return sum(input)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot sum non-numeric values: {e}")


class AverageTransformer(TransformerBrick[Iterable[int | float], float, None]):
    """Calculate average of numeric values."""

    async def transform(self, input: Iterable[int | float]) -> float:
        """Calculate average of input values.

        Args:
            input: Collection of numeric values

        Returns:
            Average of all values

        Raises:
            ValueError: If input is empty or contains non-numeric values
        """
        values = list(input) if input else []

        if not values:
            raise ValueError("Cannot calculate average of empty collection")

        try:
            return sum(values) / len(values)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot average non-numeric values: {e}")


class MinTransformer(TransformerBrick[Iterable[T], T, None]):
    """Find minimum value in collection."""

    def __init__(self, key: Callable[[T], any] = None, name: str = None):
        """Initialize with optional key function.

        Args:
            key: Function to extract comparison key from items
            name: Optional custom name
        """
        super().__init__(name)
        self.key = key

    async def transform(self, input: Iterable[T]) -> T:
        """Find minimum value in input.

        Args:
            input: Collection to search

        Returns:
            Minimum value

        Raises:
            ValueError: If input is empty
        """
        values = list(input) if input else []

        if not values:
            raise ValueError("Cannot find min of empty collection")

        try:
            return min(values, key=self.key)
        except Exception as e:
            raise ValueError(f"Error finding minimum: {e}")


class MaxTransformer(TransformerBrick[Iterable[T], T, None]):
    """Find maximum value in collection."""

    def __init__(self, key: Callable[[T], any] = None, name: str = None):
        """Initialize with optional key function.

        Args:
            key: Function to extract comparison key from items
            name: Optional custom name
        """
        super().__init__(name)
        self.key = key

    async def transform(self, input: Iterable[T]) -> T:
        """Find maximum value in input.

        Args:
            input: Collection to search

        Returns:
            Maximum value

        Raises:
            ValueError: If input is empty
        """
        values = list(input) if input else []

        if not values:
            raise ValueError("Cannot find max of empty collection")

        try:
            return max(values, key=self.key)
        except Exception as e:
            raise ValueError(f"Error finding maximum: {e}")


class CountTransformer(TransformerBrick[Iterable[T], int, None]):
    """Count elements in collection."""

    def __init__(self, predicate: Callable[[T], bool] = None, name: str = None):
        """Initialize with optional predicate.

        Args:
            predicate: Optional function to filter items before counting
            name: Optional custom name
        """
        super().__init__(name)
        self.predicate = predicate

    async def transform(self, input: Iterable[T]) -> int:
        """Count elements in input.

        Args:
            input: Collection to count

        Returns:
            Number of elements (matching predicate if provided)
        """
        if not input:
            return 0

        if self.predicate:
            return sum(1 for item in input if self.predicate(item))
        else:
            # Try to use len() for efficiency if possible
            try:
                return len(input)  # type: ignore
            except TypeError:
                # Fallback for iterables without len()
                return sum(1 for _ in input)


class ReduceTransformer(TransformerBrick[Iterable[T], U, None]):
    """Reduce collection to single value using custom function."""

    def __init__(self, func: Callable[[U, T], U], initial: U, name: str = None):
        """Initialize with reduce function and initial value.

        Args:
            func: Binary function to combine accumulator and current value
            initial: Initial accumulator value
            name: Optional custom name
        """
        super().__init__(name)
        self.func = func
        self.initial = initial

    async def transform(self, input: Iterable[T]) -> U:
        """Reduce input to single value.

        Args:
            input: Collection to reduce

        Returns:
            Reduced value
        """
        if not input:
            return self.initial

        accumulator = self.initial
        try:
            for item in input:
                accumulator = self.func(accumulator, item)
        except Exception as e:
            raise ValueError(f"Error reducing collection: {e}")

        return accumulator


class JoinTransformer(TransformerBrick[Iterable[str], str, None]):
    """Join string collection into single string."""

    def __init__(self, separator: str = "", name: str = None):
        """Initialize with separator.

        Args:
            separator: String to insert between elements
            name: Optional custom name
        """
        super().__init__(name)
        self.separator = separator

    async def transform(self, input: Iterable[str]) -> str:
        """Join strings in input.

        Args:
            input: Collection of strings to join

        Returns:
            Joined string
        """
        if not input:
            return ""

        try:
            return self.separator.join(str(item) for item in input)
        except Exception as e:
            raise ValueError(f"Error joining strings: {e}")


class FrequencyTransformer(TransformerBrick[Iterable[T], dict[T, int], None]):
    """Count frequency of each unique element."""

    async def transform(self, input: Iterable[T]) -> dict[T, int]:
        """Count frequency of elements in input.

        Args:
            input: Collection to analyze

        Returns:
            Dictionary mapping elements to their counts
        """
        if not input:
            return {}

        frequencies: dict[T, int] = {}

        for item in input:
            try:
                frequencies[item] = frequencies.get(item, 0) + 1
            except TypeError:
                # Handle unhashable types by converting to string
                key = str(item)  # type: ignore
                frequencies[key] = frequencies.get(key, 0) + 1  # type: ignore

        return frequencies
