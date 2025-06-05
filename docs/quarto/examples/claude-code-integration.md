# Claude Code Integration for Nanobricks

This guide explains how to use Claude Code to analyze and understand both your Nanobricks framework and dependent projects.

## Overview

We've created go-task commands that leverage Claude Code's headless mode (`-p` flag) to programmatically analyze codebases. This allows you to quickly get Claude to understand project structures, dependencies, and usage patterns.

## Available Tasks

### 1. From Nanobricks: Understanding Dependent Projects

When you're in the Nanobricks directory and want Claude to understand how a dependent project uses your framework:

```bash
# Analyze a specific dependent project
task dev:claude:understand:dependent NAME=nano-scorm

# Claude will analyze:
# - Overall project structure and purpose
# - How it uses the Nanobricks framework
# - Key components and their interactions
# - Patterns and best practices used
```

### 2. From a Dependent: Understanding Nanobricks

When you're in a dependent project and want Claude to understand the upstream Nanobricks framework:

```bash
# From within a dependent project directory
task claude:understand:nanobricks

# If Nanobricks is in a non-standard location
task claude:understand:nanobricks NANOBRICKS_PATH=/path/to/nanobricks
```

### 3. Comparing Usage Patterns

Compare how multiple dependent projects use Nanobricks:

```bash
# Compare usage patterns across projects
task dev:claude:compare:usage PROJECTS="nano-scorm,project2,project3"
```

## How It Works

These tasks use Claude Code's headless mode with the `-p` flag to send specific prompts:

```bash
claude -p "Please analyze and understand this codebase..."
```

Claude Code will:

1. Explore the specified directory
2. Read relevant files
3. Understand the project structure
4. Provide a comprehensive analysis

## Prerequisites

1. **Claude Code must be installed**:

   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **You must be authenticated** with Claude Code:
   ```bash
   claude login
   ```

## Use Cases

### For Framework Developers

- Understand how dependents use your framework
- Identify common patterns and anti-patterns
- Find opportunities for improvement
- Generate documentation based on real usage

### For Dependent Project Developers

- Quickly onboard to the Nanobricks framework
- Understand available components and patterns
- Learn best practices from the framework
- Find similar implementations in other dependents

## Advanced Usage

### Custom Prompts

You can create your own Claude Code tasks with custom prompts:

```yaml
# In your Taskfile.yml
claude:analyze:custom:
  desc: Custom Claude Code analysis
  cmds:
    - |
      claude -p "Your custom prompt here. Analyze the codebase focusing on: {{.FOCUS}}"
```

### Combining with Other Tools

Claude Code tasks can be combined with other development workflows:

```bash
# First understand the codebase, then run tests
task dev:claude:understand:dependent NAME=nano-scorm && \
cd dependents/nano-scorm && \
task dev:test
```

## Tips

1. **Be Specific**: The more specific your prompts, the better Claude's analysis
2. **Use Context**: Claude Code automatically reads your project context
3. **Iterate**: You can refine your understanding by asking follow-up questions
4. **Save Results**: Consider piping output to files for future reference:
   ```bash
   task dev:claude:understand:dependent NAME=nano-scorm > analysis/nano-scorm.md
   ```

## Troubleshooting

### Claude Code Not Found

If you get a "command not found" error:

```bash
# Install Claude Code globally
npm install -g @anthropic-ai/claude-code

# Or use npx
npx @anthropic-ai/claude-code -p "..."
```

### Authentication Issues

If Claude Code isn't authenticated:

```bash
# Login to Claude Code
claude login
```

### Directory Not Found

Make sure dependent projects are properly linked:

```bash
# List linked dependents
task dev:project:list

# Link a new dependent
task dev:project:link PATH=/path/to/project
```
