# Phase 2: Enhanced Core Features

**Duration**: 1 session  
**Goal**: Add dependency injection, contracts, and resource management

## Prerequisites

- [ ] Phase 1 completed and tested
- [ ] Core protocol working with basic composition

## Tasks

### 2.1 Dependency Injection System (45 min)

```python
# src/nanobricks/dependencies.py
```

- [ ] Create dependency container using TypedDict
- [ ] Implement with_deps method for pipelines
- [ ] Add dependency merging for composition
- [ ] Support partial dependency override
- [ ] Create examples with database/cache deps

### 2.2 Contract System (45 min)

```python
# src/nanobricks/contracts.py
```

- [ ] Create @nanobrick decorator
- [ ] Add precondition checking
- [ ] Add postcondition validation
- [ ] Implement invariant support
- [ ] Add contract violation exceptions

### 2.3 Resource Management (30 min)

```python
# src/nanobricks/resources.py
```

- [ ] Add context manager support to NanobrickBase
- [ ] Implement resource limits (memory, timeout)
- [ ] Create ResourceBoundedBrick mixin
- [ ] Add cleanup guarantees
- [ ] Test resource cleanup in pipelines

### 2.4 Type Safety Improvements (30 min)

```python
# src/nanobricks/typing.py
```

- [ ] Create type aliases for common patterns
- [ ] Add better generic constraints
- [ ] Implement type-safe composition helpers
- [ ] Create typed pipeline builder
- [ ] Add runtime type checking with beartype

### 2.5 Integration Examples (30 min)

```python
# examples/advanced_features.py
```

- [ ] Database integration example with deps
- [ ] Contract-based validator example
- [ ] Resource-limited processor
- [ ] Complex pipeline with all features
- [ ] Performance comparison tests

## Deliverables

- Dependency injection system
- Contract/invariant support
- Resource management
- Enhanced type safety
- Integration examples

## Success Criteria

- [ ] Dependencies flow through pipelines correctly
- [ ] Contracts are enforced at runtime
- [ ] Resources are properly managed and cleaned up
- [ ] Type inference works for 3+ level pipelines
- [ ] No performance regression from Phase 1

## Next Phase Preview

Phase 3 will add:

- Configuration system (TOML)
- Basic skill framework
- Lazy loading registry
- Feature flags
