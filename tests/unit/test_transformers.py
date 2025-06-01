"""Unit tests for transformer nanobricks."""

import json

import pytest

from nanobricks.transformers import (
    AverageTransformer,
    CamelCaseTransformer,
    CountTransformer,
    # Filter
    FilterTransformer,
    FlatMapTransformer,
    FrequencyTransformer,
    GroupByTransformer,
    JoinTransformer,
    # JSON
    JSONParser,
    JSONPrettyPrinter,
    JSONSerializer,
    KebabCaseTransformer,
    # Map
    MapTransformer,
    MaxTransformer,
    MinTransformer,
    PascalCaseTransformer,
    ReduceTransformer,
    RemoveDuplicatesTransformer,
    RemoveNoneTransformer,
    SelectTransformer,
    SkipTransformer,
    # Case
    SnakeCaseTransformer,
    # Aggregate
    SumTransformer,
    TakeTransformer,
    TitleCaseTransformer,
    UpperCaseTransformer,
    ZipTransformer,
)


class TestJSONTransformers:
    """Test JSON transformation nanobricks."""

    @pytest.mark.asyncio
    async def test_json_parser(self):
        """Test JSON parsing."""
        parser = JSONParser()

        # Valid JSON string
        result = await parser.invoke('{"name": "test", "value": 42}')
        assert result == {"name": "test", "value": 42}

        # Valid JSON bytes
        result = await parser.invoke(b'{"key": "value"}')
        assert result == {"key": "value"}

        # Empty input
        result = await parser.invoke("")
        assert result == {}

        # Invalid JSON
        with pytest.raises(ValueError, match="Invalid JSON"):
            await parser.invoke("not json")

    @pytest.mark.asyncio
    async def test_json_serializer(self):
        """Test JSON serialization."""
        serializer = JSONSerializer()

        # Basic object
        result = await serializer.invoke({"name": "test", "value": 42})
        assert json.loads(result) == {"name": "test", "value": 42}

        # With options
        pretty = JSONSerializer(indent=2, sort_keys=True)
        result = await pretty.invoke({"b": 2, "a": 1})
        assert '"a": 1' in result
        assert '"b": 2' in result
        assert "\n" in result  # Has newlines from indentation

        # Non-serializable
        with pytest.raises(ValueError, match="Cannot serialize"):
            await serializer.invoke(object())

    @pytest.mark.asyncio
    async def test_json_pretty_printer(self):
        """Test JSON pretty printing."""
        printer = JSONPrettyPrinter()

        result = await printer.invoke({"nested": {"key": "value"}, "array": [1, 2, 3]})
        assert "\n" in result  # Has newlines
        assert "  " in result  # Has indentation


class TestCaseTransformers:
    """Test case transformation nanobricks."""

    @pytest.mark.asyncio
    async def test_snake_case(self):
        """Test snake_case conversion."""
        transformer = SnakeCaseTransformer()

        assert await transformer.invoke("camelCase") == "camel_case"
        assert await transformer.invoke("PascalCase") == "pascal_case"
        assert await transformer.invoke("kebab-case") == "kebab_case"
        assert await transformer.invoke("space case") == "space_case"
        assert await transformer.invoke("UPPER_CASE") == "upper_case"
        assert await transformer.invoke("") == ""
        assert await transformer.invoke("already_snake") == "already_snake"
        assert await transformer.invoke("mixedUPPERCase") == "mixed_upper_case"

    @pytest.mark.asyncio
    async def test_camel_case(self):
        """Test camelCase conversion."""
        transformer = CamelCaseTransformer()

        assert await transformer.invoke("snake_case") == "snakeCase"
        assert await transformer.invoke("PascalCase") == "pascalCase"
        assert await transformer.invoke("kebab-case") == "kebabCase"
        assert await transformer.invoke("space case") == "spaceCase"
        assert await transformer.invoke("") == ""

    @pytest.mark.asyncio
    async def test_pascal_case(self):
        """Test PascalCase conversion."""
        transformer = PascalCaseTransformer()

        assert await transformer.invoke("snake_case") == "SnakeCase"
        assert await transformer.invoke("camelCase") == "CamelCase"
        assert await transformer.invoke("kebab-case") == "KebabCase"
        assert await transformer.invoke("") == ""

    @pytest.mark.asyncio
    async def test_kebab_case(self):
        """Test kebab-case conversion."""
        transformer = KebabCaseTransformer()

        assert await transformer.invoke("snake_case") == "snake-case"
        assert await transformer.invoke("camelCase") == "camel-case"
        assert await transformer.invoke("PascalCase") == "pascal-case"
        assert await transformer.invoke("") == ""

    @pytest.mark.asyncio
    async def test_upper_case(self):
        """Test UPPER_CASE conversion."""
        transformer = UpperCaseTransformer()

        assert await transformer.invoke("snake_case") == "SNAKE_CASE"
        assert await transformer.invoke("camelCase") == "CAMEL_CASE"
        assert await transformer.invoke("") == ""

    @pytest.mark.asyncio
    async def test_title_case(self):
        """Test Title Case conversion."""
        transformer = TitleCaseTransformer()

        assert await transformer.invoke("hello world") == "Hello World"
        assert await transformer.invoke("snake_case") == "Snake_case"
        assert await transformer.invoke("") == ""


