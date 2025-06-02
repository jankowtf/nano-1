# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Roadmap documentation based on real-world feedback from nano-scorm project
- Semantic versioning task automation in Taskfile.semver.yml
- Improved documentation structure with docs/quarto organization

### Changed
- Moved quarto documentation from root to docs/quarto directory

## [0.1.0] - 2025-01-06

### Added
- Core nanobrick protocol and base implementation
- Async-first design with `invoke` and `invoke_sync` methods
- Skills system with decorators for cross-cutting concerns
  - API skill for automatic FastAPI endpoint generation
  - Logging skill with structured output
  - CLI skill for Typer integration
  - Observability skill with OpenTelemetry support
- Composition patterns with pipe operator (`|`)
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

[Unreleased]: https://github.com/yourusername/nanobricks/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/nanobricks/releases/tag/v0.1.0