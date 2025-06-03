#!/usr/bin/env python3
"""
Migration script to convert from | pipe operator to >> pipe operator.

This script updates all Python files to use the new >> operator instead of |
for nanobrick composition.
"""

import re
import sys
from pathlib import Path


def find_python_files(root_dir: Path, exclude_dirs: list[str] = None) -> list[Path]:
    """Find all Python files in the given directory tree."""
    if exclude_dirs is None:
        exclude_dirs = [
            '.git', '__pycache__', '.venv', 'venv', 'env', '.tox', 
            'dist', 'build', 'htmlcov', 'activate', '.history', 
            'node_modules', '.pytest_cache', '.mypy_cache'
        ]
    
    python_files = []
    for path in root_dir.rglob('*.py'):
        # Skip if in excluded directory
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        python_files.append(path)
    
    return python_files


def migrate_file(file_path: Path, dry_run: bool = False) -> tuple[bool, list[str]]:
    """
    Migrate a single file from | to >> operator.
    
    Returns:
        (changed, changes): Whether file was changed and list of changes made
    """
    with open(file_path, encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: Change __or__ method definitions to __rshift__
    if 'def __or__' in content:
        content = re.sub(
            r'def __or__\(',
            'def __rshift__(',
            content
        )
        changes.append("Changed __or__ method to __rshift__")
    
    # Pattern 2: Change pipe operator usage in expressions
    # This pattern matches: ) >> Word( or ) >> word( patterns
    pipe_pattern = r'(\))\s*\|\s*(\w+\()'
    if re.search(pipe_pattern, content):
        content = re.sub(pipe_pattern, r'\1 >> \2', content)
        changes.append("Changed pipe operator | to >>")
    
    # Pattern 3: Change pipe operator in composition patterns
    # We need to be careful not to match bitwise OR operations
    # Look for patterns that are likely nanobrick compositions
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Skip lines that look like bitwise operations
        if any(keyword in line for keyword in ['if ', 'while ', 'assert ', '==', '!=', '&', '^']):
            new_lines.append(line)
            continue
            
        # Check if this line has a pipe that looks like composition
        if ' | ' in line and 'Nanobrick' in content:
            # Check if it's likely a composition (has parentheses suggesting function calls)
            if '()' in line or re.search(r'\w+\([^)]*\)\s*\|\s*\w+', line):
                new_line = line.replace(' | ', ' >> ')
                if new_line != line:
                    new_lines.append(new_line)
                    if "Changed composition operators" not in changes:
                        changes.append("Changed composition operators")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Pattern 4: Update docstrings mentioning pipe operator
    if 'pipe operator' in content and '|' in content:
        content = re.sub(
            r'using the pipe operator\.',
            'using the >> pipe operator.',
            content
        )
        content = re.sub(
            r'with the pipe operator\.',
            'with the >> pipe operator.',
            content
        )
        if "Updated docstrings" not in changes:
            changes.append("Updated docstrings")
    
    # Check if file was actually changed
    changed = content != original_content
    
    if changed and not dry_run:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return changed, changes


def main():
    """Main migration function."""
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv
    
    # Get the project root
    project_root = Path(__file__).parent
    
    print("Migrating pipe operators from | to >> in", project_root)
    if dry_run:
        print("DRY RUN - No files will be modified")
    print()
    
    # Find all Python files
    python_files = find_python_files(project_root)
    print(f"Found {len(python_files)} Python files")
    
    # Migrate each file
    total_changed = 0
    file_changes = []
    
    for file_path in python_files:
        changed, changes = migrate_file(file_path, dry_run)
        if changed:
            total_changed += 1
            rel_path = file_path.relative_to(project_root)
            file_changes.append((rel_path, changes))
    
    # Report results
    print(f"\nMigration {'would modify' if dry_run else 'modified'} {total_changed} files:")
    for rel_path, changes in file_changes:
        print(f"\n  {rel_path}:")
        for change in changes:
            print(f"    - {change}")
    
    if not dry_run:
        print(f"\nMigration complete! {total_changed} files updated.")
        print("\nNext steps:")
        print("1. Review the changes with: git diff")
        print("2. Run tests to ensure everything works: task dev:test")
        print("3. Update any documentation that references the | operator")
    else:
        print(f"\nDry run complete. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()