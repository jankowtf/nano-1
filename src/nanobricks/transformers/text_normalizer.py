"""Text normalization transformers."""

import re
import unicodedata
from collections.abc import Callable

from nanobricks.transformers.base import TransformerBase


class TextNormalizer(TransformerBase[str, str]):
    """Normalizes text with various options."""

    def __init__(
        self,
        *,
        lowercase: bool = True,
        remove_punctuation: bool = False,
        remove_numbers: bool = False,
        remove_extra_spaces: bool = True,
        normalize_unicode: bool = True,
        remove_accents: bool = False,
        expand_contractions: bool = False,
        remove_urls: bool = False,
        remove_emails: bool = False,
        remove_html: bool = False,
        custom_replacements: dict[str, str] | None = None,
        stop_words: set[str] | None = None,
        name: str = "text_normalizer",
        version: str = "1.0.0",
    ):
        """Initialize text normalizer.

        Args:
            lowercase: Convert to lowercase
            remove_punctuation: Remove punctuation marks
            remove_numbers: Remove numeric characters
            remove_extra_spaces: Normalize whitespace
            normalize_unicode: Normalize unicode characters
            remove_accents: Remove accent marks
            expand_contractions: Expand contractions (e.g., don't -> do not)
            remove_urls: Remove URLs
            remove_emails: Remove email addresses
            remove_html: Remove HTML tags
            custom_replacements: Custom string replacements
            stop_words: Words to remove
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.lowercase = lowercase
        self.remove_punctuation = remove_punctuation
        self.remove_numbers = remove_numbers
        self.remove_extra_spaces = remove_extra_spaces
        self.normalize_unicode = normalize_unicode
        self.remove_accents = remove_accents
        self.expand_contractions = expand_contractions
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_html = remove_html
        self.custom_replacements = custom_replacements or {}
        self.stop_words = stop_words or set()

        # Common contractions
        self.contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "n't": " not",
            "'re": " are",
            "'ve": " have",
            "'ll": " will",
            "'d": " would",
            "'m": " am",
            "it's": "it is",
            "that's": "that is",
            "what's": "what is",
            "there's": "there is",
            "here's": "here is",
            "let's": "let us",
        }

    async def transform(self, input: str) -> str:
        """Normalize text.

        Args:
            input: Text to normalize

        Returns:
            Normalized text
        """
        text = input

        # Remove HTML tags first if requested
        if self.remove_html:
            text = re.sub(r"<[^>]+>", " ", text)

        # Remove URLs
        if self.remove_urls:
            text = re.sub(r"https?://\S+|www\.\S+", " ", text)

        # Remove emails
        if self.remove_emails:
            text = re.sub(r"\S+@\S+", " ", text)

        # Normalize unicode
        if self.normalize_unicode:
            text = unicodedata.normalize("NFKD", text)

        # Remove accents
        if self.remove_accents:
            text = "".join(c for c in text if not unicodedata.combining(c))

        # Expand contractions
        if self.expand_contractions:
            for contraction, expansion in self.contractions.items():
                text = re.sub(
                    r"\b" + contraction + r"\b", expansion, text, flags=re.IGNORECASE
                )

        # Custom replacements
        for old, new in self.custom_replacements.items():
            text = text.replace(old, new)

        # Remove numbers
        if self.remove_numbers:
            text = re.sub(r"\d+", " ", text)

        # Remove punctuation
        if self.remove_punctuation:
            text = re.sub(r"[^\w\s]", " ", text)

        # Lowercase
        if self.lowercase:
            text = text.lower()

        # Remove stop words
        if self.stop_words:
            words = text.split()
            words = [w for w in words if w not in self.stop_words]
            text = " ".join(words)

        # Remove extra spaces
        if self.remove_extra_spaces:
            text = " ".join(text.split())

        return text.strip()


class TokenNormalizer(TransformerBase[list[str], list[str]]):
    """Normalizes a list of tokens."""

    def __init__(
        self,
        *,
        min_length: int = 1,
        max_length: int | None = None,
        lowercase: bool = True,
        remove_numbers: bool = False,
        keep_alphanumeric: bool = True,
        custom_filter: Callable | None = None,
        name: str = "token_normalizer",
        version: str = "1.0.0",
    ):
        """Initialize token normalizer.

        Args:
            min_length: Minimum token length
            max_length: Maximum token length
            lowercase: Convert to lowercase
            remove_numbers: Remove numeric tokens
            keep_alphanumeric: Keep only alphanumeric tokens
            custom_filter: Custom filter function
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.min_length = min_length
        self.max_length = max_length
        self.lowercase = lowercase
        self.remove_numbers = remove_numbers
        self.keep_alphanumeric = keep_alphanumeric
        self.custom_filter = custom_filter

    async def transform(self, input: list[str]) -> list[str]:
        """Normalize tokens.

        Args:
            input: List of tokens

        Returns:
            Normalized token list
        """
        tokens = []

        for token in input:
            # Length filter
            if len(token) < self.min_length:
                continue
            if self.max_length and len(token) > self.max_length:
                continue

            # Number filter
            if self.remove_numbers and token.isdigit():
                continue

            # Alphanumeric filter
            if self.keep_alphanumeric and not token.isalnum():
                continue

            # Custom filter
            if self.custom_filter and not self.custom_filter(token):
                continue

            # Lowercase
            if self.lowercase:
                token = token.lower()

            tokens.append(token)

        return tokens


