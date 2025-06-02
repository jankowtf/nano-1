# task-test-app

Built with [Nanobricks](https://github.com/yourusername/nanobricks).

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```python
from task-test-app import ExampleBrick

brick = ExampleBrick()
result = await brick.invoke("hello")
```

## Development

```bash
task dev:test    # Run tests
task dev:lint    # Run linters
task dev:format  # Format code
```
