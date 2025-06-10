# Product Requirements Document: Parallel Development System - Unified Plan

## Executive Summary

**TL;DR**: Implement a robust parallel development system using git worktrees and Claude Code's Task tool to enable multiple implementation approaches concurrently. Fix the issues that prevented true parallel execution in the atomic commits test case.

## Current State

### What Exists
1. **Basic exec-parallel command** (`.claude/commands/exec-parallel.md`) - Needs enhancement
2. **Atomic commits implementation** - Completed in both root and worktree (test case for parallel system)
3. **Lessons learned** - Clear understanding of what went wrong

### What's Missing
1. **Taskfile.parallel.yml** - Not implemented
2. **Enhanced exec-parallel command** - Not created
3. **Proper parallel execution** - Claude needs explicit instructions

## The Core Problem

When attempting parallel development of atomic commits:
- Claude executed tasks **sequentially** instead of in parallel
- Work happened in the **root directory** instead of worktrees
- No true **subagents** were created
- The Task tool maintains its current context

## The Solution

### 1. Enhanced Parallel Execution Command

**File**: `.claude/commands/exec-parallel-v2.md`

```markdown
# Parallel Worktree Execution v2

## Variables
FEATURE: $ARGUMENTS[0]
PLAN_FILE: $ARGUMENTS[1] 
COUNT: $ARGUMENTS[2]

## Setup Verification
1. Check worktrees exist: `eza trees/ --tree --level=1`
2. Verify plan file: `test -f $PLAN_FILE && echo "✓ Plan file exists"`
3. Show current location: `pwd`

## CRITICAL: Parallel Agent Creation

You must create $COUNT separate agents to work simultaneously using the Task tool.

### Agent Creation Instructions

Use this EXACT language to create parallel agents:

"I will now create $COUNT independent agents to work in parallel on implementing $FEATURE. Each agent will work in their own worktree directory and implement the plan independently.

Agent 1: Please work in `trees/$FEATURE-1/` directory. First run `cd trees/$FEATURE-1/ && pwd` to confirm your location, then implement the plan from $PLAN_FILE. Create RESULTS.md when complete.

Agent 2: Please work in `trees/$FEATURE-2/` directory. First run `cd trees/$FEATURE-2/ && pwd` to confirm your location, then implement the plan from $PLAN_FILE. Create RESULTS.md when complete.

Agent 3: Please work in `trees/$FEATURE-3/` directory. First run `cd trees/$FEATURE-3/ && pwd` to confirm your location, then implement the plan from $PLAN_FILE. Create RESULTS.md when complete.

All agents should begin working now in parallel."

## Post-Execution
After all agents complete:
1. Compare results: `task parallel:compare FEATURE=$FEATURE`
2. Generate report: `task parallel:collect:results FEATURE=$FEATURE`
```

### 2. Parallel Development Taskfile

**File**: `taskfiles/Taskfile.parallel.yml`

```yaml
version: '3'

tasks:
  setup:
    desc: Setup parallel worktrees for a feature
    vars:
      FEATURE: '{{.FEATURE}}'
      COUNT: '{{.COUNT | default "3"}}'
      BASE: '{{.BASE | default "main"}}'
    cmds:
      - mkdir -p trees
      - |
        for i in $(seq 1 {{.COUNT}}); do
          if [ ! -d "trees/{{.FEATURE}}-$i" ]; then
            echo "Creating worktree {{.FEATURE}}-$i..."
            git worktree add "trees/{{.FEATURE}}-$i" -b "parallel/{{.FEATURE}}-$i" {{.BASE}}
          fi
        done
      - task: verify FEATURE={{.FEATURE}}

  verify:
    desc: Verify worktree setup
    cmds:
      - echo "=== Git Worktrees ==="
      - git worktree list
      - echo -e "\n=== Tree Structure ==="
      - eza trees/ --tree --level=2 --git-ignore

  compare:
    desc: Compare implementations across worktrees
    vars:
      FEATURE: '{{.FEATURE}}'
    cmds:
      - |
        echo "# Implementation Comparison: {{.FEATURE}}"
        echo "Generated: $(date)"
        echo ""
        for dir in trees/{{.FEATURE}}-*; do
          if [ -f "$dir/RESULTS.md" ]; then
            echo "## $(basename $dir)"
            echo '```'
            head -30 "$dir/RESULTS.md"
            echo '```'
            echo ""
          fi
        done

  collect:results:
    desc: Aggregate all RESULTS.md files
    vars:
      FEATURE: '{{.FEATURE}}'
      OUTPUT: '{{.OUTPUT | default "prds/{{.FEATURE}}-comparison.md"}}'
    cmds:
      - |
        {
          echo "# Parallel Implementation Results: {{.FEATURE}}"
          echo "Generated: $(date)"
          echo ""
          
          for dir in trees/{{.FEATURE}}-*; do
            if [ -f "$dir/RESULTS.md" ]; then
              echo "## $(basename $dir)"
              cat "$dir/RESULTS.md"
              echo -e "\n---\n"
            fi
          done
        } > {{.OUTPUT}}
      - echo "Results collected in {{.OUTPUT}}"

  integrate:
    desc: Guide for integrating best implementation
    vars:
      FEATURE: '{{.FEATURE}}'
    cmds:
      - echo "Integration Guide for {{.FEATURE}}:"
      - echo "1. Review comparison: task parallel:compare FEATURE={{.FEATURE}}"
      - echo "2. Choose best approach or combine multiple"
      - echo "3. Cherry-pick commits: git cherry-pick <hash>"
      - echo "4. Or copy files: cp trees/{{.FEATURE}}-N/path/to/file ."

  cleanup:
    desc: Remove worktrees after integration
    vars:
      FEATURE: '{{.FEATURE}}'
    preconditions:
      - sh: '[ -n "{{.FEATURE}}" ]'
        msg: "FEATURE is required"
    cmds:
      - |
        echo "This will remove all {{.FEATURE}} worktrees. Continue? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
          for dir in trees/{{.FEATURE}}-*; do
            if [ -d "$dir" ]; then
              echo "Removing $dir..."
              git worktree remove "$dir" --force
            fi
          done
        fi
