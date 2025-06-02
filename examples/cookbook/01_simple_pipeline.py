#!/usr/bin/env python3
"""
Basic Pipeline Example - Your First Nanobrick Pipeline

This example demonstrates the simplest way to compose nanobricks using the pipe operator.
Perfect for when your types align naturally between stages.
"""

import asyncio
from typing import List, Dict
from nanobricks import NanobrickSimple


# Step 1: Define individual bricks with clear input/output types
class TextCleaner(NanobrickSimple[str, str]):
    """Removes extra whitespace and normalizes text."""
    
    name = "text_cleaner"
    version = "1.0.0"
    
    async def invoke(self, input: str, *, deps=None) -> str:
        # Strip leading/trailing whitespace and normalize internal spaces
        return " ".join(input.split())


class WordTokenizer(NanobrickSimple[str, List[str]]):
    """Splits text into individual words."""
    
    name = "word_tokenizer"
    version = "1.0.0"
    
    async def invoke(self, input: str, *, deps=None) -> List[str]:
        # Simple word splitting (in production, consider using nltk or spacy)
        return input.lower().split()


class WordCounter(NanobrickSimple[List[str], Dict[str, int]]):
    """Counts word frequencies."""
    
    name = "word_counter"
    version = "1.0.0"
    
    async def invoke(self, input: List[str], *, deps=None) -> Dict[str, int]:
        word_freq = {}
        for word in input:
            word_freq[word] = word_freq.get(word, 0) + 1
        return word_freq


# Step 2: Compose bricks using the pipe operator
def create_text_analysis_pipeline():
    """
    Creates a pipeline that:
    1. Cleans text
    2. Tokenizes into words
    3. Counts word frequencies
    
    Note how the output type of each stage matches the input of the next!
    """
    return TextCleaner() | WordTokenizer() | WordCounter()


# Step 3: Use the pipeline
async def main():
    # Create the pipeline
    pipeline = create_text_analysis_pipeline()
    
    # Sample text with irregular spacing
    text = "  The quick   brown fox  jumps over the   lazy dog.  The fox was quick!  "
    
    print("Input text:")
    print(f"'{text}'")
    print()
    
    # Run the pipeline - it handles all the stages automatically
    result = await pipeline.invoke(text)
    
    print("Word frequencies:")
    for word, count in sorted(result.items(), key=lambda x: x[1], reverse=True):
        print(f"  {word}: {count}")
    
    # You can also access the pipeline name (combination of all stages)
    print(f"\nPipeline name: {pipeline.name}")


# Alternative: Use individual bricks if you need intermediate results
async def main_with_intermediates():
    """Shows how to use bricks individually when you need intermediate results."""
    cleaner = TextCleaner()
    tokenizer = WordTokenizer()
    counter = WordCounter()
    
    text = "  The quick   brown fox  jumps over the   lazy dog.  "
    
    # Process step by step
    cleaned = await cleaner.invoke(text)
    print(f"Cleaned: '{cleaned}'")
    
    tokens = await tokenizer.invoke(cleaned)
    print(f"Tokens: {tokens}")
    
    frequencies = await counter.invoke(tokens)
    print(f"Frequencies: {frequencies}")


if __name__ == "__main__":
    print("=== Simple Pipeline Example ===")
    asyncio.run(main())
    
    print("\n=== With Intermediate Results ===")
    asyncio.run(main_with_intermediates())