# Taskfiles Directory

This directory contains all Task (go-task) configuration files for the Nanobricks project, organized for maintainability and clarity.

## Structure

```
taskfiles/
├── scripts/              # Common scripts used by tasks
│   ├── find-claude.sh   # Locate Claude CLI executable
│   └── run-claude.sh    # Run Claude with error handling
├── Taskfile.build.yml   # Build and distribution tasks
├── Taskfile.dev.yml     # Development utilities
├── Taskfile.docs.yml    # Documentation tasks
├── Taskfile.version.yml # Version management tasks
└── Taskfile.workflows.yml # High-level workflow orchestration
```

## Taskfile Organization

Each taskfile focuses on a specific domain:

- **Taskfile.build.yml**: Package building, project creation, publishing
- **Taskfile.dev.yml**: Development utilities, project linking, Claude integration
- **Taskfile.docs.yml**: Documentation generation and publishing
- **Taskfile.version.yml**: Semantic versioning and release management
- **Taskfile.workflows.yml**: Complex workflows that orchestrate other tasks

## Common Scripts

The `scripts/` subdirectory contains reusable shell scripts:

### find-claude.sh

Discovers the Claude CLI executable by checking:

1. `$CLAUDE_PATH` environment variable
2. Common installation paths
3. System PATH
4. Login shell environments

### run-claude.sh

Wrapper for running Claude CLI with proper error handling and helpful messages when Claude is not found.

## Adding New Scripts

When adding new common scripts:

1. Place them in `taskfiles/scripts/`
2. Make them executable: `chmod +x taskfiles/scripts/your-script.sh`
3. Use them in taskfiles with: `{{.ROOT_DIR}}/taskfiles/scripts/your-script.sh`

## Conventions

1. **DRY Principle**: Extract common logic into scripts
2. **Error Handling**: Scripts should provide helpful error messages
3. **Documentation**: Each script should have a header comment explaining its purpose
4. **Naming**: Use descriptive names with hyphens (e.g., `check-prereqs.sh`)
5. **Variables**: Access Task variables via `{{.VAR_NAME}}` in taskfiles

## Claude Integration Features

### Verbose Mode

When running Claude-integrated tasks, you can enable verbose mode to see Claude's detailed thinking process, tool executions, and progress:

```bash
# Method 1: Set environment variable
export CLAUDE_VERBOSE=1
task workflow:example:claude:hello

# Method 2: Use inline variable
CLAUDE_VERBOSE=1 task dev:claude:understand:dependent NAME=nano-scorm

# Method 3: Set VERBOSE (also works)
VERBOSE=1 task workflow:release:prepare
```

When verbose mode is enabled:

- You'll see Claude's internal operations
- Tool executions are displayed in real-time
- Progress indicators show what Claude is doing
- Error messages include full context
- Timing information helps identify bottlenecks

### Team Setup

The Claude integration is designed to work across different team environments:

1. **Environment Variable** (Recommended):

   ```bash
   export CLAUDE_PATH="/path/to/your/claude"
   ```

2. **Common Locations** (Automatically checked):

   - `$HOME/.claude/local/claude`
   - `/usr/local/bin/claude`
   - `/opt/homebrew/bin/claude`

3. **Symlink** (For custom installations):
   ```bash
   ln -s /your/actual/claude/path /usr/local/bin/claude
   ```

Run `task workflow:claude:setup` to check your configuration.

## Task Organization

Tasks follow the `namespace:component:action:variant` pattern:

- **build:** - Package building and distribution
- **dev:** - Development utilities and dependent project management
- **docs:** - Documentation generation and management
- **version:** - Semantic versioning and release management
- **workflow:** - High-level workflows combining multiple tasks

## Key Features

### Smart Claude Discovery

The `find-claude.sh` script automatically locates Claude CLI using multiple methods:

- Environment variables
- Common installation paths
- PATH search
- Login shell detection

### Progress Indicators

When not in verbose mode, tasks show helpful progress messages:

- "🤖 Claude is thinking..."
- "💡 Tip: Set CLAUDE_VERBOSE=1 to see detailed progress"

### Error Handling

If Claude CLI is not found, you'll get:

- Clear error messages
- Setup instructions
- Multiple configuration options
- Team-friendly solutions

## Usage Examples

### Basic Usage

```bash
# Test Claude integration
task workflow:example:claude:hello

# Analyze a dependent project
task dev:claude:understand:dependent NAME=nano-scorm

# Prepare a release with Claude's help
task workflow:release:prepare
```

### With Verbose Mode

```bash
# See detailed Claude processing
CLAUDE_VERBOSE=1 task workflow:example:claude:hello

# Debug release workflow issues
CLAUDE_VERBOSE=1 task workflow:release:create TYPE=patch

# Analyze with full visibility
CLAUDE_VERBOSE=1 task dev:claude:compare:usage PROJECTS="project1,project2"
```

### Manual Prompts

When Claude CLI isn't available, generate prompts:

```bash
# Generate prompt for manual execution
task workflow:claude:prompt:dependent NAME=nano-scorm

# Copy the output and run manually with:
claude --verbose -p "..."
```
