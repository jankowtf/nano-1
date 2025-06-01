# Nanobricks Documentation

This directory contains the Quarto-based documentation for Nanobricks, positioned as "The SDK for building composable Python systems."

## Documentation Structure

### For New Users
1. **index.qmd** - Landing page with overview and value proposition
2. **quickstart.qmd** - 10-minute guide to get started
3. **tutorial.qmd** - Comprehensive step-by-step tutorial
4. **sdk-guide.qmd** - Building production systems with Nanobricks

### For Developers
1. **production-examples.qmd** - Real-world, complete examples
2. **patterns.qmd** - Design patterns and best practices
3. **comparison.qmd** - How Nanobricks compares to other frameworks
4. **architecture-diagrams.qmd** - Visual guide to composition patterns

### Core Concepts
1. **principles.qmd** - The 10 commandments of Nanobricks
2. **architecture.qmd** - Technical architecture details
3. **type-safety.qmd** - Type system and inference
4. **configuration.qmd** - Configuration system guide

### Advanced Topics
1. **ai-integration.qmd** - AI and LLM integration
2. **ai-protocols.qmd** - Agent communication protocols
3. **superpowers.qmd** - Advanced composition patterns

### Historical/Design
1. **evolution.qmd** - How the concept evolved
2. **human.qmd** - Original implementation guide (being phased out)
3. **v1/** and **v2/** - Historical concept documents

## Building the Documentation

```bash
# Install Quarto (if not already installed)
# See: https://quarto.org/docs/get-started/

# Preview with hot reload
quarto preview

# Build static site
quarto render

# The output will be in _site/
```

## Key Design Decisions

### SDK Focus
The documentation positions Nanobricks as an SDK for building larger systems, not just a utility library. This is reflected in:
- Practical, production-ready examples
- Emphasis on composition and architecture patterns
- Integration guides with existing frameworks
- Clear comparison showing unique value proposition

### Progressive Disclosure
Documentation follows a learning path:
1. Quick win (10-minute quickstart)
2. Understanding (tutorial)
3. Building real systems (SDK guide)
4. Production deployment (examples)

### Visual Learning
Heavy use of Mermaid diagrams to illustrate:
- Composition patterns
- Architecture flows
- System designs
- Deployment patterns

### Code-First Examples
All examples are designed to be:
- Runnable (where possible)
- Production-ready
- Demonstrating best practices
- Showing real-world use cases

## Navigation Structure

### Top Navigation (Navbar)
- Home → Quickstart → Tutorial → SDK Guide → More (dropdown)

### Side Navigation (Sidebar)
Organized by user journey:
1. Getting Started
2. Building Systems  
3. Core Concepts
4. Advanced Topics
5. Evolution (historical)

## Style Guidelines

### Code Examples
- Use `#| eval: false` for examples that can't run in Quarto
- Add explanatory comments for async/await usage
- Show both simple and advanced usage
- Include error handling in production examples

### Diagrams
- Use Mermaid for all diagrams
- Keep diagrams focused on one concept
- Use consistent color schemes
- Include code examples with diagrams

### Writing Style
- Direct and concise
- Focus on practical usage
- Avoid academic language
- Use examples to explain concepts

## Future Additions

1. **api-reference.qmd** - Auto-generated API documentation
2. **cookbook.qmd** - Recipes for common tasks
3. **troubleshooting.qmd** - Common issues and solutions
4. **migration-guide.qmd** - Migrating from other frameworks
5. **video-tutorials.qmd** - Links to video content

## Contributing

When adding new documentation:
1. Follow the existing structure
2. Add to appropriate section in _quarto.yml
3. Include practical examples
4. Add visual diagrams where helpful
5. Test that examples work (or mark why they don't)
6. Update this README if adding new sections