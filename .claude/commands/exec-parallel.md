# Parallel Task Version Execution - Nanobricks

## Variables

FEATURE_NAME: $ARGUMENTS[0]
PLAN_FILE: $ARGUMENTS[1]
PARALLEL_COUNT: $ARGUMENTS[2]

## Pre-execution Setup

RUN `eza trees/ --tree --level=1 --git-ignore`
RUN `pwd`
RUN `test -f $PLAN_FILE && echo "✓ Plan file exists: $PLAN_FILE" || echo "⚠️  Plan file not found: $PLAN_FILE"`

## CRITICAL: Parallel Agent Creation

You must create $PARALLEL_COUNT separate agents to work simultaneously. Use this EXACT language:

"I will now create $PARALLEL_COUNT independent agents to work in parallel on implementing $FEATURE_NAME. Each agent will work in their own worktree directory and implement the plan independently.

Agent 1: Please work in `trees/$FEATURE_NAME-1/` directory. First run `cd trees/$FEATURE_NAME-1/ && pwd` to confirm your location, then implement the plan from $PLAN_FILE. Create RESULTS.md when complete.

Agent 2: Please work in `trees/$FEATURE_NAME-2/` directory. First run `cd trees/$FEATURE_NAME-2/ && pwd` to confirm your location, then implement the plan from $PLAN_FILE. Create RESULTS.md when complete.

Agent 3: Please work in `trees/$FEATURE_NAME-3/` directory. First run `cd trees/$FEATURE_NAME-3/ && pwd` to confirm your location, then implement the plan from $PLAN_FILE. Create RESULTS.md when complete.

All agents should begin working now in parallel."

## Instructions for Each Agent

Each agent will independently implement the engineering plan detailed in $PLAN_FILE in their respective workspace (trees/$FEATURE_NAME-<number>/).

When the subagent completes its work, have the subagent report their final changes made in a comprehensive `RESULTS.md` file at the root of their respective workspace.

Important for nanobricks development:

- Ensure all tests pass with `uv run pytest` before completing
- Run `uv run mypy src/nanobricks` to check type safety
- Document any new nanobrick patterns or skills created
- Include example usage in the RESULTS.md file