```

### 3. Best Practices Guide

**File**: `docs/quarto/advanced-topics/parallel-development.qmd`

```markdown
---
title: "Parallel Development with Git Worktrees"
description: "Using git worktrees and Claude Code for parallel implementation exploration"
---

## Quick Start

```bash
# 1. Setup worktrees
task parallel:setup FEATURE=new-skill COUNT=3

# 2. Create implementation plan
echo "Implement a new caching skill for nanobricks" > prds/caching-skill-plan.md

# 3. Execute in parallel
/project:exec-parallel-v2 new-skill prds/caching-skill-plan.md 3

# 4. Compare results
task parallel:compare FEATURE=new-skill

# 5. Integrate best approach
task parallel:integrate FEATURE=new-skill
```

## Critical Success Factors

### 1. Use Explicit Parallel Language
- ❌ "Implement this in three worktrees"
- ✅ "Create three agents working in parallel"

### 2. Provide Directory Context
- ❌ "Work on the feature"
- ✅ "Work in trees/feature-1/ directory"

### 3. Verify Location First
- Always run `cd <directory> && pwd` before starting work
- This prevents work in the wrong directory

## Common Patterns

### Pattern 1: Feature Exploration
```bash
# When you need to explore different approaches
task parallel:setup FEATURE=auth-system COUNT=3
# Agent 1: Simple password auth
# Agent 2: OAuth integration
# Agent 3: Multi-factor auth
```

### Pattern 2: Performance Optimization
```bash
# When optimizing existing code
task parallel:setup FEATURE=optimize-pipeline COUNT=3
# Agent 1: Caching approach
# Agent 2: Parallel processing
# Agent 3: Algorithm optimization
```

### Pattern 3: Refactoring Options
```bash
# When refactoring complex code
task parallel:setup FEATURE=refactor-validators COUNT=3
# Agent 1: Minimal changes
# Agent 2: Full rewrite
# Agent 3: Gradual migration
```

## Troubleshooting

### Issue: Sequential Execution
**Symptom**: Agents work one after another
**Fix**: Use explicit "create N agents in parallel" language

### Issue: Wrong Directory
**Symptom**: All changes in root directory
**Fix**: Each agent must `cd` to their worktree first

### Issue: No RESULTS.md
**Symptom**: Agents don't create summary files
**Fix**: Include "Create RESULTS.md when complete" in instructions
```

## Implementation Plan

### Phase 1: Core Infrastructure (Immediate)
1. Create `taskfiles/Taskfile.parallel.yml`
2. Create `.claude/commands/exec-parallel-v2.md`
3. Update main Taskfile to include parallel tasks
4. Test with simple feature

### Phase 2: Documentation (This Week)
1. Create parallel development guide
2. Add examples to cookbook
3. Document in CLAUDE.md
4. Create video tutorial

### Phase 3: Enhancement (Next Sprint)
1. Add progress monitoring
2. Create visual diff tools
3. Implement automated integration
4. Add team collaboration features

## Success Metrics
- Parallel execution success rate: >90%
- Time savings vs sequential: 3x faster
- Quality improvement: 50% better solutions
- Developer satisfaction: High

## Lessons Applied

From the atomic commits experience:
1. **Be explicit** about parallel execution
2. **Verify directory** before starting work  
3. **Use Task tool** with proper context
4. **Document results** in each worktree
5. **Compare systematically** after completion

## Next Steps

1. **Implement Phase 1** - Get basic system working
2. **Test with simple feature** - Validate parallel execution
3. **Document patterns** - Build knowledge base
4. **Train team** - Ensure everyone understands

---

**Document Version**: 2.0.0  
**Status**: Ready for Implementation  
**Owner**: Nanobricks Team  
**Last Updated**: January 2025