# test-nanobricks-app

A project built with [Nanobricks](https://github.com/yourusername/nanobricks).

## Setup

```bash
# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
pip install -e ".[dev]"  # For development
```

## Usage

```python
from nanobricks import NanobrickSimple

class MyBrick(NanobrickSimple[str, str]):
    async def invoke(self, input: str) -> str:
        return f"Processed: {input}"
```

## Testing

```bash
pytest
```
