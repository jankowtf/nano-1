# Nanobricks Agentic Documentation

> AI-first documentation for the Nanobricks framework, optimized for AI coding agents.

## What is This?

This directory contains documentation specifically designed for AI agents (like Claude Code, GitHub Copilot, etc.) to understand and work with the Nanobricks framework efficiently. Unlike traditional documentation that tells a story, this documentation provides:


- **Immediate context** for every concept
- **Executable contracts** that validate code
- **Structured knowledge** in machine-readable formats
- **Task-oriented guidance** with copy-paste solutions
- **MCP-compatible tools** for integration

## Entry Points

1. **llms.txt** - Start here! Follows the llms.txt standard for AI agents
2. **_contracts/** - Executable specifications that validate your code
3. **tasks/** - Step-by-step guides for common tasks
4. **memories/** - Structured knowledge in JSON-LD format
5. **tools/** - MCP tool definitions for IDE integration

## How to Use This Documentation

### For AI Agents

```python
# 1. Read llms.txt for immediate context
# 2. Find your task in tasks/
# 3. Copy the code template
# 4. Modify for your use case
# 5. Validate with contracts
```

### For Human Developers

While optimized for AI agents, humans can benefit too:


- Use task definitions as quick references
- Run contract validators to check implementations
- Browse memories/ for structured concept maps
- Integrate tools/ with your IDE

## Key Principles

1. **Structure > Narrative**: Information is structured, not story-based
2. **Executable > Descriptive**: Contracts and examples run
3. **Tasks > Topics**: Organized by what you want to do
4. **Validated > Assumed**: Everything can be verified

## Integration with Human Docs

This AI-centric documentation complements the human-oriented Quarto docs:


- Human docs: `../quarto/` - Explanations and concepts
- AI docs: `./` - Structures and patterns
- Bridge: `../_bridge/` - Tools to connect both

## Quick Example

```python
# Task: Create a validator nanobrick
# Context: from ./tasks/create-nanobrick.json

from nanobricks import Nanobrick
from pydantic import BaseModel

class UserInput(BaseModel):
    name: str
    email: str

class UserValidator(Nanobrick[dict, UserInput]):
    async def invoke(self, input: dict, *, deps=None) -> UserInput:
        return UserInput(**input)  # Validates and converts

# Validate with contract
from docs.agentic._contracts.nanobrick_contract import ContractValidator
is_valid, issues = ContractValidator.validate(UserValidator)
assert is_valid  # ✅
```

## Contributing

When adding new documentation:

1. Update llms.txt with new sections
2. Add contracts for new patterns
3. Create task definitions for common operations
4. Update memories with new concepts
5. Test all examples still work

## Standards Compliance

- **llms.txt**: https://llmstxt.org/
- **MCP**: https://modelcontextprotocol.io/
- **JSON-LD**: https://json-ld.org/
- **Schema.org**: https://schema.org/