#!/bin/bash
# Quick setup script

echo "Setting up development environment..."

# Create virtual environment
python3.13 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install package and dev dependencies
pip install -e .
pip install -e ".[dev]"

echo "✅ Setup complete!"
echo "Run 'source .venv/bin/activate' to activate the environment"
