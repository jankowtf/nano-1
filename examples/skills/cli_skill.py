# Import skills to trigger registration
from nanobricks import Nanobrick, skill


@skill("cli", command="wordcount", input_type="text", output_format="pretty")
class WordCounterBrick(Nanobrick[str, dict]):
    """Counts words, characters, and lines in text."""

    async def invoke(self, input: str, *, deps=None) -> dict:
        lines = input.splitlines()
        words = input.split()
        chars = len(input)

        return {
            "text_preview": input[:50] + "..." if len(input) > 50 else input,
            "statistics": {
                "lines": len(lines),
                "words": len(words),
                "characters": chars,
                "characters_no_spaces": len(input.replace(" ", "")),
                "average_word_length": round(sum(len(w) for w in words) / len(words), 2)
                if words
                else 0,
            },
            "most_common_words": self._get_most_common_words(words, 5),
        }

    def _get_most_common_words(self, words: list[str], n: int) -> list[tuple[str, int]]:
        """Get the n most common words."""
        from collections import Counter

        word_counts = Counter(w.lower() for w in words if len(w) > 2)
        return word_counts.most_common(n)


if __name__ == "__main__":
    counter = WordCounterBrick()

    # Show example usage
    import asyncio

    sample_text = """The quick brown fox jumps over the lazy dog.
This is a sample text for word counting.
It contains multiple lines and various words."""

    result = asyncio.run(counter.invoke(sample_text))
    print(f"Direct invocation result: {result}")

    print("\n" + "=" * 60)
    print("🚀 CLI Usage Examples")
    print("=" * 60)

    print("\n📝 Interactive mode:")
    print("  python -m examples.skills.cli")
    print("  (Then type or paste your text)")

    print("\n📄 From file:")
    print("  python -m examples.skills.cli --file README.md")

    print("\n🔤 Direct text:")
    print('  python -m examples.skills.cli --input "Your text here"')

    print("\n💾 JSON output:")
    print("  python -m examples.skills.cli --output-format json")

    print("\n🎯 Pipe from other commands:")
    print("  cat README.md | python -m examples.skills.cli")

    print("\n" + "=" * 60)

    # Create and run the CLI
    print("\nStarting CLI... (use --help for options)\n")

    # The CLI skill automatically creates a typer app
    # When run as a module, it will handle command line arguments
    import sys

    if len(sys.argv) == 1:
        # If no arguments, show help
        sys.argv.append("--help")

    counter.run_cli()
