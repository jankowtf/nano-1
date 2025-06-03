#!/usr/bin/env python3
"""
Testing Patterns Example - How to Test Nanobricks

This example demonstrates various testing patterns for nanobricks including:
- Unit testing individual bricks
- Testing pipelines
- Mocking dependencies
- Testing error scenarios
- Async testing patterns
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

# First, let's create some example bricks to test
from nanobricks import Nanobrick


class TextProcessor(Nanobrick[str, str]):
    """Simple text processor for testing."""
    
    name = "text_processor"
    version = "1.0.0"
    
    async def invoke(self, text: str, *, deps=None) -> str:
        if not text:
            raise ValueError("Text cannot be empty")
        
        # Use optional dependency if available
        logger = deps.get("logger") if deps else None
        if logger:
            logger.info(f"Processing text of length {len(text)}")
        
        return text.upper().strip()


class WordCounter(Nanobrick[str, Dict[str, int]]):
    """Counts words in text."""
    
    name = "word_counter"
    version = "1.0.0"
    
    async def invoke(self, text: str, *, deps=None) -> Dict[str, int]:
        words = text.lower().split()
        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "longest_word": max(len(w) for w in words) if words else 0
        }


class DatabaseBrick(Nanobrick[str, List[Dict[str, Any]]]):
    """Brick that requires database dependency."""
    
    name = "database_brick"
    version = "1.0.0"
    
    async def invoke(self, query: str, *, deps=None) -> List[Dict[str, Any]]:
        if not deps or "db" not in deps:
            raise ValueError("Database connection required")
        
        db = deps["db"]
        return await db.execute(query)


# Now let's write comprehensive tests

class TestTextProcessor:
    """Unit tests for TextProcessor brick."""
    
    @pytest.fixture
    def brick(self):
        """Create a fresh brick instance for each test."""
        return TextProcessor()
    
    @pytest.mark.asyncio
    async def test_basic_processing(self, brick):
        """Test basic text processing."""
        result = await brick.invoke("hello world")
        assert result == "HELLO WORLD"
    
    @pytest.mark.asyncio
    async def test_with_whitespace(self, brick):
        """Test handling of whitespace."""
        result = await brick.invoke("  hello world  ")
        assert result == "HELLO WORLD"
    
    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, brick):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await brick.invoke("")
    
    @pytest.mark.asyncio
    async def test_with_logger_dependency(self, brick):
        """Test using optional logger dependency."""
        # Create a mock logger
        mock_logger = Mock()
        deps = {"logger": mock_logger}
        
        result = await brick.invoke("test", deps=deps)
        
        # Verify result
        assert result == "TEST"
        
        # Verify logger was called
        mock_logger.info.assert_called_once_with("Processing text of length 4")
    
    @pytest.mark.asyncio
    async def test_without_dependencies(self, brick):
        """Test that brick works without dependencies."""
        # Should work fine without deps
        result = await brick.invoke("test")
        assert result == "TEST"


class TestWordCounter:
    """Unit tests for WordCounter brick."""
    
    @pytest.fixture
    def brick(self):
        return WordCounter()
    
    @pytest.mark.asyncio
    async def test_word_counting(self, brick):
        """Test basic word counting functionality."""
        text = "The quick brown fox jumps over the lazy dog"
        result = await brick.invoke(text)
        
        assert result["total_words"] == 9
        assert result["unique_words"] == 8  # "the" appears twice
        assert result["longest_word"] == 5  # "quick", "brown", "jumps"
    
    @pytest.mark.asyncio
    async def test_empty_text(self, brick):
        """Test handling of empty text."""
        result = await brick.invoke("")
        
        assert result["total_words"] == 0
        assert result["unique_words"] == 0
        assert result["longest_word"] == 0
    
    @pytest.mark.parametrize("text,expected_total", [
        ("one", 1),
        ("one two", 2),
        ("one two three", 3),
        ("one one one", 3),
    ])
    @pytest.mark.asyncio
    async def test_various_inputs(self, brick, text, expected_total):
        """Test with various inputs using parametrize."""
        result = await brick.invoke(text)
        assert result["total_words"] == expected_total


class TestDatabaseBrick:
    """Tests for DatabaseBrick with dependency injection."""
    
    @pytest.fixture
    def brick(self):
        return DatabaseBrick()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database connection."""
        db = AsyncMock()
        db.execute.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
        return db
    
    @pytest.mark.asyncio
    async def test_with_database(self, brick, mock_db):
        """Test with mock database dependency."""
        deps = {"db": mock_db}
        
        result = await brick.invoke("SELECT * FROM users", deps=deps)
        
        # Verify result
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        
        # Verify database was called correctly
        mock_db.execute.assert_called_once_with("SELECT * FROM users")
    
    @pytest.mark.asyncio
    async def test_missing_database_dependency(self, brick):
        """Test that missing database raises error."""
        with pytest.raises(ValueError, match="Database connection required"):
            await brick.invoke("SELECT *")
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, brick):
        """Test handling of database errors."""
        # Create a mock that raises an exception
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        deps = {"db": mock_db}
        
        with pytest.raises(Exception, match="Database connection failed"):
            await brick.invoke("SELECT *", deps=deps)


