# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nanobricks is a Python framework for creating "antifragile code components" - atomic, self-sufficient modules that compose like Lego bricks. The framework emphasizes simplicity, standardized interfaces, and emergent complexity through composition.

## Development Commands

### Essential Commands

- `task dev:setup` - Initial development environment setup
- `task dev:test` - Run pytest tests
- `task dev:lint` - Run ruff and mypy linters
- `task dev:format` - Format code with ruff and black
- `task dev:all` - Run all checks and render documentation

### Documentation

- `task docs:preview` - Live preview documentation with hot reload
- `task docs:render` - Build Quarto documentation
- `task docs:publish` - Publish to GitHub Pages

### Scaffolding

- `nanobrick new my-brick` - Create new nanobrick interactively
- `nanobrick new list-templates` - Show available templates
- `nanobrick new my-brick --type validator --skill cli` - Create validator with CLI
- `nanobrick new my-service --type advanced --skill api --skill cli --docker --ci` - Full service
- `task brick:new BRICK_NAME=my_brick` - Quick scaffold using Taskfile

## Architecture

### Core Concepts

- **Nanobricks**: Self-contained modules implementing the Runnable protocol
- **Skills**: Optional capabilities (API, CLI, UI, DB, AI, logging, observability, deployment) that activate when needed
- **Composition**: Modules compose via pipe operator (`|`) and other patterns (branching, parallel, fan-out/fan-in)
- **Antifragility**: Components that gain strength from stress through self-healing and adaptation

### Key Architectural Decisions

- **Protocol + ABC Hybrid**: Protocol for type checking, ABC for runtime enforcement
- **Simple Error Semantics**: Fail-fast by default, explicit error handling via fallbacks
- **State as Skill**: Stateless by default, state management via optional skills
- **Clean Dependency Injection**: Dependencies flow through composition with TypedDict contracts
- **Contracts & Invariants**: Built-in design-by-contract support
- **Hot-swapping**: Dynamic component replacement without downtime
- **Resource Management**: Context managers and explicit resource limits
- **Branching/Merging**: Beyond linear pipelines with conditional and parallel flows

### Package Structure

```
nanobrick/
├── pyproject.toml      # uv-managed dependencies
├── nanobrick.toml      # TOML configuration
├── src/
│   └── my_nanobrick/   # Directory-based module
│       ├── __init__.py
│       ├── core.py     # Core implementation
│       ├── skills/
│       │   ├── api.py  # FastAPI integration
│       │   ├── cli.py  # Typer CLI
│       │   ├── ui.py   # Streamlit components
│       │   ├── logging.py  # Loguru integration
│       │   └── observability.py  # OpenTelemetry
│       └── models.py   # SQLModel definitions
└── tests/
```

### Core Interface

```python
from typing import Protocol, Generic, TypeVar, runtime_checkable
from abc import ABC, abstractmethod

T_in = TypeVar('T_in')
T_out = TypeVar('T_out')
T_deps = TypeVar('T_deps')

@runtime_checkable
class NanobrickProtocol(Protocol, Generic[T_in, T_out, T_deps]):
    name: str
    version: str

    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out: ...
    def invoke_sync(self, input: T_in, *, deps: T_deps = None) -> T_out: ...
    def __or__(self, other: 'NanobrickProtocol') -> 'NanobrickProtocol': ...

class NanobrickBase(ABC, Generic[T_in, T_out, T_deps]):
    """Base class with runtime enforcement"""

    @abstractmethod
    async def invoke(self, input: T_in, *, deps: T_deps = None) -> T_out:
        pass
```

### Configuration System

- **TOML-based**: Clean, readable configuration format
- **Feature Flags**: Static and dynamic feature management
- **Environment-specific**: Different configs for dev/prod/test
- **Inheritance**: Base configurations with overrides
- **Skill Config**: Declarative skill activation

### AI Integration Strategy

