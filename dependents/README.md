# Dependents Directory

This directory contains symbolic links to projects that depend on Nanobricks. These links are created using absolute paths to ensure consistent file referencing across different tools and environments, including Claude Code.

## Why Absolute Paths?

We use absolute paths for symbolic links to:
- Ensure consistent behavior across different working directories
- Improve compatibility with tools like Claude Code that may have issues with relative symlinks
- Make debugging easier by showing exact paths
- Prevent broken links when the project is moved

## Managing Links

### Create a link
```bash
task dev:project:link PATH=/absolute/path/to/project
# or with relative path (will be converted to absolute)
task dev:project:link PATH=../my-project
```

### List all links
```bash
task dev:project:list
```

### Remove a link
```bash
task dev:project:unlink NAME=project-name
```

## Note for Claude Code Users

The symlinks in this directory use absolute paths to ensure proper file navigation and referencing within Claude Code. This prevents issues that can occur when Claude Code tries to resolve relative symbolic links.