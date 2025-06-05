#!/bin/bash
# Check for required tools and prerequisites

set -e

echo "🔍 Checking prerequisites..."

# Array of required tools
REQUIRED_TOOLS=(
    "python3:Python 3.13+"
    "uv:UV package manager"
    "git:Git version control"
    "task:Task (go-task) runner"
)

# Optional but recommended tools
OPTIONAL_TOOLS=(
    "ruff:Python linter and formatter"
    "mypy:Python type checker"
    "pytest:Python testing framework"
    "quarto:Documentation system"
    "watchexec:File watcher for development"
)

# Check required tools
MISSING_REQUIRED=()
for tool_spec in "${REQUIRED_TOOLS[@]}"; do
    tool=$(echo "$tool_spec" | cut -d: -f1)
    desc=$(echo "$tool_spec" | cut -d: -f2)
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✅ $desc found: $(command -v $tool)"
    else
        echo "❌ $desc not found"
        MISSING_REQUIRED+=("$desc")
    fi
done

# Check optional tools
echo ""
echo "📦 Optional tools:"
MISSING_OPTIONAL=()
for tool_spec in "${OPTIONAL_TOOLS[@]}"; do
    tool=$(echo "$tool_spec" | cut -d: -f1)
    desc=$(echo "$tool_spec" | cut -d: -f2)
    
    if command -v "$tool" >/dev/null 2>&1; then
        echo "✅ $desc found"
    else
        echo "⚠️  $desc not found (optional)"
        MISSING_OPTIONAL+=("$desc")
    fi
done

# Python version check
echo ""
echo "🐍 Python version check:"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 13) else 1)' 2>/dev/null; then
        echo "✅ Python $PYTHON_VERSION (meets requirement >= 3.13)"
    else
        echo "⚠️  Python $PYTHON_VERSION (requires >= 3.13)"
        echo "   Consider using uv to manage Python versions"
    fi
fi

# Summary
echo ""
if [ ${#MISSING_REQUIRED[@]} -eq 0 ]; then
    echo "✅ All required prerequisites are installed!"
else
    echo "❌ Missing required tools:"
    for tool in "${MISSING_REQUIRED[@]}"; do
        echo "   - $tool"
    done
    echo ""
    echo "Installation suggestions:"
    echo "  - UV: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  - Task: https://taskfile.dev/installation/"
    exit 1
fi

if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
    echo ""
    echo "💡 Consider installing optional tools for full functionality:"
    for tool in "${MISSING_OPTIONAL[@]}"; do
        echo "   - $tool"
    done
fi