class TestFilterTransformers:
    """Test filter transformation nanobricks."""

    @pytest.mark.asyncio
    async def test_filter(self):
        """Test filtering with predicate."""
        is_even = FilterTransformer(lambda x: x % 2 == 0)

        assert await is_even.invoke([1, 2, 3, 4, 5]) == [2, 4]
        assert await is_even.invoke([]) == []
        assert await is_even.invoke([1, 3, 5]) == []

        # String filter
        is_long = FilterTransformer(lambda s: len(s) > 3)
        assert await is_long.invoke(["a", "test", "hi", "hello"]) == ["test", "hello"]

    @pytest.mark.asyncio
    async def test_remove_none(self):
        """Test removing None values."""
        transformer = RemoveNoneTransformer()

        assert await transformer.invoke([1, None, 2, None, 3]) == [1, 2, 3]
        assert await transformer.invoke([None, None]) == []
        assert await transformer.invoke([1, 2, 3]) == [1, 2, 3]
        assert await transformer.invoke([]) == []

    @pytest.mark.asyncio
    async def test_remove_duplicates(self):
        """Test removing duplicates."""
        transformer = RemoveDuplicatesTransformer()

        assert await transformer.invoke([1, 2, 2, 3, 1, 4]) == [1, 2, 3, 4]
        assert await transformer.invoke(["a", "b", "a", "c"]) == ["a", "b", "c"]
        assert await transformer.invoke([]) == []

        # With key function
        by_first_letter = RemoveDuplicatesTransformer(key=lambda s: s[0])
        assert await by_first_letter.invoke(["apple", "apricot", "banana"]) == [
            "apple",
            "banana",
        ]

    @pytest.mark.asyncio
    async def test_take(self):
        """Test taking first N items."""
        take3 = TakeTransformer(3)

        assert await take3.invoke([1, 2, 3, 4, 5]) == [1, 2, 3]
        assert await take3.invoke([1, 2]) == [1, 2]
        assert await take3.invoke([]) == []

        # Edge cases
        take0 = TakeTransformer(0)
        assert await take0.invoke([1, 2, 3]) == []

        take_negative = TakeTransformer(-1)  # Should be treated as 0
        assert await take_negative.invoke([1, 2, 3]) == []

    @pytest.mark.asyncio
    async def test_skip(self):
        """Test skipping first N items."""
        skip2 = SkipTransformer(2)

        assert await skip2.invoke([1, 2, 3, 4, 5]) == [3, 4, 5]
        assert await skip2.invoke([1, 2]) == []
        assert await skip2.invoke([]) == []


