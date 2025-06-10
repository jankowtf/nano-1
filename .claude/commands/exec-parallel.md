# Parallel Task Version Execution - Nanobricks

## Variables

PLAN_TO_EXECUTE: $ARGUMENTS
NUMBER_OF_PARALLEL_WORKTREES: $ARGUMENTS

## Run these commands top to bottom

RUN `eza -la --git`
RUN `eza src/nanobricks --tree --level=2 --git-ignore`
RUN `eza trees --tree --level=3 --git-ignore`
READ: PLAN_TO_EXECUTE

## Instructions

We're going to create NUMBER_OF_PARALLEL_WORKTREES new subagents that use the Task tool to create N versions of the same feature in parallel.

This enables us to concurrently build the same feature in parallel so we can test and validate each subagent's changes in isolation then pick the best changes.

The first agent will run in trees/<predefined_feature_name>-1/
The second agent will run in trees/<predefined_feature_name>-2/
...
The last agent will run in trees/<predefined_feature_name>-<NUMBER_OF_PARALLEL_WORKTREES>/

The code in trees/<predefined_feature_name>-<i>/ will be identical to the code in the current branch. It will be setup and ready for you to build the feature end to end.

Each agent will independently implement the engineering plan detailed in PLAN_TO_EXECUTE in their respective workspace.

When the subagent completes its work, have the subagent report their final changes made in a comprehensive `RESULTS.md` file at the root of their respective workspace.

Important for nanobricks development:

- Ensure all tests pass with `uv run pytest` before completing
- Run `uv run mypy src/nanobricks` to check type safety
- Document any new nanobrick patterns or skills created
- Include example usage in the RESULTS.md file
