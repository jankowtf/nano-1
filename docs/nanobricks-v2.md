# Nanobricks v2: Evolved Concept

## Core Philosophy Refined

Nanobricks are **composable units of potential** - they carry capabilities (skills) that activate only when needed, maintaining simplicity while offering power.

## Key Insights from Discussion

### 1. Packaging Flexibility

- **Packages**: For complex, reusable nanobricks (via uv)
- **Modules**: For simpler nanobricks within a project
- **Collections**: Themed groups of related nanobricks in one package

### 2. Skills (formerly "Batteries")

Optional capabilities that can be activated:

- **API Skill**: FastAPI integration
- **CLI Skill**: Typer commands
- **UI Skill**: Streamlit components
- **DB Skill**: SQLModel persistence
- **AI Skill**: LLM/Agent capabilities (via MCP or ag-ui protocols)

### 3. Composition Patterns

#### Pattern A: Pipeline Composition (R-style)

```python
# Within Python code
result = (
    ValidatorData()
    | DataTransformer()
    | DataPersistor()
).invoke(data)
```

#### Pattern B: Augmentation Composition

```python
# Adding to existing FastAPI
app = FastAPI()
app.mount("/health", HealthMonitor().as_api())
app.mount("/metrics", MetricsCollector().as_api())

# Adding to existing Streamlit
st_app = st.container()
st_app.add(DataVisualizer().as_ui())
```

#### Pattern C: Hybrid Composition

```python
# Nanobricks enhancing each other
enhanced_validator = (
    ValidatorData()
    .with_skill(AISkill(model="gpt-4"))
    .with_skill(SkillAI(endpoint="/validate"))
)
```

## Architecture Levels

### Level 1: Core Nanobrick Protocol

```python
from typing import Protocol, TypeVar, Generic

T_in = TypeVar('T_in')
T_out = TypeVar('T_out')

class Nanobrick(Protocol, Generic[T_in, T_out]):
    """Minimal interface - just input/output transformation"""

    async def invoke(self, input: T_in) -> T_out: ...

    def __or__(self, other: 'Nanobrick') -> 'Nanobrick': ...
```

### Level 2: Skilled Nanobrick

```python
class SkilledNanobrick(Nanobrick[T_in, T_out]):
    """Nanobrick with optional skills"""

    def with_skill(self, power: Skill) -> 'SkilledNanobrick':
        """Add a skill to this nanobrick"""
        ...

    def activate_api(self) -> FastAPI:
        """Activate API skill if available"""
        ...
```

### Level 3: Stateful Nanobrick

```python
class StatefulNanobrick(SkilledNanobrick[T_in, T_out]):
    """Nanobrick with memory and learning capabilities"""

    async def learn_from(self, experience: Experience) -> None:
        """Antifragile learning mechanism"""
        ...
```

## Skill System

### Skill Interface

```python
class Skill(Protocol):
    """Base interface for all skills"""

    def enhance(self, nanobrick: Nanobrick) -> Nanobrick:
        """Enhance a nanobrick with this power"""
        ...
```

### Example Skills

```python
@skill
class HealthMonitorPower:
    """Adds /health endpoint to any nanobrick"""
    endpoints = ["/health", "/ready", "/live"]

@skill
class StreamlitTabPower:
    """Adds a Streamlit tab to any nanobrick"""
    tab_name: str = "Nanobrick Output"

@skill
class MCPServerPower:
    """Enables MCP server protocol for AI communication"""
    protocol: str = "mcp"
```

## Discovery Mechanisms

### 1. Static (Default)

```python
from nanobricks.stdlib import ValidatorData, DataTransformer
from my_project.bricks import CustomProcessor
```

### 2. Dependency Injection

```python
@inject
class MyWorkflow:
    validator: ValidatorData
    transformer: DataTransformer
```

### 3. Dynamic Discovery (Future)

```python
# Nanobricks register themselves
@nanobrick(discoverable=True, tags=["validation", "data"])
class SmartValidator:
    pass

# Later, discover by capability
validators = discover_nanobricks(tag="validation")
```

## Project Structure Options

### Option A: Single Nanobrick Package

```
my-nanobrick/
├── pyproject.toml
└── src/
    └── my_nanobrick/
        ├── __init__.py
        ├── core.py
        └── skills/
            ├── api.py
            ├── cli.py
            └── ui.py
```

### Option B: Nanobrick Collection

```
nanobricks-validators/
├── pyproject.toml
└── src/
    └── validators/
        ├── __init__.py
        ├── email.py      # ValidatorEmail nanobrick
        ├── phone.py      # PhoneValidator nanobrick
        └── address.py    # AddressValidator nanobrick
```

### Option C: Project-Local Nanobricks

```
my-project/
├── pyproject.toml
├── src/
│   └── my_app/
│       └── nanobricks/  # Local nanobricks as modules
│           ├── __init__.py
│           ├── custom_validator.py
│           └── custom_transformer.py
└── external_bricks/     # Git submodules or pip deps
```

## Open Questions for Next Phase

1. **Skill Activation**: Should skills be activated explicitly or auto-detect context?
2. **Type Safety**: How do we maintain type safety through complex compositions?
3. **Testing Strategy**: How do we test nanobricks in isolation vs. composition?
4. **Performance**: Should we support async-only or both sync/async?
5. **Versioning**: How do we handle nanobrick evolution and compatibility?
