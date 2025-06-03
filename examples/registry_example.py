"""Example demonstrating package registry functionality."""

import asyncio
from pathlib import Path

from nanobricks import Nanobrick
from nanobricks.registry import (
    Package,
    PackageMetadata,
    RegistryClient,
    Version,
    create_package_from_brick,
    get_registry,
)


# Example bricks to package
class TextProcessor(Nanobrick[str, str]):
    """Process text with various transformations."""
    
    def __init__(self):
        super().__init__(name="text-processor", version="1.0.0")
    
    async def invoke(self, input: str, *, deps=None) -> str:
        # Simple text processing
        return input.strip().lower().replace(" ", "_")


class DataValidator(Nanobrick[dict, dict]):
    """Validate data structures."""
    
    def __init__(self):
        super().__init__(name="data-validator", version="2.1.0")
    
    async def invoke(self, input: dict, *, deps=None) -> dict:
        # Validate required fields
        required = ["name", "email"]
        missing = [f for f in required if f not in input]
        
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return {"valid": True, "data": input}


async def demo_package_creation():
    """Demonstrate creating packages from bricks."""
    print("\n=== Package Creation Demo ===")
    
    # Create a brick
    processor = TextProcessor()
    
    # Create package metadata
    package = create_package_from_brick(
        processor,
        name="text-processor",
        version="1.0.0",
        author="Alice Developer",
        description="A powerful text processing nanobrick",
        keywords=["text", "processing", "nlp"],
        homepage="https://example.com/text-processor",
    )
    
    print(f"\nCreated package: {package.metadata.name} v{package.metadata.version}")
    print(f"Author: {package.metadata.author}")
    print(f"Description: {package.metadata.description}")
    print(f"Files: {len(package.files)}")
    
    # Show package checksum
    print(f"Package checksum: {package.checksum[:16]}...")
    
    # Create archive
    archive = package.to_archive()
    print(f"Archive size: {len(archive) / 1024:.2f} KB")
    
    return package


async def demo_registry_publishing():
    """Demonstrate publishing to registry."""
    print("\n=== Registry Publishing Demo ===")
    
    # Get registry client
    registry = get_registry()
    
    # Create packages
    packages = []
    
    # Text processor v1.0.0
    processor_v1 = create_package_from_brick(
        TextProcessor(),
        name="text-processor",
        version="1.0.0",
        author="Alice Developer",
        description="A powerful text processing nanobrick",
        keywords=["text", "processing"],
    )
    packages.append(processor_v1)
    
    # Text processor v1.1.0
    processor_v2 = create_package_from_brick(
        TextProcessor(),
        name="text-processor",
        version="1.1.0",
        author="Alice Developer",
        description="A powerful text processing nanobrick (improved)",
        keywords=["text", "processing", "nlp"],
    )
    packages.append(processor_v2)
    
    # Data validator
    validator = create_package_from_brick(
        DataValidator(),
        name="data-validator",
        version="2.1.0",
        author="Bob Builder",
        description="Validate data structures with ease",
        keywords=["validation", "data", "schema"],
    )
    packages.append(validator)
    
    # Publish all packages
    for pkg in packages:
        success = await registry.publish(pkg, "local-dev-key")
        if success:
            print(f"✓ Published {pkg.metadata.name} v{pkg.metadata.version}")
        else:
            print(f"✗ Failed to publish {pkg.metadata.name}")


async def demo_package_search():
    """Demonstrate searching packages."""
    print("\n=== Package Search Demo ===")
    
    registry = get_registry()
    
    # Search for text-related packages
    print("\nSearching for 'text':")
    results = await registry.search("text", limit=10)
    
    for result in results:
        print(f"  - {result.name} v{result.version}")
        print(f"    {result.description}")
        print(f"    Downloads: {result.downloads}, Score: {result.score}")
    
    # Search by author
    print("\nSearching by author 'Alice':")
    results = await registry.search("", author="Alice Developer")
    
    for result in results:
        print(f"  - {result.name} by {result.author}")
    
    # Search by keyword
    print("\nSearching for validation packages:")
    results = await registry.search("validation")
    
    for result in results:
        print(f"  - {result.name}: {result.description}")


async def demo_package_info():
    """Demonstrate getting package information."""
    print("\n=== Package Info Demo ===")
    
    registry = get_registry()
    
    # Get package info
    info = await registry.info("text-processor")
    
    if info:
        print(f"\nPackage: {info.metadata.name}")
        print(f"Latest version: {info.latest_version}")
        print(f"Latest stable: {info.latest_stable}")
        print(f"Total downloads: {info.total_downloads}")
        
        print("\nAvailable versions:")
        for version in info.versions:
            downloads = info.downloads.get(str(version), 0)
            print(f"  - {version} ({downloads} downloads)")
    else:
        print("Package not found")


