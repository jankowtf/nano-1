"""Tests for additional transformers."""

from datetime import date

import pytest

from nanobricks.transformers import (
    BulkTypeConverter,
    CSVParser,
    CSVSerializer,
    DynamicTypeConverter,
    SentenceNormalizer,
    SmartTypeConverter,
    TextNormalizer,
    TokenNormalizer,
)


class TestCSVTransformers:
    """Tests for CSV transformers."""

    @pytest.mark.asyncio
    async def test_csv_parser(self):
        """Test CSV parsing."""
        parser = CSVParser()

        csv_text = """name,age,city
Alice,30,New York
Bob,25,London
Charlie,35,Tokyo"""

        result = await parser.transform(csv_text)

        assert len(result) == 3
        assert result[0] == {"name": "Alice", "age": "30", "city": "New York"}
        assert result[1]["name"] == "Bob"
        assert result[2]["city"] == "Tokyo"

    @pytest.mark.asyncio
    async def test_csv_parser_with_options(self):
        """Test CSV parser with custom options."""
        parser = CSVParser(delimiter=";", skip_empty=True, strip_values=True)

        csv_text = """name;age;city
Alice ; 30 ; New York
;;
Bob;25;London"""

        result = await parser.transform(csv_text)

        assert len(result) == 2  # Empty row skipped
        assert result[0]["name"] == "Alice"  # Stripped
        assert result[0]["city"] == "New York"  # Stripped

    @pytest.mark.asyncio
    async def test_csv_serializer(self):
        """Test CSV serialization."""
        serializer = CSVSerializer()

        data = [
            {"name": "Alice", "age": 30, "city": "New York"},
            {"name": "Bob", "age": 25, "city": "London"},
        ]

        result = await serializer.transform(data)

        lines = result.strip().split("\n")
        assert len(lines) == 3  # Header + 2 rows
        assert "name,age,city" in lines[0]
        assert "Alice,30,New York" in lines[1]

    @pytest.mark.asyncio
    async def test_csv_serializer_custom_columns(self):
        """Test CSV serializer with custom columns."""
        serializer = CSVSerializer(
            columns=["name", "city"],  # Skip age
            include_header=False,
        )

        data = [
            {"name": "Alice", "age": 30, "city": "New York", "extra": "ignored"},
            {"name": "Bob", "age": 25, "city": "London"},
        ]

        result = await serializer.transform(data)

        lines = result.strip().split("\n")
        assert len(lines) == 2  # No header
        assert "30" not in result  # Age excluded
        assert "Alice,New York" in lines[0]


class TestTextNormalizers:
    """Tests for text normalization transformers."""

    @pytest.mark.asyncio
    async def test_text_normalizer_basic(self):
        """Test basic text normalization."""
        normalizer = TextNormalizer(lowercase=True, remove_extra_spaces=True)

        text = "  Hello   WORLD!   "
        result = await normalizer.transform(text)

        assert result == "hello world!"

    @pytest.mark.asyncio
    async def test_text_normalizer_advanced(self):
        """Test advanced text normalization."""
        normalizer = TextNormalizer(
            lowercase=True,
            remove_punctuation=True,
            remove_numbers=True,
            remove_urls=True,
            remove_emails=True,
            expand_contractions=True,
        )

        text = "Don't email me@test.com! Visit https://example.com or call 123-456."
        result = await normalizer.transform(text)

        assert "do not" in result  # Contraction expanded
        assert "@" not in result  # Email removed
        assert "https" not in result  # URL removed
        assert "123" not in result  # Numbers removed
        assert "!" not in result  # Punctuation removed

    @pytest.mark.asyncio
    async def test_text_normalizer_custom_replacements(self):
        """Test custom replacements."""
        normalizer = TextNormalizer(
            lowercase=False,  # Don't lowercase to test replacements
            custom_replacements={
                "CEO": "Chief Executive Officer",
                "AI": "Artificial Intelligence",
            },
        )

        text = "The CEO discussed AI strategy"
        result = await normalizer.transform(text)

        assert "Chief Executive Officer" in result
        assert "Artificial Intelligence" in result

    @pytest.mark.asyncio
    async def test_token_normalizer(self):
        """Test token normalization."""
        normalizer = TokenNormalizer(
            min_length=3, max_length=10, lowercase=True, remove_numbers=True
        )

        tokens = ["Hello", "WORLD", "123", "a", "beautiful", "incredibly-long-word"]
        result = await normalizer.transform(tokens)

        assert "hello" in result
        assert "world" in result
        assert "123" not in result  # Number removed
        assert "a" not in result  # Too short
        assert "incredibly-long-word" not in result  # Too long
        assert "beautiful" in result

    @pytest.mark.asyncio
    async def test_sentence_normalizer(self):
        """Test sentence normalization."""
        normalizer = SentenceNormalizer(min_length=10, strip_sentences=True)

        text = "This is a sentence. Short. Another good sentence! And one more?"
        result = await normalizer.transform(text)

        assert len(result) == 3  # "Short." excluded
        assert "This is a sentence" in result[0]
        assert "Another good sentence" in result[1]
        assert "And one more" in result[2]