- Primary: MCP (Model Context Protocol) for tool integration
- Secondary: A2A for agent-to-agent communication
- UI Layer: AG-UI for interactive interfaces

## Development Guidelines

### Code Conventions

- Use absolute imports throughout
- Directory-based modules at top level for clarity
- File-based sub-modules to maintain simplicity
- Type annotations with Python generics for type safety
- Runtime validation with beartype (when implemented)

### Testing

- Tests go in `tests/` directory with unit/ and integration/ subdirectories
- Follow pytest conventions with async support
- Test individual nanobricks and their compositions
- Run all tests: `pytest`
- Run with coverage: `pytest --cov=nanobricks`
- Shared fixtures in tests/conftest.py
- Keep tests SIMPLE, meaningful, and fast

### Documentation

- Generally put all documentation in the @docs/ cs folder and favor @quarto/ qmds over one-off the Markdown files 
- Quarto-based documentation in `quarto/` directory
- Design documents in `docs/` directory
- Each nanobrick should have inline documentation explaining its purpose and usage
- Ensure that all examples in `examples/` and `quarto/human.qmd` are always
  kept in sync with the implementation state of the codebase

## Version Management

**IMPORTANT**: All version management must be done through the Task system, not manually. The version in `pyproject.toml` is the single source of truth.

### Complete Release Workflow

#### 1. Prepare Changes
- Make your code changes on a feature branch
- Write tests for new features
- Update documentation as needed
- Run `task core:dev:all` to ensure all checks pass

#### 2. Update CHANGELOG
- Keep changes in the `[Unreleased]` section during development
- Follow [Keep a Changelog](https://keepachangelog.com) format
- Group changes by: Added, Changed, Fixed, Deprecated, Removed, Security

#### 3. Version Bump and Release

**Option A: Full Automated Release (Recommended)**
```bash
# 1. Check current version
task version:current

# 2. Bump version (choose one)
task version:bump:patch  # Bug fixes: 0.1.0 → 0.1.1
task version:bump:minor  # New features: 0.1.0 → 0.2.0  
task version:bump:major  # Breaking changes: 0.1.0 → 1.0.0

# 3. Update __version__ in src/nanobricks/__init__.py to match

# 4. Move [Unreleased] to new version section in CHANGELOG.md
# The date will be automatically set to today's date

# 5. Complete release (commit, tag, push)
task version:release
```

**Option B: Step-by-Step Release**
```bash
# After version bump and CHANGELOG update:
task version:commit:version  # Commit with auto-generated message
task version:tag:create      # Create git tag
git push origin main         # Push commits
git push origin --tags       # Push tags
```

### Version Tasks Reference

- `task version:current` - Show current version from pyproject.toml
- `task version:bump:patch` - Increment patch version (0.1.0 → 0.1.1)
- `task version:bump:minor` - Increment minor version (0.1.0 → 0.2.0)
- `task version:bump:major` - Increment major version (0.1.0 → 1.0.0)
- `task version:commit:version` - Commit changes with version message
- `task version:tag:create` - Create annotated git tag for current version
- `task version:release` - Complete release workflow (commit, tag, push)

### Important Notes

1. **Version Sync**: After bumping version with task, manually update `__version__` in `src/nanobricks/__init__.py`
2. **CHANGELOG Format**: The commit task checks for version entry in CHANGELOG.md
3. **Clean Working Directory**: Version tasks require a clean git state
4. **Semantic Versioning**: Follow [SemVer](https://semver.org) principles:
   - MAJOR: Incompatible API changes
   - MINOR: Backwards-compatible functionality
   - PATCH: Backwards-compatible bug fixes

## Memories
- Remember that echo statements in go-task files cannot have `:`
- dude, no...\
\
`- echo "2. Create tag: task version:semver:tag:create"` is NOT allowed but `- echo "2. Create tag - task version:semver:tag:create"` is.\
\
Try again pls