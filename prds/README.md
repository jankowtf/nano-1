# Product Requirements Documents

## Active PRDs

### prd-parallel-development-unified.md
**Status**: Ready for Implementation  
**Summary**: Unified plan for implementing parallel development using git worktrees and Claude Code. Incorporates lessons learned from the atomic commits test case.

## Background

The parallel development system enables exploring multiple implementation approaches simultaneously using git worktrees. The initial test with atomic commits revealed issues with Claude's Task tool execution, leading to sequential rather than parallel work. This PRD addresses those issues with:

1. Enhanced exec-parallel command with explicit parallel agent creation
2. Comprehensive Taskfile.parallel.yml for worktree management  
3. Clear best practices and troubleshooting guide

## Implementation Status

- ✅ Lessons learned from atomic commits test
- ✅ Root cause analysis complete
- ✅ Solution designed
- ⏳ Ready for implementation
- ❌ Not yet tested with true parallel execution

## Archived PRDs

Older PRDs have been moved to `_archive/` to reduce confusion. These include:
- Original parallel worktree integration PRD
- Atomic commits analysis documents
- Various integration plans

The unified PRD consolidates all learnings and provides a clear path forward.