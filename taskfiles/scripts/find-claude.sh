#!/bin/bash
# Find Claude CLI executable
# This script tries multiple methods to locate the claude command

# 1. Check if CLAUDE_PATH env var is set (team members can set this)
if [ -n "$CLAUDE_PATH" ]; then
    if [ -x "$CLAUDE_PATH" ]; then
        echo "$CLAUDE_PATH"
        exit 0
    fi
fi

# 2. Check common installation paths
COMMON_PATHS=(
    "$HOME/.claude/local/claude"
    "/usr/local/bin/claude"
    "/opt/homebrew/bin/claude"
    "/Applications/Cursor.app/Contents/Resources/app/bin/claude"
)

for path in "${COMMON_PATHS[@]}"; do
    if [ -x "$path" ]; then
        echo "$path"
        exit 0
    fi
done

# 3. Try to find via PATH in interactive shell
if command -v claude >/dev/null 2>&1; then
    command -v claude
    exit 0
fi

# 4. Try using which in login shell
CLAUDE_PATH=$(/bin/zsh -l -c 'which claude 2>/dev/null')
if [ -n "$CLAUDE_PATH" ] && [ -x "$CLAUDE_PATH" ]; then
    echo "$CLAUDE_PATH"
    exit 0
fi

# 5. Try bash login shell as fallback
CLAUDE_PATH=$(/bin/bash -l -c 'which claude 2>/dev/null')
if [ -n "$CLAUDE_PATH" ] && [ -x "$CLAUDE_PATH" ]; then
    echo "$CLAUDE_PATH"
    exit 0
fi

# Not found
exit 1