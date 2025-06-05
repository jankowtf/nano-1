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

### For Team Leaders

If you're setting up Claude for your team, consider:

1. Creating a standard installation guide
2. Setting up shared environment variable conventions
3. Documenting which method your team should use
4. Including Claude setup in your onboarding process

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

## Common Patterns

### Understanding Multiple Dependents

When you need to understand how different projects use Nanobricks:

```bash
task dev:claude:compare:usage PROJECTS="project1,project2,project3"
```

This helps identify:

- Common usage patterns
- Different implementation approaches
- Opportunities for new Nanobricks features
- Best practices that emerge from real usage

## Verbose Mode and Progress Indicators

### Understanding Verbose Mode

Claude CLI supports a `--verbose` flag that provides detailed diagnostic output. This is incredibly useful for:

1. **Debugging** - See exactly what Claude is doing
2. **Learning** - Understand Claude's thinking process
3. **Performance** - Identify slow operations
4. **Troubleshooting** - Get detailed error context

### Enabling Verbose Mode

There are several ways to enable verbose mode:

#### Method 1: Environment Variable

```bash
export CLAUDE_VERBOSE=1
task workflow:example:claude:hello
```

#### Method 2: Inline Variable

```bash
CLAUDE_VERBOSE=1 task dev:claude:understand:dependent NAME=nano-scorm
```

#### Method 3: Direct Claude Command

```bash
claude --verbose -p "Your prompt here"
```

### What Verbose Mode Shows

When enabled, verbose mode displays:

- **Function Calls**: Every tool Claude uses with parameters
- **Variable Values**: The state of data during execution
- **File Operations**: Reading, writing, and permissions checks
- **Network Activity**: API communications (without sensitive data)
- **Timing Information**: How long each operation takes
- **Error Context**: Full stack traces and debugging information

### Progress Indicators

When verbose mode is **not** enabled, our tasks show friendly progress indicators:

```
🤖 Claude is thinking...
💡 Tip: Set CLAUDE_VERBOSE=1 to see detailed progress
```

This provides a better user experience by:

- Confirming that Claude is working
- Suggesting how to get more information
- Keeping the output clean by default

### Best Practices

1. **Default Usage**: Keep verbose mode off for normal operations
2. **Debugging**: Enable verbose mode when something goes wrong
3. **Learning**: Use verbose mode when learning how Claude works
4. **Performance**: Enable to identify slow operations
5. **Team Settings**: Document when team members should use verbose mode

### Example Output Comparison

#### Without Verbose Mode:

```bash
$ task workflow:example:claude:hello
🤖 Claude is thinking...
💡 Tip: Set CLAUDE_VERBOSE=1 to see detailed progress

Hello! Here's the current status of your repository:
...
```

#### With Verbose Mode:

```bash
$ CLAUDE_VERBOSE=1 task workflow:example:claude:hello
🔍 Running Claude in verbose mode...

[DEBUG] Building context...
[INFO] Executing tool: git_status
[DEBUG] Tool parameters: {}
[INFO] Tool result: On branch main...
[DEBUG] Processing response...
...
```

## Team Setup Guide

Since Claude CLI installations vary across team members, we've made the integration flexible. Here's how to set it up:

### Quick Setup

Run the setup helper to check your configuration:

```bash
task workflow:claude:setup
```

### Configuration Options

#### Option 1: Environment Variable (Recommended)

Add to your shell config (`~/.zshrc` or `~/.bashrc`):

```bash
# If you have claude as an alias, find the real path first:
# alias | grep claude

export CLAUDE_PATH="/path/to/your/claude"
```

#### Option 2: Standard Locations

The tasks automatically check these locations:

- `$HOME/.claude/local/claude`
- `/usr/local/bin/claude`
- `/opt/homebrew/bin/claude`
- Anywhere in your PATH

#### Option 3: Symlink

If claude is installed in a non-standard location:

```bash
sudo ln -s /your/actual/claude/path /usr/local/bin/claude
```

### Testing Your Setup

After configuration:

```bash
source ~/.zshrc  # or restart your terminal
task workflow:example:claude:hello
```

### Fallback: Manual Prompts

If Claude CLI isn't available, you can generate prompts to copy/paste:

```bash
# Generate a prompt to analyze a dependent
task workflow:claude:prompt:dependent NAME=my-project

# Generate a prompt to understand Nanobricks
task workflow:claude:prompt:nanobricks
```

## Implementation Details

```bash
claude -p "Please analyze and understand this codebase..."
```

Claude Code will:

1. Explore the specified directory
2. Read relevant files
3. Understand the project structure
4. Provide a comprehensive analysis
