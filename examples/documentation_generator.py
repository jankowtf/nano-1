"""Example demonstrating the documentation generator."""

import asyncio
from pathlib import Path
from nanobricks.docs.enhanced_generator import EnhancedDocumentationGenerator


async def main():
    """Generate documentation for nanobricks."""
    print("🔍 Nanobricks Documentation Generator Example")
    print("=" * 50)
    
    # Initialize generator
    generator = EnhancedDocumentationGenerator(
        output_dir=Path("docs/generated"),
        include_examples=True,
        include_diagrams=True
    )
    
    # Discover nanobricks in the codebase
    print("\n📂 Discovering nanobricks...")
    search_paths = [
        Path("src/nanobricks/validators"),
        Path("src/nanobricks/transformers"),
        Path("src/nanobricks/skills"),
        Path("examples")
    ]
    
    all_bricks = []
    for path in search_paths:
        if path.exists():
            bricks = generator.discover_bricks([path])
            print(f"  Found {len(bricks)} bricks in {path}")
            all_bricks.extend(bricks)
    
    print(f"\n✨ Total nanobricks discovered: {len(all_bricks)}")
    
    # Group by category
    categories = {}
    for brick in all_bricks:
        if brick.category not in categories:
            categories[brick.category] = []
        categories[brick.category].append(brick)
    
    print("\n📊 Bricks by category:")
    for category, bricks in sorted(categories.items()):
        print(f"  {category}: {len(bricks)} bricks")
        for brick in bricks[:3]:  # Show first 3
            print(f"    - {brick.name} ({brick.input_type} → {brick.output_type})")
        if len(bricks) > 3:
            print(f"    ... and {len(bricks) - 3} more")
    
    # Generate documentation
    print("\n📝 Generating documentation...")
    
    # Markdown documentation
    print("  Generating Markdown...")
    generator.generate_markdown(all_bricks)
    
    # JSON documentation
    print("  Generating JSON...")
    generator.generate_json(all_bricks)
    
    print(f"\n✅ Documentation generated in: {generator.output_dir}")
    
    # Show sample of generated files
    print("\n📄 Generated files:")
    if generator.output_dir.exists():
        files = list(generator.output_dir.rglob("*.md"))[:5]
        for file in files:
            print(f"  - {file.relative_to(generator.output_dir)}")
        if len(list(generator.output_dir.rglob("*.md"))) > 5:
            print(f"  ... and more")
    
    # Example of programmatic access to brick info
    print("\n🔧 Example: Accessing brick information programmatically")
    if all_bricks:
        example_brick = all_bricks[0]
        print(f"\nBrick: {example_brick.name}")
        print(f"  Module: {example_brick.module_path}")
        print(f"  Type: {example_brick.input_type} → {example_brick.output_type}")
        print(f"  Description: {example_brick.description}")
        if example_brick.constructor_params:
            print(f"  Constructor params:")
            for param, type_str in example_brick.constructor_params.items():
                print(f"    - {param}: {type_str}")
        if example_brick.methods:
            print(f"  Methods: {', '.join(example_brick.methods)}")


if __name__ == "__main__":
    asyncio.run(main())