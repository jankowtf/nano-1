# Simple Init Parallel - Nanobricks

Initialize three parallel git worktree directories for concurrent nanobricks development.

## Variables

FEATURE_NAME: $ARGUMENTS

## Execute these tasks

CREATE new directory `trees/`

> Execute these steps in parallel for concurrency
>
> Use absolute paths for all commands

CREATE first worktree:

- RUN `git worktree add -b FEATURE_NAME-1 ./trees/FEATURE_NAME-1`
- RUN `cd ./trees/FEATURE_NAME-1` then `uv sync`
- VERIFY Python environment with `cd ./trees/FEATURE_NAME-1 && uv run python -c "import nanobricks; print(nanobricks.__version__)"`

CREATE second worktree:

- RUN `git worktree add -b FEATURE_NAME-2 ./trees/FEATURE_NAME-2`
- RUN `cd ./trees/FEATURE_NAME-2` then `uv sync`
- VERIFY Python environment with `cd ./trees/FEATURE_NAME-2 && uv run python -c "import nanobricks; print(nanobricks.__version__)"`

CREATE third worktree:

- RUN `git worktree add -b FEATURE_NAME-3 ./trees/FEATURE_NAME-3`
- RUN `cd ./trees/FEATURE_NAME-3` then `uv sync`
- VERIFY Python environment with `cd ./trees/FEATURE_NAME-3 && uv run python -c "import nanobricks; print(nanobricks.__version__)"`

VERIFY setup:
- RUN `git worktree list` to show all worktrees
- RUN `ls -la trees/` to confirm directory structure
- REPORT: "Created 3 parallel worktrees for FEATURE_NAME, each with isolated Python environments"