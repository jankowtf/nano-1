#!/bin/bash
# Build Nanobricks for distribution

echo "🏗️  Building Nanobricks for distribution..."

# Ensure we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Ensure build tools are installed
echo "Ensuring build tools are installed..."
pip install --upgrade pip build wheel

# Build the package
echo "Building wheel and source distribution..."
python -m build

# Show results
echo ""
echo "✅ Build complete! Packages created:"
ls -la dist/

# Create a local repository structure
LOCAL_REPO="$HOME/.nanobricks-repo"
echo ""
echo "Setting up local repository at $LOCAL_REPO..."
mkdir -p "$LOCAL_REPO"
cp dist/* "$LOCAL_REPO/"

echo ""
echo "📦 Distribution packages ready!"
echo ""
echo "To use in other projects, you can:"
echo ""
echo "1. Install directly from wheel:"
echo "   pip install $SCRIPT_DIR/dist/nanobricks-0.1.0-py3-none-any.whl"
echo ""
echo "2. Install from local repository:"
echo "   pip install nanobricks --find-links file://$LOCAL_REPO"
echo ""
echo "3. Use in pyproject.toml:"
echo "   dependencies = ["
echo "       \"nanobricks @ file://$SCRIPT_DIR\","
echo "   ]"
echo ""
echo "4. For development (editable install):"
echo "   pip install -e $SCRIPT_DIR"