class SentenceNormalizer(TransformerBase[str, list[str]]):
    """Splits and normalizes text into sentences."""

    def __init__(
        self,
        *,
        min_length: int = 5,
        max_length: int | None = None,
        remove_empty: bool = True,
        strip_sentences: bool = True,
        end_punctuation: str = ".!?",
        abbreviations: set[str] | None = None,
        name: str = "sentence_normalizer",
        version: str = "1.0.0",
    ):
        """Initialize sentence normalizer.

        Args:
            min_length: Minimum sentence length
            max_length: Maximum sentence length
            remove_empty: Remove empty sentences
            strip_sentences: Strip whitespace
            end_punctuation: Sentence ending punctuation
            abbreviations: Known abbreviations (to avoid false splits)
            name: Transformer name
            version: Transformer version
        """
        super().__init__(name=name, version=version)
        self.min_length = min_length
        self.max_length = max_length
        self.remove_empty = remove_empty
        self.strip_sentences = strip_sentences
        self.end_punctuation = end_punctuation
        self.abbreviations = abbreviations or {
            "Mr.",
            "Mrs.",
            "Ms.",
            "Dr.",
            "Prof.",
            "Inc.",
            "Ltd.",
            "Co.",
            "vs.",
            "etc.",
            "i.e.",
            "e.g.",
            "cf.",
            "al.",
        }

    async def transform(self, input: str) -> list[str]:
        """Split text into normalized sentences.

        Args:
            input: Text to split

        Returns:
            List of sentences
        """
        # Basic sentence splitting with abbreviation handling
        text = input

        # Protect abbreviations
        for abbr in self.abbreviations:
            text = text.replace(abbr, abbr.replace(".", "<!DOT!>"))

        # Split on sentence endings
        pattern = f"[{re.escape(self.end_punctuation)}]+\\s+"
        sentences = re.split(pattern, text)

        # Restore dots in abbreviations
        sentences = [s.replace("<!DOT!>", ".") for s in sentences]

        # Process sentences
        result = []
        for sentence in sentences:
            if self.strip_sentences:
                sentence = sentence.strip()

            if self.remove_empty and not sentence:
                continue

            if len(sentence) < self.min_length:
                continue

            if self.max_length and len(sentence) > self.max_length:
                continue

            result.append(sentence)

        return result
