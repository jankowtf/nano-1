# Nanobricks

**Build antifragile code that composes like Lego bricks**

Nanobricks is a Python framework for creating atomic, self-sufficient code components that gain strength from stress. Think of it as functional programming meets microservices meets Lego  where every piece is designed to work alone or together, adapting and improving under pressure.

## ( Key Features

- **= Protocol-First Design**: Clean interfaces with runtime enforcement via Protocol + ABC hybrid
- **= Composable by Default**: Chain components with the pipe operator (`|`) for elegant data flows
- **=� Antifragile Architecture**: Components that self-heal and adapt under stress
- **<� Zero Dependencies**: Each brick is self-contained  add only what you need
- **� Async-First**: Built for modern Python with full async/await support
- **=' Optional Skills**: Activate capabilities (API, CLI, logging) only when needed
- **<� Type-Safe**: Full type annotations with runtime validation support
- **=� Production-Ready**: Built-in error handling, resource management, and observability

## =� Installation

Install with [uv](https://github.com/astral-sh/uv) (recommended):

```bash
uv pip install nanobricks
```

Or with pip:

```bash
pip install nanobricks
```

## =� Quick Start

### Your First Nanobrick

```python
from nanobricks import Nanobrick
from typing import Dict, Any

class Greeter(Nanobrick[str, str, None]):
    """A simple nanobrick that greets people"""

    name = "greeter"
    version = "1.0.0"

    async def invoke(self, input: str, *, deps: None = None) -> str:
        return f"Hello, {input}!"

# Use it
greeter = Greeter()
result = await greeter.invoke("World")  # "Hello, World!"
```

### Composition Magic

Chain nanobricks together with the pipe operator:

```python
from nanobricks import Nanobrick

class Uppercase(Nanobrick[str, str, None]):
    name = "uppercase"
    version = "1.0.0"

    async def invoke(self, input: str, *, deps: None = None) -> str:
        return input.upper()

class Exclaim(Nanobrick[str, str, None]):
    name = "exclaim"
    version = "1.0.0"

    async def invoke(self, input: str, *, deps: None = None) -> str:
        return f"{input}!!!"

# Compose them!
pipeline = Greeter() | Uppercase() | Exclaim()
result = await pipeline.invoke("nanobricks")  # "HELLO, NANOBRICKS!!!"
```

### Type Safety with v0.1.2

Handle type mismatches elegantly with the new type utilities:

```python
from nanobricks import Nanobrick, Result, string_to_dict, dict_to_json

# Use Result for safe error handling
class SafeDivider(Nanobrick[tuple[float, float], Result[float, str]]):
    name = "divider"
    
    async def invoke(self, input: tuple[float, float]) -> Result[float, str]:
        x, y = input
        if y == 0:
            return Result.err("Division by zero")
        return Result.ok(x / y)

# Use type adapters to connect incompatible bricks
class ConfigParser(Nanobrick[str, str]):
    name = "parser"
    
    async def invoke(self, input: str) -> str:
        return "host=localhost,port=8080"

class ConfigValidator(Nanobrick[dict, dict]):
    name = "validator"
    
    async def invoke(self, input: dict) -> dict:
        return {"validated": True, **input}

# Type adapter makes it work!
config_pipeline = ConfigParser() | string_to_dict() | ConfigValidator() | dict_to_json()
result = await config_pipeline.invoke("config.ini")
# {"validated": true, "host": "localhost", "port": "8080"}
```

## <� Core Concepts

- **Nanobricks**: Self-contained modules implementing the Runnable protocol
- **Skills**: Optional capabilities that activate when needed
- **Composition**: Combine bricks using pipes, branches, and parallel flows
- **Dependencies**: Clean dependency injection via TypedDict contracts

[=� Read the full documentation �](https://your-github-pages-url.github.io/nanobricks)

## =� Example Usage

### Adding Skills

```python
from nanobricks import Nanobrick
from nanobricks.skills import with_logging, with_api, with_cli
from typing import Dict

@with_logging
@with_api(path="/process")
@with_cli(name="processor")
class DataProcessor(Nanobrick[Dict, Dict, None]):
    """Process data with automatic logging, API, and CLI"""

    name = "data_processor"
    version = "1.0.0"

    async def invoke(self, input: Dict, *, deps: None = None) -> Dict:
        self.logger.info(f"Processing: {input}")
        return {"processed": True, **input}

# Now you have:
# - Automatic logging with context
# - REST API endpoint at /process
# - CLI command: python -m your_module processor --input '{"key": "value"}'
```

### Validators and Transformers

```python
from nanobricks import Validator, Transformer
from pydantic import BaseModel

class UserInput(BaseModel):
    name: str
    age: int

class UserValidator(Validator[Dict, UserInput, None]):
    """Validate and parse user input"""

    async def invoke(self, input: Dict, *, deps: None = None) -> UserInput:
        return UserInput(**input)

class AgeTransformer(Transformer[UserInput, UserInput, None]):
    """Transform user age to dog years"""

    async def invoke(self, input: UserInput, *, deps: None = None) -> UserInput:
        input.age = input.age * 7
        return input

# Compose validation and transformation
pipeline = UserValidator() | AgeTransformer() | DataProcessor()
```

### Advanced Composition

```python
from nanobricks import branch, parallel, fallback

# Conditional branching
router = branch(
    condition=lambda x: x.get("premium", False),
    if_true=PremiumProcessor(),
    if_false=StandardProcessor()
)

# Parallel execution
analyzer = parallel(
    SentimentAnalyzer(),
    KeywordExtractor(),
    LanguageDetector()
)

# Error handling with fallbacks
safe_processor = DataProcessor() | fallback(
    DefaultProcessor(),
    on_error=ProcessingError
)
```


## 📚 Documentation

Full documentation is available at [https://your-github-pages-url.github.io/nanobricks](https://your-github-pages-url.github.io/nanobricks)

### Quick Links

- [🚀 Quick Start Guide](https://your-github-pages-url.github.io/nanobricks/quickstart) - Get up and running fast
- [📦 Distribution & Deployment](https://your-github-pages-url.github.io/nanobricks/distribution) - Using Nanobricks in your projects
- [📖 Tutorial](https://your-github-pages-url.github.io/nanobricks/tutorial) - Step-by-step learning
- [🛠️ SDK Guide](https://your-github-pages-url.github.io/nanobricks/sdk-guide) - Building applications
- [🏛️ Architecture Overview](https://your-github-pages-url.github.io/nanobricks/architecture) - How it all works
- [💡 Design Philosophy](https://your-github-pages-url.github.io/nanobricks/design-philosophy) - Why we built it this way

### Building Documentation Locally

```bash
task docs:preview  # Live preview with hot reload
task docs:render   # Build static site
task docs:open     # Open built docs in browser
```

## =� Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/nanobricks.git
   cd nanobricks
   ```

2. Set up development environment with uv:

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

3. Run tests:

   ```bash
   task dev:test  # or pytest
   ```

4. Run all checks:
   ```bash
   task dev:all  # lint, type check, test, and build docs
   ```

## > Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run the test suite and ensure all checks pass
5. Commit with a descriptive message
6. Push to your branch and open a Pull Request

Please read our [Contributing Guidelines](CONTRIBUTING.md) for details on our code of conduct and development process.

### Development Commands

- `task dev:test` - Run tests
- `task dev:lint` - Run linters
- `task dev:format` - Format code
- `task docs:preview` - Preview documentation
- `task brick:new BRICK_NAME=my_brick` - Create new nanobrick scaffold

## =� License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with d by the Nanobricks Community
</p>

<p align="center">
  <a href="https://github.com/yourusername/nanobricks">GitHub</a> "
  <a href="https://your-github-pages-url.github.io/nanobricks">Documentation</a> "
  <a href="https://pypi.org/project/nanobricks">PyPI</a>
</p>
