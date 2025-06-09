# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nanobricks is a Python framework for creating "antifragile code components" - atomic, self-sufficient modules that compose like Lego bricks. The framework emphasizes simplicity, standardized interfaces, and emergent complexity through composition.

## Development Commands

### Essential Commands

- `task core:dev:all` - Run lint, test, and build docs (recommended before commits)
- `task core:dev:test` - Run pytest tests
- `pytest tests/unit/test_protocol.py::test_specific` - Run specific test
- `task core:dev:lint` - Run ruff and mypy linters
- `task core:dev:format` - Format code with ruff and black

### Documentation

- `task docs:preview` - Live preview documentation with hot reload
- `task docs:render` - Build Quarto documentation
- `task docs:publish` - Publish to GitHub Pages

### Scaffolding

- `nanobrick new my-brick` - Create new nanobrick interactively
- `nanobrick new list-templates` - Show available templates
- `nanobrick new my-brick --type validator --skill cli` - Create validator with CLI
- `nanobrick new my-service --type advanced --skill api --skill cli --docker --ci` - Full service

## Architecture

### Core Concepts

The framework uses a Protocol + ABC hybrid approach where `NanobrickProtocol` defines the interface for type checking and `NanobrickBase` provides runtime enforcement. All nanobricks implement three core methods:

- `async def invoke(input: T_in, *, deps: T_deps = None) -> T_out` - Process input
- `def invoke_sync(input: T_in, *, deps: T_deps = None) -> T_out` - Sync wrapper
- `def __rshift__(other) -> NanobrickProtocol` - Pipe operator composition

### Composition Patterns

Primary composition uses the pipe operator (`>>`):
```python
pipeline = validator >> transformer >> processor
result = await pipeline.invoke(data)
```

Type checking ensures compatible interfaces with helpful error messages when types don't align.

### Skills System

Optional capabilities activate via decorators:
```python
@with_logging
@with_api(path="/process")
@with_cache(ttl=300)
class MyBrick(Nanobrick[Dict, Dict]):
    # Gets logging, API endpoint, and caching automatically
```

### Dependency Injection

Dependencies flow through the `deps` parameter using TypedDict contracts:
```python
class StandardDeps(TypedDict, total=False):
    db: Database
    cache: Cache
    config: Config
```

### Configuration System

TOML-based configuration with environment inheritance:
- Base config in `[nanobrick]` section
- Environment overrides in `[nanobrick.production]`, `[nanobrick.test]`
- Feature flags in `[nanobrick.features]`
- Skill configs in `[nanobrick.skills.api]`, etc.

### Testing Structure

- `tests/unit/` - Test individual nanobricks
- `tests/integration/` - Test compositions and workflows
- `tests/conftest.py` - Shared fixtures (sample_data, temp_config_file, mock_deps)
- Use `pytest-asyncio` for async testing

## Version Management

**IMPORTANT**: We follow atomic commit-based development. Version bumps are rare and intentional.

### Current Version: v0.1.0 (Reset)
As of June 2025, we reset from v0.2.5 to v0.1.0 to reflect:
- Shift to atomic commit-based development
- More accurate project maturity representation
- Better semantic versioning alignment

### Version Management Commands

1. `task version:current` - Check current version
2. `task version:validate:consistency` - Verify version sync across files
3. `task version:bump:patch:safe` - Bump patch with safeguards
4. `task version:bump:minor:safe` - Bump minor with safeguards
5. `task version:bump:major:safe` - Bump major with safeguards

### Version Bump Safeguards

Before any version bump:
1. Create `.version-bump-rationale.md` explaining why
2. Update CHANGELOG.md `[Unreleased]` section
3. Confirm this isn't better as atomic commits
4. Run `task version:validate:consistency`
5. After bump, manually sync `__version__` in `src/nanobricks/__init__.py`

### When to Bump Versions

Only bump versions for:
- Major feature sets (multiple related atomic commits)
- Breaking API changes
- Significant architectural shifts
- NOT for individual features or fixes (use atomic commits)

## AI Integration Strategy

- Primary: MCP (Model Context Protocol) for tool integration
- Secondary: A2A for agent-to-agent communication
- UI Layer: AG-UI for interactive interfaces

## Code Conventions

- Use absolute imports throughout
- Directory-based modules at top level
- Type annotations with Python generics
- Runtime validation with beartype

## Memories

- Echo statements in go-task files cannot have `:`
- After version bump, manually sync `__version__` in src/nanobricks/__init__.py
- Keep examples in `examples/` and `docs/quarto/human.qmd` in sync with implementation