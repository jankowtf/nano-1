"""Case transformation nanobricks for string conversions."""

import re

from nanobricks.transformers.base import TransformerBrick


class SnakeCaseTransformer(TransformerBrick[str, str, None]):
    """Convert strings to snake_case."""

    async def transform(self, input: str) -> str:
        """Convert input to snake_case.

        Args:
            input: String to convert

        Returns:
            snake_case string
        """
        if not input:
            return ""

        # Handle camelCase and PascalCase
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", input)
        s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)

        # Replace spaces, hyphens with underscores
        s3 = re.sub(r"[\s\-]+", "_", s2)

        # Remove non-alphanumeric except underscores
        s4 = re.sub(r"[^\w_]", "", s3)

        # Remove duplicate underscores and convert to lower
        return re.sub(r"_+", "_", s4).lower().strip("_")


class CamelCaseTransformer(TransformerBrick[str, str, None]):
    """Convert strings to camelCase."""

    async def transform(self, input: str) -> str:
        """Convert input to camelCase.

        Args:
            input: String to convert

        Returns:
            camelCase string
        """
        if not input:
            return ""

        # Handle PascalCase by detecting capital at start
        if input[0].isupper() and not input.isupper():
            # Check if it's PascalCase (no underscores/spaces)
            if "_" not in input and "-" not in input and " " not in input:
                return input[0].lower() + input[1:]

        # Split on non-alphanumeric or case boundaries
        words = []
        current_word = []

        for i, char in enumerate(input):
            if char.isalnum():
                # Check for case boundary
                if i > 0 and current_word and char.isupper() and input[i - 1].islower():
                    words.append("".join(current_word))
                    current_word = [char]
                else:
                    current_word.append(char)
            else:
                if current_word:
                    words.append("".join(current_word))
                    current_word = []

        if current_word:
            words.append("".join(current_word))

        if not words:
            return ""

        # First word lowercase, rest title case
        return words[0].lower() + "".join(w.capitalize() for w in words[1:])


class PascalCaseTransformer(TransformerBrick[str, str, None]):
    """Convert strings to PascalCase."""

    async def transform(self, input: str) -> str:
        """Convert input to PascalCase.

        Args:
            input: String to convert

        Returns:
            PascalCase string
        """
        if not input:
            return ""

        # Handle camelCase by detecting lowercase at start
        if input[0].islower() and any(c.isupper() for c in input[1:]):
            # Check if it's camelCase (no underscores/spaces)
            if "_" not in input and "-" not in input and " " not in input:
                return input[0].upper() + input[1:]

        # Split on non-alphanumeric or case boundaries
        words = []
        current_word = []

        for i, char in enumerate(input):
            if char.isalnum():
                # Check for case boundary
                if i > 0 and current_word and char.isupper() and input[i - 1].islower():
                    words.append("".join(current_word))
                    current_word = [char]
                else:
                    current_word.append(char)
            else:
                if current_word:
                    words.append("".join(current_word))
                    current_word = []

        if current_word:
            words.append("".join(current_word))

        if not words:
            return ""

        # All words title case
        return "".join(w.capitalize() for w in words)


class KebabCaseTransformer(TransformerBrick[str, str, None]):
    """Convert strings to kebab-case."""

    async def transform(self, input: str) -> str:
        """Convert input to kebab-case.

        Args:
            input: String to convert

        Returns:
            kebab-case string
        """
        if not input:
            return ""

        # Convert to snake_case first
        snake = await SnakeCaseTransformer().transform(input)

        # Replace underscores with hyphens
        return snake.replace("_", "-")


class UpperCaseTransformer(TransformerBrick[str, str, None]):
    """Convert strings to UPPER_CASE."""

    async def transform(self, input: str) -> str:
        """Convert input to UPPER_CASE.

        Args:
            input: String to convert

        Returns:
            UPPER_CASE string
        """
        if not input:
            return ""

        # Convert to snake_case first
        snake = await SnakeCaseTransformer().transform(input)

        # Convert to upper
        return snake.upper()


class TitleCaseTransformer(TransformerBrick[str, str, None]):
    """Convert strings to Title Case."""

    async def transform(self, input: str) -> str:
        """Convert input to Title Case.

        Args:
            input: String to convert

        Returns:
            Title Case string
        """
        if not input:
            return ""

        # Split on non-alphanumeric, keeping spaces
        words = re.split(r"(\s+)", input)

        # Capitalize words, preserve whitespace
        result: list[str] = []
        for word in words:
            if word.strip():  # Not just whitespace
                # Only capitalize if it's a word
                if re.match(r"[A-Za-z]", word):
                    result.append(word.capitalize())
                else:
                    result.append(word)
            else:
                result.append(word)  # Preserve whitespace

        return "".join(result)
