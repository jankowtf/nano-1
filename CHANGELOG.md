# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.3] - 2025-06-06

### Added

- **AI-First Documentation System**: Revolutionary agentic documentation framework

  - Created `docs/agentic/` directory with specialized formats for AI agents
  - Implemented llms.txt standard for AI discovery and navigation
  - Added executable contracts in Python for validation
  - Introduced JSON-LD knowledge graphs for semantic relationships
  - Built comprehensive task registry for common AI operations
  - Established tool definitions for AI-assisted development
  - Created memory structures for persistent AI understanding

- **Agentic Task Workflows**: New task system for AI documentation

  - Added `Taskfile.agentic.yml` with validation, sync, and maintenance tasks
  - Implemented automated context generation from code
  - Built synchronization workflows between human and AI docs
  - Added version management for agentic documentation
  - Created CI/CD integration tasks for validation

- **Documentation Bridge System**: Integration between human and AI docs

  - Built context injection system for Quarto documents
  - Added AI-specific CSS classes for visual differentiation
  - Created dual-mode documentation supporting both audiences
  - Implemented context-aware blocks in human documentation

- **Enhanced Documentation Structure**: Major reorganization
  - Reordered sections: Getting Started, Core Concepts, Building Systems, Cookbook, Advanced Topics
  - Consolidated Evolution section with nested subsections
  - Added comprehensive agentic documentation guides
  - Created format decision documentation explaining YAML/JSON/JSON-LD/Python choices

### Fixed

- **Markdown Formatting**: Improved list formatting across all documentation

  - Fixed 36 files to ensure empty lines before all markdown lists
  - Resolved parsing issues in various documentation files
  - Enhanced readability and consistency

- **Validation Errors**: Fixed multiple issues in agentic documentation
  - Corrected syntax errors in task JSON files
  - Fixed YAML parsing issues in version checks
  - Resolved orphaned AI context files
  - Aligned context filenames with corresponding .qmd files

### Changed

- **Documentation Focus**: Shifted to treat AI developers as first-class citizens
  - Added dedicated AI agent sections throughout
  - Created AI-specific tutorials and walkthroughs
  - Built comprehensive cheatsheets for AI agents
  - Established clear patterns for AI consumption

### Improved

- **Task System Documentation**: Enhanced CLAUDE.md files
  - Updated main CLAUDE.md with latest commands and patterns
  - Created taskfiles/CLAUDE.md with comprehensive task guidance
  - Added agentic task documentation and workflows
  - Improved memory and convention tracking

## [0.2.2] - 2025-06-05

### Changed

- **Task System Organization**: Restructured task files for better maintainability
  - Moved all Taskfile\*.yml to `taskfiles/` directory
  - Created `scripts/` directory for general utilities
  - Created `taskfiles/scripts/` for task-specific scripts
  - Extracted common Claude CLI discovery logic into `find-claude.sh`
  - Applied DRY principles across all taskfiles

### Fixed

- **Documentation Consistency**: Completed migration from `|` to `>>` operator
  - Fixed remaining instances in architecture.qmd and comparison.qmd
  - Updated method references from `__or__` to `__rshift__`
  - Corrected cookbook examples to use new operator syntax
  - Ensured all code examples use current API

### Added

- **Enhanced Claude Integration**: Improved developer experience
  - Verbose mode support with `CLAUDE_VERBOSE=1`
  - Progress indicators for non-verbose mode
  - Better error messages when Claude CLI not found
  - Team-friendly setup documentation in taskfiles/README.md

### Improved

- **Documentation Rendering**: Better visual presentation
  - Mermaid diagrams now render without showing source code
  - Python examples remain visible with proper syntax highlighting
  - Cleaner architecture-diagrams.qmd layout

## [0.2.1] - 2025-06-05

### Changed

- **Task System Refactoring**: Renamed `project:*` namespace to `dev:*` for consistency
  - All project management tasks now under unified `dev:` prefix
  - Updated documentation to reflect new namespace
  - Better organization and discoverability of development tasks

### Fixed

- **Symbolic Link Handling**: Improved symlink creation for better tool compatibility
  - Refactored to use absolute paths throughout
  - Enhanced compatibility with Claude Code's file referencing
  - Added verification step to ensure symlinks are created correctly
  - Better logging showing both source and resolved paths

### Added

- **Developer Documentation**: Enhanced documentation for symlink management
  - Added README.md in dependents directory explaining symlink structure
  - Updated .gitignore to properly handle dependent project symlinks
  - Improved task documentation with absolute path information

## [0.2.0] - 2025-06-05

### Added

- **Pipeline Builder API**: Fluent interface for complex compositions beyond simple piping
  - `Pipeline()` function creates a builder for method chaining
  - `.branch()` for conditional routing with custom condition functions
  - `.parallel()` for concurrent execution of multiple bricks
  - `.merge_with()` to combine results from parallel/branching operations
  - `.catch_errors()` for error boundaries at any pipeline stage
  - `.adapt()` for explicit type conversions between incompatible stages
  - `.visualize()` and `.explain()` for pipeline introspection
  - Comprehensive test suite covering all builder features
- **Migration Script**: `migrate_pipe_operator.py` to convert code from `|` to `>>`
- **Example**: `pipeline_builder_demo.py` showcasing all PipelineBuilder features

### Changed

