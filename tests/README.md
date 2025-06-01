# Nanobricks Test Suite

## Structure

```
tests/
├── conftest.py      # Shared fixtures and configuration
├── unit/           # Fast, isolated unit tests
├── integration/    # Tests of component interactions
└── fixtures/       # Test data and resources
```

## Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=nanobricks

# Run excluding slow tests
pytest -m "not slow"

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_protocol.py

# Run specific test
pytest tests/unit/test_protocol.py::test_basic_invocation
```

## Test Guidelines

### Unit Tests

- Test single components in isolation
- Use mocks for external dependencies
- Should run in <100ms each
- Focus on edge cases and error conditions

### Integration Tests

- Test real component interactions
- Can use real dependencies (database, etc.)
- May take longer (up to a few seconds)
- Test complete user scenarios

### Performance Tests

- Benchmark critical paths
- Track performance over time
- Alert on regressions
- Run separately from normal test suite

## Writing Tests

### Basic Test Structure

```python
import pytest
from nanobricks import Nanobrick

class TestMyNanobrick:
    @pytest.fixture
    def brick(self):
        return MyNanobrick()

    @pytest.mark.unit
    async def test_basic_functionality(self, brick):
        result = await brick.invoke("input")
        assert result == "expected"

    @pytest.mark.unit
    async def test_error_handling(self, brick):
        with pytest.raises(ValueError):
            await brick.invoke(None)
```

### Using Fixtures

```python
async def test_with_dependencies(mock_deps):
    brick = MyNanobrick()
    result = await brick.invoke("data", deps=mock_deps)
    assert result["from_db"] == [{"id": 1, "name": "test"}]
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
async def test_uppercase(input, expected):
    brick = UppercaseBrick()
    assert await brick.invoke(input) == expected
```

## Coverage Goals

- Core components: >95%
- Skills: >90%
- Examples: 100% (they must work!)
- Overall: >90%
