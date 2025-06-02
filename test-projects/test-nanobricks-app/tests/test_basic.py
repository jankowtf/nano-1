"""Basic tests."""

import pytest
from test-nanobricks-app import GreetingBrick, UppercaseBrick, greeting_pipeline


@pytest.mark.asyncio
async def test_greeting_brick():
    brick = GreetingBrick()
    result = await brick.invoke("Alice")
    assert result == "Hello, Alice!"


@pytest.mark.asyncio
async def test_uppercase_brick():
    brick = UppercaseBrick()
    result = await brick.invoke("hello world")
    assert result == "HELLO WORLD"


@pytest.mark.asyncio
async def test_pipeline():
    result = await greeting_pipeline.invoke("test")
    assert result == "HELLO, TEST!"
