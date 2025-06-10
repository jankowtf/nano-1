# Pipe Operator Migration: `|` to `>>`

## Overview
This document tracks the migration from `|` (bitwise OR) to `>>` (right shift) as the pipe operator in nanobricks v0.2.0.

## Key Changes Required

### 1. Protocol Changes
- **File**: `src/nanobricks/protocol.py`
  - Change `__or__` method to `__rshift__` in `NanobrickProtocol`
  - Change `__or__` method to `__rshift__` in `NanobrickBase`
  - Update docstrings to reference `>>` instead of `|`

### 2. Composition Changes
- **File**: `src/nanobricks/composition.py`
  - Update any references to pipe operator
  - Ensure NanobrickComposite supports `>>` 

### 3. Test Changes
- **File**: `tests/unit/test_protocol.py`
  - Update test that verifies `__or__` exists to check for `__rshift__`
  - Update any pipe operator usage in tests

- **File**: `tests/unit/test_composition.py`
  - Update all pipe operator usage from `|` to `>>`

### 4. Documentation Changes
- **Files**: All `.qmd` files in `docs/quarto/`
  - Update code examples using `|` to use `>>`
  - Update explanations about pipe operator

- **File**: `CLAUDE.md`
  - Update examples to use `>>`

### 5. Example Changes
All Python files in `examples/` directory that use the pipe operator:
- `examples/cookbook/01_simple_pipeline.py`
- `examples/cookbook/05_testing_example.py`
- `examples/basic_pipeline.py`
- `examples/type_utilities_demo.py`
- `examples/sync_usage.py`
- `examples/advanced_validators.py`
- `examples/quick-start-project.py`
- `examples/devtools_demo.py`
- And many others...

### 6. Enhanced Classes
Classes that override `__or__` need to override `__rshift__` instead:
- `src/nanobricks/performance.py` - CachedNanobrick, PerformanceMonitoredNanobrick
- `src/nanobricks/production.py` - ProductionNanobrick
- `src/nanobricks/security.py` - SecureNanobrick
- `src/nanobricks/adaptive/adaptive.py` - AdaptiveNanobrick
- `src/nanobricks/devtools/*.py` - Various debug wrappers

## Migration Script
A script should be provided to automatically convert user code from `|` to `>>`.

## Backwards Compatibility
Consider supporting both operators during a deprecation period:
- v0.2.0: Support both `|` and `>>` with deprecation warning for `|`
- v0.3.0: Remove `|` support entirely