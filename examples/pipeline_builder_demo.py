#!/usr/bin/env python3
"""Demonstration of the PipelineBuilder fluent interface."""

import asyncio
from typing import Dict, List, Any

from nanobricks import Nanobrick, PipelineBuilder
from nanobricks.pipeline_builder import Pipeline
from nanobricks.typing import string_to_dict, dict_to_json


# Define some example nanobricks
class DataLoader(Nanobrick[str, Dict[str, Any]]):
    """Load data from a string (simulated)."""
    
    async def invoke(self, input: str, *, deps=None) -> Dict[str, Any]:
        # Simulate loading data based on input
        return {
            "source": input,
            "type": "email" if "@" in input else "phone" if input.isdigit() else "text",
            "data": input,
            "timestamp": "2025-01-06T12:00:00Z"
        }


class EmailValidator(Nanobrick[Dict[str, Any], Dict[str, Any]]):
    """Validate and enrich email data."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
        email = input.get("data", "")
        if "@" not in email:
            raise ValueError(f"Invalid email: {email}")
        
        domain = email.split("@")[1]
        return {
            **input,
            "validated": True,
            "domain": domain,
            "is_corporate": not domain.endswith((".gmail.com", ".yahoo.com", ".hotmail.com"))
        }


class PhoneValidator(Nanobrick[Dict[str, Any], Dict[str, Any]]):
    """Validate and enrich phone data."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
        phone = input.get("data", "")
        if not phone.replace("-", "").isdigit():
            raise ValueError(f"Invalid phone: {phone}")
        
        return {
            **input,
            "validated": True,
            "formatted": f"+1-{phone}" if not phone.startswith("+") else phone,
            "country": "US"  # Simplified
        }


class TextProcessor(Nanobrick[Dict[str, Any], Dict[str, Any]]):
    """Process general text data."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> Dict[str, Any]:
        text = input.get("data", "")
        return {
            **input,
            "processed": True,
            "length": len(text),
            "words": len(text.split()),
            "uppercase": text.upper()
        }


class SentimentAnalyzer(Nanobrick[Dict[str, Any], float]):
    """Analyze sentiment (mock implementation)."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> float:
        # Mock sentiment analysis
        text = str(input.get("data", ""))
        positive_words = ["good", "great", "excellent", "happy", "love"]
        negative_words = ["bad", "terrible", "hate", "sad", "angry"]
        
        score = 0.5  # Neutral
        for word in positive_words:
            if word in text.lower():
                score += 0.1
        for word in negative_words:
            if word in text.lower():
                score -= 0.1
        
        return max(0.0, min(1.0, score))