class TestPipeline:
    """Tests for pipelines composed of multiple bricks."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline of text processor and word counter."""
        return TextProcessor() >> WordCounter()
    
    @pytest.mark.asyncio
    async def test_pipeline_execution(self, pipeline):
        """Test that pipeline processes data through both stages."""
        result = await pipeline.invoke("hello world")
        
        # Text should be uppercased by TextProcessor
        # Then counted by WordCounter
        assert result["total_words"] == 2
        assert result["unique_words"] == 2
    
    @pytest.mark.asyncio
    async def test_pipeline_with_dependencies(self, pipeline):
        """Test that dependencies flow through pipeline."""
        mock_logger = Mock()
        deps = {"logger": mock_logger}
        
        result = await pipeline.invoke("test text", deps=deps)
        
        # Verify result
        assert result["total_words"] == 2
        
        # Verify logger was called in first stage
        mock_logger.info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pipeline_error_propagation(self, pipeline):
        """Test that errors propagate through pipeline."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await pipeline.invoke("")


# Advanced testing patterns

class TestMockingPatterns:
    """Advanced mocking patterns for testing."""
    
    @pytest.mark.asyncio
    async def test_mock_entire_brick(self):
        """Test replacing an entire brick with a mock."""
        # Create a mock brick
        mock_brick = AsyncMock()
        mock_brick.invoke.return_value = {"mocked": True}
        
        # Use the mock
        result = await mock_brick.invoke("any input")
        assert result == {"mocked": True}
    
    @pytest.mark.asyncio
    async def test_partial_mock_with_patch(self):
        """Test partial mocking of brick methods."""
        brick = TextProcessor()
        
        # Patch just the processing logic
        with patch.object(brick, 'invoke', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = "MOCKED"
            
            result = await brick.invoke("test")
            assert result == "MOCKED"
    
    @pytest.mark.asyncio
    async def test_spy_pattern(self):
        """Test spying on brick calls while preserving behavior."""
        brick = TextProcessor()
        original_invoke = brick.invoke
        
        # Create a spy that calls the original
        call_count = 0
        async def spy_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return await original_invoke(*args, **kwargs)
        
        brick.invoke = spy_invoke
        
        # Use the brick
        result = await brick.invoke("test")
        
        # Verify behavior preserved
        assert result == "TEST"
        
        # Verify spy counted calls
        assert call_count == 1


class TestAsyncPatterns:
    """Testing patterns specific to async code."""
    
    @pytest.mark.asyncio
    async def test_concurrent_brick_calls(self):
        """Test calling a brick concurrently."""
        brick = WordCounter()
        
        # Create multiple concurrent calls
        tasks = [
            brick.invoke("text one"),
            brick.invoke("text two"),
            brick.invoke("text three")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all completed
        assert len(results) == 3
        assert all(r["total_words"] == 2 for r in results)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of timeouts."""
        class SlowBrick(Nanobrick[str, str]):
            async def invoke(self, input: str, *, deps=None) -> str:
                await asyncio.sleep(1)  # Simulate slow operation
                return input
        
        brick = SlowBrick()
        
        # Test with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(brick.invoke("test"), timeout=0.1)


# Test fixtures and utilities

@pytest.fixture
def mock_dependencies():
    """Create a standard set of mock dependencies."""
    return {
        "logger": Mock(),
        "db": AsyncMock(),
        "cache": AsyncMock(),
        "config": {"debug": True}
    }


@pytest.fixture
async def async_dependencies():
    """Create async dependencies (useful for cleanup)."""
    db = AsyncMock()
    cache = AsyncMock()
    
    yield {
        "db": db,
        "cache": cache
    }
    
    # Cleanup would go here
    await db.close()
    await cache.close()


# Integration test example
class TestIntegration:
    """Integration tests that test multiple components together."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self, mock_dependencies):
        """Test a complete pipeline with all dependencies."""
        # Create a complex pipeline
        processor = TextProcessor()
        counter = WordCounter()
        db_brick = DatabaseBrick()
        
        # Process text
        processed = await processor.invoke("hello world", deps=mock_dependencies)
        counts = await counter.invoke(processed, deps=mock_dependencies)
        
        # Store results (mocked)
        mock_dependencies["db"].execute.return_value = [{"id": 1}]
        stored = await db_brick.invoke(
            f"INSERT INTO word_counts VALUES ({counts})",
            deps=mock_dependencies
        )
        
        # Verify the flow
        assert processed == "HELLO WORLD"
        assert counts["total_words"] == 2
        assert len(stored) == 1


# Property-based testing example (requires hypothesis)
try:
    from hypothesis import given, strategies as st
    
    class TestPropertyBased:
        """Property-based tests for more thorough testing."""
        
        @given(st.text(min_size=1))
        @pytest.mark.asyncio
        async def test_text_processor_properties(self, text):
            """Test properties that should always hold."""
            brick = TextProcessor()
            result = await brick.invoke(text)
            
            # Properties that should always be true
            assert result == text.upper().strip()
            assert len(result) <= len(text)  # Stripping can only reduce length
            
except ImportError:
    # Hypothesis not installed
    pass


if __name__ == "__main__":
    # Run a simple test to verify everything works
    async def simple_test():
        processor = TextProcessor()
        result = await processor.invoke("Hello, World!")
        print(f"Processed: {result}")
        
        counter = WordCounter()
        counts = await counter.invoke(result)
        print(f"Counts: {counts}")
    
    asyncio.run(simple_test())