class TestTypeConverters:
    """Tests for type conversion transformers."""

    @pytest.mark.asyncio
    async def test_smart_type_converter_to_int(self):
        """Test converting to int."""
        converter = SmartTypeConverter(target_type=int)

        assert await converter.transform("42") == 42
        assert await converter.transform("1,234") == 1234
        assert await converter.transform(42.7) == 42
        assert await converter.transform(True) == 1

    @pytest.mark.asyncio
    async def test_smart_type_converter_to_bool(self):
        """Test converting to bool."""
        converter = SmartTypeConverter(target_type=bool)

        assert await converter.transform("true") is True
        assert await converter.transform("yes") is True
        assert await converter.transform("1") is True
        assert await converter.transform("false") is False
        assert await converter.transform("no") is False
        assert await converter.transform(1) is True
        assert await converter.transform(0) is False

    @pytest.mark.asyncio
    async def test_smart_type_converter_to_date(self):
        """Test converting to date."""
        converter = SmartTypeConverter(target_type=date, date_format="%Y-%m-%d")

        result = await converter.transform("2024-01-15")
        assert isinstance(result, date)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    @pytest.mark.asyncio
    async def test_smart_type_converter_to_list(self):
        """Test converting to list."""
        converter = SmartTypeConverter(target_type=list)

        # From JSON string
        result = await converter.transform('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

        # From comma-separated
        result = await converter.transform("a, b, c")
        assert result == ["a", "b", "c"]

        # From tuple
        result = await converter.transform(("x", "y"))
        assert result == ["x", "y"]

    @pytest.mark.asyncio
    async def test_smart_type_converter_strict_mode(self):
        """Test strict mode error handling."""
        converter = SmartTypeConverter(target_type=int, strict=True)

        with pytest.raises(ValueError):
            await converter.transform("not a number")

        # Non-strict with fallback
        converter_fallback = SmartTypeConverter(
            target_type=int, strict=False, fallback=-1
        )

        result = await converter_fallback.transform("not a number")
        assert result == -1

    @pytest.mark.asyncio
    async def test_bulk_type_converter(self):
        """Test bulk type conversion."""
        converter = BulkTypeConverter(target_type=int, skip_errors=True, error_value=0)

        values = ["42", "100", "invalid", "75", "not a number"]
        result = await converter.transform(values)

        assert result == [42, 100, 0, 75, 0]

    @pytest.mark.asyncio
    async def test_bulk_type_converter_with_report(self):
        """Test bulk converter with error reporting."""
        converter = BulkTypeConverter(target_type=float, report_errors=True)

        values = ["1.5", "invalid", "2.7"]
        result = await converter.transform(values)

        assert isinstance(result, dict)
        assert result["results"] == [1.5, None, 2.7]
        assert result["error_count"] == 1
        assert result["success_count"] == 2

    @pytest.mark.asyncio
    async def test_dynamic_type_converter(self):
        """Test dynamic type conversion."""
        converter = DynamicTypeConverter(
            type_map={"age": int, "active": bool}, infer_types=True
        )

        data = {"name": "Alice", "age": "30", "salary": "50000.50", "active": "yes"}

        result = await converter.transform(data)

        assert result["name"] == "Alice"  # String stays string
        assert result["age"] == 30  # Converted to int
        assert result["salary"] == 50000.50  # Inferred as float
        assert result["active"] is True  # Converted to bool
