"""Filter transformation nanobricks for collections."""

from collections.abc import Callable, Iterable
from typing import TypeVar

from nanobricks.transformers.base import TransformerBrick

T = TypeVar("T")


class FilterTransformer(TransformerBrick[Iterable[T], list[T], None]):
    """Filter collections based on predicates."""

    def __init__(self, predicate: Callable[[T], bool], name: str = None):
        """Initialize with filter predicate.

        Args:
            predicate: Function that returns True for items to keep
            name: Optional custom name
        """
        super().__init__(name)
        self.predicate = predicate

    async def transform(self, input: Iterable[T]) -> list[T]:
        """Filter input collection.

        Args:
            input: Collection to filter

        Returns:
            List of items that match the predicate
        """
        if not input:
            return []

        try:
            return [item for item in input if self.predicate(item)]
        except Exception as e:
            raise ValueError(f"Error filtering collection: {e}")


class RemoveNoneTransformer(TransformerBrick[Iterable[T], list[T], None]):
    """Remove None values from collections."""

    async def transform(self, input: Iterable[T]) -> list[T]:
        """Remove None values from input.

        Args:
            input: Collection potentially containing None values

        Returns:
            List with None values removed
        """
        if not input:
            return []

        return [item for item in input if item is not None]


class RemoveDuplicatesTransformer(TransformerBrick[Iterable[T], list[T], None]):
    """Remove duplicate values from collections."""

    def __init__(self, key: Callable[[T], any] = None, name: str = None):
        """Initialize with optional key function.

        Args:
            key: Function to extract comparison key from items
            name: Optional custom name
        """
        super().__init__(name)
        self.key = key

    async def transform(self, input: Iterable[T]) -> list[T]:
        """Remove duplicates from input.

        Args:
            input: Collection potentially containing duplicates

        Returns:
            List with duplicates removed, preserving order
        """
        if not input:
            return []

        seen = set()
        result = []

        for item in input:
            # Get key for comparison
            key_value = self.key(item) if self.key else item

            # Handle unhashable types
            try:
                if key_value not in seen:
                    seen.add(key_value)
                    result.append(item)
            except TypeError:
                # Fallback for unhashable types
                if key_value not in [self.key(i) if self.key else i for i in result]:
                    result.append(item)

        return result


class TakeTransformer(TransformerBrick[Iterable[T], list[T], None]):
    """Take first N items from collections."""

    def __init__(self, count: int, name: str = None):
        """Initialize with count.

        Args:
            count: Number of items to take
            name: Optional custom name
        """
        super().__init__(name)
        self.count = max(0, count)  # Ensure non-negative

    async def transform(self, input: Iterable[T]) -> list[T]:
        """Take first N items from input.

        Args:
            input: Collection to take from

        Returns:
            List of first N items
        """
        if not input or self.count == 0:
            return []

        result = []
        for i, item in enumerate(input):
            if i >= self.count:
                break
            result.append(item)

        return result


class SkipTransformer(TransformerBrick[Iterable[T], list[T], None]):
    """Skip first N items from collections."""

    def __init__(self, count: int, name: str = None):
        """Initialize with count.

        Args:
            count: Number of items to skip
            name: Optional custom name
        """
        super().__init__(name)
        self.count = max(0, count)  # Ensure non-negative

    async def transform(self, input: Iterable[T]) -> list[T]:
        """Skip first N items from input.

        Args:
            input: Collection to skip from

        Returns:
            List with first N items skipped
        """
        if not input:
            return []

        result = []
        for i, item in enumerate(input):
            if i >= self.count:
                result.append(item)

        return result
