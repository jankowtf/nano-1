# CLAUDE.md - Taskfiles

This file provides guidance to Claude Code when working with the Nanobricks task system.

## Overview

The Nanobricks task system uses go-task (Task) to orchestrate development, documentation, versioning, and release workflows. Tasks are organized into focused modules with clear namespacing and dependencies.

## Task System Architecture

### File Organization

- `Taskfile.build.yml` - Package building and distribution
- `Taskfile.dev.yml` - Development utilities and project linking
- `Taskfile.docs.yml` - Documentation management
- `Taskfile.version.yml` - Semantic versioning operations
- `Taskfile.workflows.yml` - High-level orchestration and Claude integration
- `Taskfile.agentic.yml` - AI-first documentation workflows
- `scripts/` - Helper scripts for Claude CLI discovery

### Naming Convention

Tasks follow a hierarchical namespace pattern: `namespace:component:action:variant`

Examples:

- `package:build` - Build distribution packages
- `dev:project:link` - Link a dependent project
- `version:bump:minor` - Bump minor version
- `workflow:release:create` - Complete release workflow

## Critical Task Guidelines

### Echo Statement Format

**IMPORTANT**: Echo statements in go-task CANNOT contain colons (`:`). Use dashes or other separators instead.

```yaml
# WRONG - This will fail
- echo "Step 1: Do something"

# CORRECT - Use dashes or other separators
- echo "Step 1 - Do something"
- echo "Step 1. Do something"
```

### Version Management

All version operations must use the task system, never manual edits:

1. Version in `pyproject.toml` is the single source of truth
2. After version bump, manually sync `src/nanobricks/__init__.py`
3. Clean git state required for version operations
4. Use `task version:release` for complete workflow

### Release Workflow

Standard release process:

```bash
# 1. Check current state
task version:current

# 2. Prepare release (analyze changes)
task workflow:release:prepare

# 3. Create release (includes version bump, changelog, commit, tag)
task workflow:release:create TYPE=patch|minor|major

# 4. If issues occur
task workflow:recovery:rollback    # Undo release
task workflow:recovery:hotfix      # Quick fixes
```

## Task Dependencies

### Critical Dependencies to Maintain

- `version:release` depends on clean git state
- `package:publish` requires `package:build`
- `deploy:production` requires `site:render`
- Release workflows must check CHANGELOG.md format

### Internal Task Pattern

Tasks prefixed with `_` or marked `internal: true` are helpers not meant for direct use.

## Claude CLI Integration

### Discovery Mechanism

The system uses `scripts/find-claude.sh` to locate Claude:

1. Checks `CLAUDE_CLI_PATH` environment variable
2. Searches PATH
3. Tries common installation locations
4. Provides manual fallback instructions

### Verbose Mode

Enable verbose Claude output:

```bash
CLAUDE_VERBOSE=1 task workflow:example:claude:hello
VERBOSE=1 task dev:claude:understand:dependent NAME=myproject
```

## Development Patterns

### Project Linking

For multi-project development:

```bash
# Link a dependent project
task dev:project:link PATH=/path/to/project

# List linked projects
task dev:project:list

# Unlink project
task dev:project:unlink NAME=project-name
```

### Continuous Development

```bash
# Watch and run tests
task dev:watch:test

# Live documentation preview
task docs:site:preview
```

### Agentic Documentation Management

The new `agentic:` namespace provides AI-first documentation workflows:

```bash
# Validate all agentic docs
task agentic:validate:all

# Check synchronization
task agentic:validate:sync

# Generate contexts from code
task agentic:generate:contexts

# Sync docs with code changes
task agentic:sync:all

# Version management
task agentic:version:check
task agentic:version:bump TYPE=patch

# Maintenance
task agentic:stats
task agentic:lint
task agentic:format
```

Key workflows:

- **Daily**: `task agentic:stats` → `task agentic:validate:sync`
- **After code changes**: `task agentic:sync:all` → `task agentic:validate:all`
- **Before release**: `task agentic:ci:validate` → `task agentic:version:bump`

## Common Issues and Solutions

### Claude Not Found

If Claude CLI isn't found:

1. Install: `npm install -g @anthropic-ai/claude-cli`
2. Set path: `export CLAUDE_CLI_PATH=/path/to/claude`
3. Or follow manual instructions provided by the task

### Version Sync

After `task version:bump:*`, always update `__version__` in the main module.

### Release Recovery

If release fails:

- `task workflow:recovery:rollback` - Full rollback
- `task workflow:recovery:fix-forgotten` - Add missed files
- `task workflow:recovery:hotfix` - Quick production fix

## Task Writing Guidelines

When creating or modifying tasks:

1. **Use clear descriptions** - Set the `desc` field for user-facing tasks
2. **Add emoji indicators** - 🔨 for builds, 📦 for packages, 🚀 for releases
3. **Provide next steps** - Echo helpful commands users can run next
4. **Check prerequisites** - Use `preconditions` for critical checks
5. **Handle errors gracefully** - Provide fallback instructions
6. **Keep output clean** - Use `silent: true` by default
7. **Document variables** - List required vars in task descriptions

## Variable Reference

### Common Variables

- `VERSION` - Current or target version
- `TYPE` - Release type (patch/minor/major)
- `PATH` - File or directory path
- `NAME` - Project or component name
- `MESSAGE` - Commit or description message
- `VERBOSE` / `CLAUDE_VERBOSE` - Enable verbose output

### Environment Variables

- `CLAUDE_CLI_PATH` - Override Claude executable location
- `NO_COLOR` - Disable colored output
- `TASK_FORCE` - Force operations despite warnings

## Testing Tasks

When testing task changes:

1. Use `--dry` flag to preview: `task --dry version:release`
2. Test in clean git state
3. Verify echo statements have no colons
4. Check variable interpolation
5. Test both success and failure paths

## Integration Points

### Main Taskfile

The root `Taskfile.yml` includes all module taskfiles and provides:

- Namespace organization
- Common variables
- Default task (`dev:all`)
- Cross-module task aliases

### GitHub Actions

Several tasks are designed for CI/CD:

- `dev:check:all` - Run in CI
- `package:build` - Create artifacts
- `deploy:production` - Deploy docs

### Developer Tools

Tasks integrate with:

- pytest, ruff, mypy - Quality checks
- uv - Python packaging
- Quarto - Documentation
- git - Version control
- Claude CLI - AI assistance

## Best Practices

1. **Atomic Tasks** - Each task does one thing well
2. **Idempotent** - Tasks can be run multiple times safely
3. **Descriptive Output** - Users understand what's happening
4. **Error Recovery** - Clear messages and next steps
5. **Cross-Platform** - Works on macOS, Linux, Windows (where applicable)
