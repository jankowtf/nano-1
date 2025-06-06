# Agentic Documentation Quick Reference

## For AI Agents

```bash
# Start here
cat docs/agentic/llms.txt

# Find a task
ls docs/agentic/tasks/

# Check troubleshooting
cat docs/agentic/memories/troubleshooting.jsonld
```

## For Humans

### Understanding the System
- Read `/docs/quarto/agentic-docs-guide.qmd` - Overview
- Read `/docs/quarto/agentic-docs-walkthrough.qmd` - Practical examples  
- Read `/docs/quarto/agentic-docs-formats.qmd` - Format rationale

### Key Commands

```bash
# Validate everything
task agentic:validate:all

# Check version compatibility
task agentic:version:check

# Sync docs with code
task agentic:sync:all

# Inject AI contexts into Quarto
task agentic:inject:contexts

# Show statistics
task agentic:stats
```

### File Types

| Extension | Purpose | Example |
|-----------|---------|---------|
| `.yaml` | Human-editable configs | `_contexts/nanobrick.context.yaml` |
| `.json` | Data exchange | `tasks/create-nanobrick.json` |
| `.jsonld` | Knowledge graphs | `memories/concepts.jsonld` |
| `.py` | Executable specs | `_contracts/nanobrick.contract.py` |

### Version Management

```bash
# Check current version
task agentic:version:check

# Bump version (patch/minor/major)
task agentic:version:bump TYPE=minor

# Check compatibility
task agentic:validate:versions
```

### CI Integration

```bash
# Run in CI pipeline
task agentic:ci:validate

# Generate report
task agentic:ci:generate-report
```

## Quick Wins

1. **For better AI understanding**: Add `ai-context: filename.context.yaml` to any `.qmd` file
2. **For validation**: Run contracts as Python scripts
3. **For troubleshooting**: Search `memories/troubleshooting.jsonld` by error pattern
4. **For examples**: Copy from `tasks/*.json` step-by-step guides

## Architecture at a Glance

```
docs/
├── agentic/          # AI-first docs
│   ├── llms.txt      # Entry point
│   ├── version.yaml  # Independent versioning
│   └── ...
├── quarto/           # Human-first docs
└── _bridge/          # Integration tools
```

The system is **polyglot by design** - each format optimized for its purpose!