- **Pipe operator changed from `|` to `>>`**: More intuitive arrow syntax (with deprecation period)
  - Added `__rshift__` method for `>>` operator support
  - Visual arrow metaphor (`>>`) better represents data flow
  - Less ambiguity compared to `|` (which often means "OR")
  - Migration script provided for easy conversion
- **Composite naming**: Pipeline names now show `Brick1>>Brick2` instead of `Brick1|Brick2`

### Deprecated

- The `|` operator for composition - Use `>>` instead (will be removed in v0.3.0)
  - Both operators work during transition period
  - Using `|` will emit a DeprecationWarning

### Fixed

- **Test Suite Cleanup**: Aligned tests with framework philosophy
  - Removed tests for non-existent features (ConnectionPool, Bulkhead, etc.)
  - Fixed import errors and API mismatches
  - All tests now passing, focusing on simplicity over complexity

## [0.1.3] - 2025-01-06

### Added

- **Enhanced Git Integration**: New git tasks in version management workflow
  - `task version:commit:version` - Commit with auto-generated message
  - `task version:release` - Complete release workflow (commit, tag, push)
  - Dynamic date handling using system commands
- **Migration Script**: `migrate_to_nanobrick.py` to update imports automatically

### Changed

- **Renamed `NanobrickSimple` to `Nanobrick`**: Clearer naming for the primary class
  - `Nanobrick[T_in, T_out]` is now the main class for 99% of use cases
  - `NanobrickBase[T_in, T_out, T_deps]` remains for advanced scenarios
  - `NanobrickSimple` kept as deprecated alias for backwards compatibility
- **Updated all examples and documentation** to use the new `Nanobrick` name
- **Improved task date handling** to use system date commands instead of hardcoded values

### Deprecated

- `NanobrickSimple` - Use `Nanobrick` instead (will be removed in v0.2.0)

## [0.1.2] - 2025-01-06

### Added

- **Type Utilities** - New module providing enhanced type support for composition
  - `Result[T, E]` type for Rust-inspired explicit error handling
  - `TypeAdapter` class for automatic type conversions in pipelines
  - Built-in adapters: `string_to_dict()`, `dict_to_string()`, `json_to_dict()`, `dict_to_json()`, `list_to_tuple()`, `tuple_to_list()`
  - `auto_adapter()` function to automatically create adapters between compatible types
  - `check_type_compatibility()` utility for runtime type validation
- **Enhanced Error Messages** - Better type mismatch errors in pipe operations
  - `TypeMismatchError` with clear output/expected type information
  - Automatic suggestions for compatible type adapters
  - Type checking during composition with helpful error messages
- **Type Documentation** - New comprehensive documentation page for type utilities
- **Examples** - New `type_utilities_demo.py` showcasing all type features

### Changed

- Enhanced `NanobrickComposite` with type validation during composition
- Improved pipe operator to provide better error messages on type mismatches

### Fixed

- Type compatibility issues when composing bricks with slightly different types
- Unclear error messages when pipe operator encounters type mismatches

## [0.1.1] - 2025-01-06

### Added

- Comprehensive Cookbook section with practical recipes and patterns
  - Basic pipeline guide showing pipe operator usage
  - Dependency injection guide with `deps` parameter patterns
  - Error handling patterns comparing exceptions vs result types
  - Testing patterns for unit and integration testing
  - Architecture decision guide for composition vs inheritance
- Five complete example scripts in examples/cookbook/
- Roadmap documentation based on real-world feedback from nano-scorm project
- Semantic versioning task automation with resource-based naming in Taskfile.semver.yml
  - `version:*` commands for version management
  - `changelog:*` commands for changelog operations
  - Single source of truth in pyproject.toml

### Changed

- Moved quarto documentation from root to docs/quarto directory
- Updated navigation to include cookbook section prominently

### Documentation

- Zero code changes - pure documentation improvements addressing user feedback
- All examples tested and type-checked
- Clear problem/solution format for each pattern
- Links between related topics

## [0.1.0] - 2025-01-06

### Added

- Core nanobrick protocol and base implementation
- Async-first design with `invoke` and `invoke_sync` methods
- Skills system with decorators for cross-cutting concerns
  - API skill for automatic FastAPI endpoint generation
  - Logging skill with structured output
  - CLI skill for Typer integration
  - Observability skill with OpenTelemetry support
- Composition patterns with pipe operator (`|`) [Changed to `>>` in v0.2.0]
- Built-in transformers and validators
- Type-safe generics support
- Configuration system with TOML support
- CLI scaffolding tool (`nanobrick new`)
- Comprehensive test suite
- Quarto-based documentation
- Examples demonstrating various patterns
- Registry system for nanobrick discovery
- Hot-swapping capabilities
- Security features with sandboxing
- Performance monitoring
- Production-ready patterns

### Features Demonstrated

- Self-contained, atomic components
- Protocol + ABC hybrid for type and runtime safety
- Directory-based module structure
- Dependency injection support
- Resource management with context managers
- Error handling patterns
- AI integration via MCP protocol

[Unreleased]: https://github.com/yourusername/nanobricks/compare/v0.2.3...HEAD
[0.2.3]: https://github.com/yourusername/nanobricks/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/yourusername/nanobricks/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/yourusername/nanobricks/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/yourusername/nanobricks/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/yourusername/nanobricks/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/yourusername/nanobricks/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/yourusername/nanobricks/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/yourusername/nanobricks/releases/tag/v0.1.0