class TestMapTransformers:
    """Test map transformation nanobricks."""

    @pytest.mark.asyncio
    async def test_map(self):
        """Test mapping function over collection."""
        double = MapTransformer(lambda x: x * 2)

        assert await double.invoke([1, 2, 3]) == [2, 4, 6]
        assert await double.invoke([]) == []

        # String transformation
        upper = MapTransformer(str.upper)
        assert await upper.invoke(["hello", "world"]) == ["HELLO", "WORLD"]

    @pytest.mark.asyncio
    async def test_select(self):
        """Test selecting field from dictionaries."""
        selector = SelectTransformer("name")

        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        assert await selector.invoke(data) == ["Alice", "Bob"]

        # With default
        selector_default = SelectTransformer("missing", default="N/A")
        assert await selector_default.invoke(data) == ["N/A", "N/A"]

        # Empty input
        assert await selector.invoke([]) == []

    @pytest.mark.asyncio
    async def test_flat_map(self):
        """Test flat mapping."""
        words = FlatMapTransformer(lambda s: s.split())

        assert await words.invoke(["hello world", "foo bar"]) == [
            "hello",
            "world",
            "foo",
            "bar",
        ]
        assert await words.invoke([]) == []

        # Nested lists
        flatten = FlatMapTransformer(lambda x: x)
        assert await flatten.invoke([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_group_by(self):
        """Test grouping by key."""
        by_len = GroupByTransformer(lambda s: str(len(s)))

        result = await by_len.invoke(["a", "bb", "ccc", "dd", "e"])
        assert result == {"1": ["a", "e"], "2": ["bb", "dd"], "3": ["ccc"]}

        assert await by_len.invoke([]) == {}

    @pytest.mark.asyncio
    async def test_zip(self):
        """Test zipping iterables."""
        # Single iterable
        zipper = ZipTransformer()
        assert await zipper.invoke([1, 2, 3]) == [(1,), (2,), (3,)]

        # With additional iterables
        zipper2 = ZipTransformer(["a", "b", "c"])
        assert await zipper2.invoke([1, 2, 3]) == [(1, "a"), (2, "b"), (3, "c")]

        # List of iterables
        assert await zipper.invoke([[1, 2], ["a", "b"]]) == [(1, "a"), (2, "b")]


class TestAggregateTransformers:
    """Test aggregate transformation nanobricks."""

    @pytest.mark.asyncio
    async def test_sum(self):
        """Test sum aggregation."""
        summer = SumTransformer()

        assert await summer.invoke([1, 2, 3, 4, 5]) == 15
        assert await summer.invoke([1.5, 2.5]) == 4.0
        assert await summer.invoke([]) == 0

        # Non-numeric
        with pytest.raises(ValueError, match="non-numeric"):
            await summer.invoke(["a", "b"])

    @pytest.mark.asyncio
    async def test_average(self):
        """Test average calculation."""
        avg = AverageTransformer()

        assert await avg.invoke([1, 2, 3, 4, 5]) == 3.0
        assert await avg.invoke([10, 20]) == 15.0

        # Empty collection
        with pytest.raises(ValueError, match="empty collection"):
            await avg.invoke([])

    @pytest.mark.asyncio
    async def test_min_max(self):
        """Test min/max aggregation."""
        min_t = MinTransformer()
        max_t = MaxTransformer()

        assert await min_t.invoke([3, 1, 4, 1, 5]) == 1
        assert await max_t.invoke([3, 1, 4, 1, 5]) == 5

        # With key function
        by_len = MinTransformer(key=len)
        assert await by_len.invoke(["hello", "a", "world"]) == "a"

        # Empty collection
        with pytest.raises(ValueError, match="empty collection"):
            await min_t.invoke([])

    @pytest.mark.asyncio
    async def test_count(self):
        """Test counting elements."""
        counter = CountTransformer()

        assert await counter.invoke([1, 2, 3, 4, 5]) == 5
        assert await counter.invoke([]) == 0

        # With predicate
        even_counter = CountTransformer(lambda x: x % 2 == 0)
        assert await even_counter.invoke([1, 2, 3, 4, 5]) == 2

    @pytest.mark.asyncio
    async def test_reduce(self):
        """Test custom reduction."""
        # Product
        product = ReduceTransformer(lambda acc, x: acc * x, initial=1)
        assert await product.invoke([1, 2, 3, 4]) == 24

        # String concatenation
        concat = ReduceTransformer(lambda acc, x: acc + x, initial="")
        assert await concat.invoke(["a", "b", "c"]) == "abc"

        # Empty collection returns initial
        assert await product.invoke([]) == 1

    @pytest.mark.asyncio
    async def test_join(self):
        """Test string joining."""
        joiner = JoinTransformer(", ")

        assert await joiner.invoke(["a", "b", "c"]) == "a, b, c"
        assert await joiner.invoke([]) == ""

        # No separator
        concat = JoinTransformer()
        assert await concat.invoke(["hello", "world"]) == "helloworld"

    @pytest.mark.asyncio
    async def test_frequency(self):
        """Test frequency counting."""
        freq = FrequencyTransformer()

        result = await freq.invoke(["a", "b", "a", "c", "b", "a"])
        assert result == {"a": 3, "b": 2, "c": 1}

        assert await freq.invoke([]) == {}

        # With numbers
        result = await freq.invoke([1, 2, 1, 3, 2, 1])
        assert result == {1: 3, 2: 2, 3: 1}
