# Nanobricks: Antifragile Code Components

## Core Philosophy

Nanobricks are the code equivalent of "antifragile nanobots" — atomic, self-sufficient components that gain strength from stress and compose organically into complex systems.

## Foundational Principles

### Package Architecture

- **uv-based**: Every nanobrick is a Python package managed by `uv`
- **src-layout**: Following the src-based project layout standard
- **Directory-based modules**: Top-level modules as directories, sub-modules as files
- **Absolute imports**: Always use absolute imports for clarity and consistency

## The Five Pillars

### 1. **Simple**

- Designed for clarity and straightforward implementation
- Easy for both humans and AIs to reason about
- Single responsibility principle at the atomic level
- Minimal cognitive overhead

### 2. **Standardized**

- Consistent interfaces — the "Lego Connector Mechanism" for code
- Predictable behavior patterns
- Universal protocols for:
  - Input/Output contracts
  - Configuration management
  - Error handling
  - Lifecycle hooks

### 3. **Composable**

- Seamless integration patterns
- Pipeline-ready (can be chained/piped together)
- Supports multiple composition patterns:
  - Sequential (A → B → C)
  - Parallel (A + B + C)
  - Nested (A(B(C)))
  - Hybrid workflows

### 4. **Batteries Included**

Each nanobrick ships with modular, self-contained interfaces:

- **API Layer** (FastAPI) — RESTful endpoints auto-generated
- **CLI Layer** (Typer) — Command-line interface out of the box
- **Frontend Layer** (Streamlit) — UI components (app/page/tab/subtab)
- **Data Layer** (SQLModel) — Database interaction when needed

### 5. **Scaffoldable**

- Instant end-to-end functionality
- Rails-inspired convention over configuration
- go-task powered automation
- AI-friendly cursorrules for guided implementation
- Progressive enhancement model

## Key Design Patterns

### Selected Patterns from LangChain & PydanticAI

Based on analysis of successful frameworks, nanobricks will leverage:

1. **Runnable Interface Pattern** (from LangChain)

   - Standardized methods: `invoke()`, `batch()`, `stream()`
   - Enables uniform interaction across all components

2. **Composition Pattern with Pipe Operator** (from LangChain's LCEL)

   - Use `|` operator for intuitive chaining
   - Declarative pipeline construction

3. **Dependency Injection** (from PydanticAI)

   - Context-based dependency passing
   - Enhances testability and flexibility

4. **Decorator Pattern** (from PydanticAI)

   - `@nanobrick` decorator for component registration
   - Clean, pythonic API

5. **Generic Programming** (from PydanticAI)
   - Type-safe interfaces using Python generics
   - Compile-time type checking

### The Nanobrick Interface

```python
from typing import Protocol, TypeVar, Generic, Any
from abc import abstractmethod

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
DepsT = TypeVar('DepsT')

class Nanobrick(Protocol, Generic[InputT, OutputT, DepsT]):
    """Universal interface for all nanobricks - inspired by LangChain's Runnable"""

    # Core identity
    name: str
    version: str

    # Primary execution methods (Runnable pattern)
    @abstractmethod
    async def invoke(self, input: InputT, *, deps: DepsT = None) -> OutputT:
        """Async execution with dependency injection"""
        ...

    def batch(self, inputs: list[InputT], *, deps: DepsT = None) -> list[OutputT]:
        """Batch processing"""
        ...

    async def stream(self, input: InputT, *, deps: DepsT = None):
        """Streaming execution"""
        ...

    # Composition support (LCEL-inspired)
    def __or__(self, other: 'Nanobrick') -> 'Nanobrick':
        """Pipe operator for composition"""
        ...

    # Battery interfaces
    def as_api(self) -> 'FastAPI': ...
    def as_cli(self) -> 'Typer': ...
    def as_ui(self) -> 'StreamlitComponent': ...
    def as_model(self) -> 'SQLModel': ...
```

### Antifragility Mechanisms

1. **Self-Healing**

   - Automatic retry with exponential backoff
   - Graceful degradation
   - Circuit breaker patterns

2. **Adaptation**

   - Runtime configuration updates
   - Dynamic scaling based on load
   - Learning from failures

3. **Evolution**
   - Version migration support
   - Backward compatibility guarantees
   - Progressive enhancement

## Implementation Strategy

### Phase 1: Core Framework

- Define base Nanobrick protocol
- Implement composition operators
- Create battery interface adapters

### Phase 2: Scaffolding System

- go-task templates
- Project generator CLI
- AI-optimized cursorrules

### Phase 3: Standard Library

- Common nanobricks (validators, transformers, etc.)
- Integration patterns
- Example compositions

### Phase 4: Ecosystem

- Package registry
- Composition marketplace
- Visual workflow builder

## Package Structure

```
my-nanobrick/
├── pyproject.toml      # uv-managed project file
├── src/
│   └── my_nanobrick/   # Directory-based module
│       ├── __init__.py
│       ├── core.py     # Core nanobrick implementation
│       ├── api.py      # FastAPI integration
│       ├── cli.py      # Typer CLI
│       ├── ui.py       # Streamlit components
│       └── models.py   # SQLModel definitions
└── tests/
```

## Example Usage

```python
from my_nanobrick import ValidatorData, DataTransformer
from typing import Dict

# Define a simple nanobrick with type safety
@nanobrick
class ValidatorData(Nanobrick[Dict, Dict, None]):
    async def invoke(self, input: Dict, *, deps=None) -> Dict:
        # Validation logic
        return validated_data

# Another nanobrick
@nanobrick
class DataTransformer(Nanobrick[Dict, Dict, None]):
    async def invoke(self, input: Dict, *, deps=None) -> Dict:
        # Transformation logic
        return transformed_data

# Compose using pipe operator (LCEL-style)
pipeline = ValidatorData() | DataTransformer()

# Use in multiple ways
app = pipeline.as_api()  # FastAPI app
cli = pipeline.as_cli()  # Typer CLI
ui = pipeline.as_ui()    # Streamlit component
```

## Open Questions

1. **Interface Standardization**: What's the minimal yet sufficient interface?
2. **Composition Rules**: How do we handle type safety across compositions?
3. **State Management**: Should nanobricks be stateless or support controlled state?
4. **Discovery Mechanism**: How do nanobricks find and connect to each other?
5. **Performance**: How do we ensure composition doesn't degrade performance?

## Implementation Roadmap

### Phase 1: Core Framework

1. Set up `nanobricks-core` package with uv
2. Implement Nanobrick protocol with generics
3. Create composition operators (`|`, parallel, etc.)
4. Build decorator system (`@nanobrick`)

### Phase 2: Battery Adapters

1. FastAPI adapter (`as_api()`)
2. Typer adapter (`as_cli()`)
3. Streamlit adapter (`as_ui()`)
4. SQLModel adapter (`as_model()`)

### Phase 3: Scaffolding

1. `uv`-based project template
2. go-task automation scripts
3. AI-optimized cursorrules
4. Example nanobricks library

### Phase 4: Testing & Documentation

1. Testing patterns for nanobricks
2. Type checking with mypy/pyright
3. Documentation generation
4. Best practices guide
