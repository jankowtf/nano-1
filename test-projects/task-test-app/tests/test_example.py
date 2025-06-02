"""Example tests."""

import pytest
from task-test-app import ExampleBrick


@pytest.mark.asyncio
async def test_example_brick():
    brick = ExampleBrick()
    result = await brick.invoke("test")
    assert result == "Processed: test"