class LanguageDetector(Nanobrick[Dict[str, Any], str]):
    """Detect language (mock implementation)."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> str:
        # Mock language detection
        text = str(input.get("data", ""))
        if any(char in text for char in "áéíóúñ"):
            return "es"
        elif any(char in text for char in "àèìòù"):
            return "it"
        elif any(char in text for char in "äöüß"):
            return "de"
        else:
            return "en"


class ResultCombiner(Nanobrick[List[Any], Dict[str, Any]]):
    """Combine results from parallel analysis."""
    
    async def invoke(self, input: List[Any], *, deps=None) -> Dict[str, Any]:
        sentiment, language = input
        return {
            "sentiment_score": sentiment,
            "sentiment": "positive" if sentiment > 0.6 else "negative" if sentiment < 0.4 else "neutral",
            "language": language,
            "analysis_complete": True
        }


class Formatter(Nanobrick[Dict[str, Any], str]):
    """Format the final output."""
    
    async def invoke(self, input: Dict[str, Any], *, deps=None) -> str:
        lines = ["=== Processing Result ==="]
        for key, value in input.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)


class ErrorLogger(Nanobrick[Exception, Dict[str, Any]]):
    """Log errors and return error response."""
    
    async def invoke(self, input: Exception, *, deps=None) -> Dict[str, Any]:
        return {
            "error": True,
            "error_type": type(input).__name__,
            "error_message": str(input),
            "handled": True
        }


async def demo_basic_pipeline():
    """Demonstrate a basic linear pipeline."""
    print("\n=== Basic Linear Pipeline ===")
    
    pipeline = (
        Pipeline()
        .start_with(DataLoader(name="loader"))
        .then(EmailValidator(name="email_validator"))
        .then(Formatter(name="formatter"))
        .build()
    )
    
    result = await pipeline.invoke("user@example.com")
    print(result)


async def demo_branching_pipeline():
    """Demonstrate conditional branching."""
    print("\n=== Branching Pipeline ===")
    
    pipeline = (
        Pipeline()
        .start_with(DataLoader(name="loader"))
        .branch(
            ("email", EmailValidator(name="email_validator")),
            ("phone", PhoneValidator(name="phone_validator")),
            ("text", TextProcessor(name="text_processor"))
        )
        .then(Formatter(name="formatter"))
        .build()
    )
    
    # Test different inputs
    for input_data in ["john@company.com", "555-1234", "Hello world!"]:
        print(f"\nProcessing: {input_data}")
        result = await pipeline.invoke(input_data)
        print(result)


async def demo_parallel_pipeline():
    """Demonstrate parallel execution."""
    print("\n=== Parallel Execution Pipeline ===")
    
    pipeline = (
        Pipeline()
        .start_with(DataLoader(name="loader"))
        .then(TextProcessor(name="preprocessor"))
        .parallel(
            SentimentAnalyzer(name="sentiment"),
            LanguageDetector(name="language")
        )
        .merge_with(ResultCombiner(name="combiner"))
        .then(Formatter(name="formatter"))
        .build()
    )
    
    result = await pipeline.invoke("This is a great example!")
    print(result)


async def demo_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling Pipeline ===")
    
    pipeline = (
        Pipeline()
        .start_with(DataLoader(name="loader"))
        .then(EmailValidator(name="validator"))
        .catch_errors(ErrorLogger(name="error_logger"))
        .then(Formatter(name="formatter"))
        .build()
    )
    
    # Test with invalid email
    result = await pipeline.invoke("not-an-email")
    print(result)


async def demo_type_adaptation():
    """Demonstrate type adaptation."""
    print("\n=== Type Adaptation Pipeline ===")
    
    class StringInput(Nanobrick[str, str]):
        async def invoke(self, input: str, *, deps=None) -> str:
            return f"key1={input},key2=test"
    
    class DictProcessor(Nanobrick[Dict[str, str], Dict[str, str]]):
        async def invoke(self, input: Dict[str, str], *, deps=None) -> Dict[str, str]:
            return {k: v.upper() for k, v in input.items()}
    
    pipeline = (
        Pipeline()
        .start_with(StringInput(name="string_input"))
        .adapt(string_to_dict())
        .then(DictProcessor(name="dict_processor"))
        .adapt(dict_to_json(indent=2))
        .build()
    )
    
    result = await pipeline.invoke("hello")
    print(result)


async def demo_pipeline_introspection():
    """Demonstrate pipeline visualization and explanation."""
    print("\n=== Pipeline Introspection ===")
    
    builder = (
        Pipeline()
        .start_with(DataLoader(name="loader"))
        .branch(
            ("email", EmailValidator(name="email_validator")),
            ("phone", PhoneValidator(name="phone_validator"))
        )
        .parallel(
            SentimentAnalyzer(name="sentiment"),
            LanguageDetector(name="language")
        )
        .merge_with(ResultCombiner(name="combiner"))
        .then(Formatter(name="formatter"))
        .name("ComplexAnalysisPipeline")
    )
    
    print("\nVisualization:")
    print(builder.visualize())
    
    print("\n\nExplanation:")
    print(builder.explain())


async def main():
    """Run all demonstrations."""
    print("PipelineBuilder Demonstration")
    print("=" * 50)
    
    await demo_basic_pipeline()
    await demo_branching_pipeline()
    await demo_parallel_pipeline()
    await demo_error_handling()
    await demo_type_adaptation()
    await demo_pipeline_introspection()
    
    print("\n" + "=" * 50)
    print("Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())