async def demo_version_management():
    """Demonstrate version parsing and comparison."""
    print("\n=== Version Management Demo ===")
    
    # Parse versions
    versions = [
        "1.0.0",
        "1.0.1",
        "1.1.0",
        "2.0.0-alpha",
        "2.0.0-beta.1",
        "2.0.0",
    ]
    
    print("\nParsing versions:")
    parsed = []
    for v_str in versions:
        v = Version.parse(v_str)
        parsed.append(v)
        print(f"  {v_str} -> major={v.major}, minor={v.minor}, patch={v.patch}, pre={v.prerelease}")
    
    # Sort versions
    print("\nSorted versions (newest first):")
    parsed.sort(reverse=True)
    for v in parsed:
        print(f"  {v}")
    
    # Version ranges
    print("\nVersion range examples:")
    
    from nanobricks.registry import VersionRange, find_best_version
    
    # Caret range (^) - compatible versions
    range1 = VersionRange.parse("^1.0.0")
    print(f"\n^1.0.0 (compatible with 1.0.0):")
    for v in parsed:
        if range1.contains(v):
            print(f"  ✓ {v}")
        else:
            print(f"  ✗ {v}")
    
    # Find best version
    best = find_best_version(parsed, range1, prefer_stable=True)
    print(f"  Best version: {best}")


async def demo_package_installation():
    """Demonstrate installing packages."""
    print("\n=== Package Installation Demo ===")
    
    registry = get_registry()
    
    # Install latest version
    print("\nInstalling text-processor (latest):")
    package = await registry.install(
        "text-processor",
        target_dir=Path("temp/text-processor"),
    )
    
    if package:
        print(f"✓ Installed {package.metadata.name} v{package.metadata.version}")
        print(f"  Files: {len(package.files)}")
    
    # Install specific version
    print("\nInstalling text-processor v1.0.0:")
    package = await registry.install(
        "text-processor",
        version_spec="==1.0.0",
        target_dir=Path("temp/text-processor-v1"),
    )
    
    if package:
        print(f"✓ Installed {package.metadata.name} v{package.metadata.version}")
    
    # List installed packages
    print("\nInstalled packages:")
    installed = await registry.list_installed(Path("temp"))
    
    for pkg_info in installed:
        print(f"  - {pkg_info.metadata.name} v{pkg_info.metadata.version}")
        print(f"    {pkg_info.metadata.description}")


async def demo_dependency_resolution():
    """Demonstrate dependency resolution."""
    print("\n=== Dependency Resolution Demo ===")
    
    from nanobricks.registry import resolve_dependencies
    
    # Available versions
    available = {
        "nanobrick-core": [
            Version.parse("1.0.0"),
            Version.parse("1.1.0"),
            Version.parse("1.2.0"),
            Version.parse("2.0.0"),
        ],
        "nanobrick-utils": [
            Version.parse("0.9.0"),
            Version.parse("1.0.0"),
            Version.parse("1.1.0"),
        ],
        "nanobrick-types": [
            Version.parse("1.0.0"),
            Version.parse("2.0.0-beta"),
            Version.parse("2.0.0"),
        ],
    }
    
    # Dependencies with constraints
    dependencies = {
        "nanobrick-core": "^1.0.0",      # Compatible with 1.x
        "nanobrick-utils": ">=1.0.0",    # At least 1.0.0
        "nanobrick-types": "~1.0.0",     # Approximately 1.0.x
    }
    
    print("\nResolving dependencies:")
    for pkg, constraint in dependencies.items():
        print(f"  {pkg}: {constraint}")
    
    # Resolve
    resolved = resolve_dependencies(dependencies, available)
    
    print("\nResolved versions:")
    for pkg, version in resolved.items():
        print(f"  {pkg}: {version}")


async def cleanup_temp():
    """Clean up temporary files."""
    import shutil
    
    temp_dir = Path("temp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
        print("\nCleaned up temporary files")


async def main():
    """Run all registry demos."""
    print("Nanobricks Package Registry Examples")
    print("=" * 50)
    
    # Create and show package
    package = await demo_package_creation()
    
    # Publish to registry
    await demo_registry_publishing()
    
    # Search packages
    await demo_package_search()
    
    # Get package info
    await demo_package_info()
    
    # Version management
    await demo_version_management()
    
    # Install packages
    await demo_package_installation()
    
    # Dependency resolution
    await demo_dependency_resolution()
    
    # Cleanup
    await cleanup_temp()
    
    print("\n" + "=" * 50)
    print("Registry demos completed!")


if __name__ == "__main__":
    asyncio.run(main())