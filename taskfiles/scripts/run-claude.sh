#!/bin/bash
# Run Claude CLI with proper error handling
# Usage: run-claude.sh "prompt" [additional_flags]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_CMD=$("$SCRIPT_DIR/find-claude.sh")

if [ -z "$CLAUDE_CMD" ]; then
    echo "❌ Claude CLI not found"
    echo ""
    echo "To use Claude integration, you need to set up Claude CLI:"
    echo ""
    echo "Option 1: Set CLAUDE_PATH environment variable"
    echo "  export CLAUDE_PATH=/path/to/your/claude"
    echo "  Add this to your ~/.zshrc or ~/.bashrc"
    echo ""
    echo "Option 2: Ensure claude is in one of these locations:"
    echo "  - \$HOME/.claude/local/claude"
    echo "  - /usr/local/bin/claude"
    echo "  - /opt/homebrew/bin/claude"
    echo "  - Anywhere in your PATH"
    echo ""
    echo "Option 3: Create a symlink:"
    echo "  ln -s /your/actual/claude/path /usr/local/bin/claude"
    echo ""
    echo "For setup help, run: task workflow:claude:setup"
    exit 1
fi

# Get the prompt (first argument)
PROMPT="$1"
shift  # Remove the first argument to pass remaining ones to claude

# Check if verbose mode is enabled via environment variable
CLAUDE_FLAGS=""
if [ -n "$CLAUDE_VERBOSE" ] || [ -n "$VERBOSE" ]; then
    CLAUDE_FLAGS="--verbose"
    echo "🔍 Running Claude in verbose mode..."
    echo ""
fi

# Show progress indicator if not in verbose mode
if [ -z "$CLAUDE_FLAGS" ]; then
    echo "🤖 Claude is thinking..."
    echo "💡 Tip: Set CLAUDE_VERBOSE=1 to see detailed progress"
    echo ""
fi

# Run claude with the prompt and any additional flags
"$CLAUDE_CMD" $CLAUDE_FLAGS -p "$PROMPT" "$@"