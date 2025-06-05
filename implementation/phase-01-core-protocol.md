# Phase 1: Core Protocol & Basic Composition

**Duration**: 1 session  
**Goal**: Establish the foundational protocol and basic composition mechanics

## Prerequisites
- [ ] Python 3.11+ environment with `uv` installed
- [ ] Basic project structure created
- [ ] Development dependencies installed

## Tasks

### 1.1 Create Core Protocol (30 min)
```python
# src/nanobricks/protocol.py
```
- [ ] Define TypeVars (T_in, T_out, T_deps)
- [ ] Create NanobrickProtocol with @runtime_checkable
- [ ] Create NanobrickBase ABC with invoke methods
- [ ] Add name and version attributes
- [ ] Implement invoke_sync wrapper

### 1.2 Implement Composition Operator (45 min)
```python
# src/nanobricks/composition.py
```
- [ ] Create CompositeBrick class
- [ ] Implement __or__ operator
- [ ] Handle type preservation in composition
- [ ] Add error propagation (fail-fast)
- [ ] Create tests for basic pipelines

### 1.3 Simple Error Handling (30 min)
```python
# src/nanobricks/errors.py
```
- [ ] Define NanobrickError base exception
- [ ] Create InvocationError for runtime failures
- [ ] Implement with_fallback method
- [ ] Add error context preservation
- [ ] Test error propagation in pipelines

### 1.4 First Working Examples (45 min)
```python
# examples/basic_pipeline.py
```
- [ ] Create Echo nanobrick (identity function)
- [ ] Create Uppercase transformer
- [ ] Create simple Validator
- [ ] Demonstrate basic pipeline: Echo >> Uppercase >> Validator
- [ ] Add async and sync usage examples

### 1.5 Basic Tests (30 min)
```python
# tests/test_core.py
```
- [ ] Test protocol compliance
- [ ] Test composition operator
- [ ] Test error propagation
- [ ] Test async/sync invocation
- [ ] Test type checking with mypy

## Deliverables
- Working core protocol implementation
- Basic composition with pipe operator
- Simple error handling
- 3-4 example nanobricks
- Test suite with >90% coverage

## Success Criteria
- [ ] Can create nanobricks by inheriting from NanobrickBase
- [ ] Can compose nanobricks with >> operator
- [ ] Errors propagate correctly through pipelines
- [ ] Both async and sync invocation work
- [ ] All tests pass and mypy is happy

## Next Phase Preview
Phase 2 will add:
- Dependency injection system
- Type safety improvements
- Contract support (pre/post conditions)
- Resource management