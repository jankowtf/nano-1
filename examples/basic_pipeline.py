"""
Basic pipeline example demonstrating nanobrick composition.

This example shows how to create simple nanobricks and compose them
using the pipe operator (|) to create data processing pipelines.
"""

import asyncio
from typing import List

from nanobricks import Nanobrick


# Define some simple nanobricks
class ValidateEmailBrick(Nanobrick[str, str]):
    """Validates that input looks like an email."""
    
    async def invoke(self, input: str, *, deps=None) -> str:
        if "@" not in input or "." not in input:
            raise ValueError(f"Invalid email format: {input}")
        return input


class NormalizeEmailBrick(Nanobrick[str, str]):
    """Normalizes email to lowercase and strips whitespace."""
    
    async def invoke(self, input: str, *, deps=None) -> str:
        return input.strip().lower()


class ExtractDomainBrick(Nanobrick[str, str]):
    """Extracts domain from email address."""
    
    async def invoke(self, input: str, *, deps=None) -> str:
        return input.split("@")[1]


class WordCountBrick(Nanobrick[str, int]):
    """Counts words in a string."""
    
    async def invoke(self, input: str, *, deps=None) -> int:
        return len(input.split())


class SumBrick(Nanobrick[List[int], int]):
    """Sums a list of integers."""
    
    async def invoke(self, input: List[int], *, deps=None) -> int:
        return sum(input)


async def main():
    """Demonstrate various pipeline compositions."""
    
    print("=== Nanobrick Composition Examples ===\n")
    
    # Example 1: Email processing pipeline
    print("1. Email Processing Pipeline")
    print("-" * 30)
    
    validate = ValidateEmailBrick(name="validate")
    normalize = NormalizeEmailBrick(name="normalize")
    extract = ExtractDomainBrick(name="extract")
    
    # Compose them into a pipeline
    email_pipeline = validate | normalize | extract
    
    # Test with various inputs
    test_emails = [
        "  John.Doe@Example.COM  ",
        "alice@wonderland.io",
        "BOB@CORP.NET"
    ]
    
    for email in test_emails:
        try:
            domain = await email_pipeline.invoke(email)
            print(f"  {email:30} -> {domain}")
        except ValueError as e:
            print(f"  {email:30} -> ERROR: {e}")
    
    # Example 2: Three-way composition
    print("\n2. Three-Way Composition")
    print("-" * 30)
    
    # Create the full pipeline name
    print(f"  Pipeline: {email_pipeline.name}")
    print(f"  String representation: {str(email_pipeline)}")
    
    # Example 3: Async usage continues
    print("\n3. Multiple Async Calls")
    print("-" * 30)
    
    # Process multiple emails concurrently
    emails = ["async1@example.com", "async2@test.org", "async3@demo.net"]
    results = await asyncio.gather(*[email_pipeline.invoke(e) for e in emails])
    for email, result in zip(emails, results):
        print(f"  {email} -> {result}")
    
    # Example 4: Error handling
    print("\n4. Error Handling (Fail-Fast)")
    print("-" * 30)
    
    try:
        # This will fail validation
        await email_pipeline.invoke("not-an-email")
    except ValueError as e:
        print(f"  Error caught: {e}")
    
    # Example 5: Longer pipelines
    print("\n5. Building Longer Pipelines")
    print("-" * 30)
    
    # Each pipe operation creates a new composite
    step1 = validate | normalize
    step2 = step1 | extract
    
    # This is equivalent to the full pipeline
    result1 = await step2.invoke("test@example.com")
    result2 = await email_pipeline.invoke("test@example.com")
    print(f"  Step-by-step result: {result1}")
    print(f"  Full pipeline result: {result2}")
    print(f"  Results match: {result1 == result2}")
    
    # Example 6: Type transformations
    print("\n6. Type Transformations")
    print("-" * 30)
    
    word_count = WordCountBrick(name="count")
    
    # This creates a pipeline that transforms: str -> str -> int
    count_domain_words = extract | word_count
    
    email = "user@this-is-a-very-long-domain-name.com"
    word_count_result = await count_domain_words.invoke(email)
    print(f"  Email: {email}")
    print(f"  Domain word count: {word_count_result}")


if __name__ == "__main__":
    asyncio.run(main())