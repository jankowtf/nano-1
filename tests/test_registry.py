"""Tests for package registry functionality."""

import tempfile
from pathlib import Path

import pytest

from nanobricks.protocol import Nanobrick
from nanobricks.registry import (
    LocalRegistry,
    Package,
    PackageMetadata,
    RegistryClient,
    Version,
    VersionRange,
    create_package_from_brick,
    find_best_version,
    resolve_dependencies,
)


class TestVersion:
    """Test version parsing and comparison."""

    def test_parse_simple_version(self):
        """Test parsing simple versions."""
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None
        assert v.build is None

    def test_parse_prerelease_version(self):
        """Test parsing prerelease versions."""
        v = Version.parse("1.0.0-alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"

    def test_parse_build_version(self):
        """Test parsing versions with build metadata."""
        v = Version.parse("1.0.0+build.123")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.build == "build.123"

    def test_parse_complex_version(self):
        """Test parsing complex versions."""
        v = Version.parse("2.1.0-rc.1+build.456")
        assert v.major == 2
        assert v.minor == 1
        assert v.patch == 0
        assert v.prerelease == "rc.1"
        assert v.build == "build.456"

    def test_version_comparison(self):
        """Test version comparison."""
        v1 = Version.parse("1.0.0")
        v2 = Version.parse("1.0.1")
        v3 = Version.parse("1.1.0")
        v4 = Version.parse("2.0.0")

        assert v1 < v2 < v3 < v4
        assert v4 > v3 > v2 > v1
        assert v1 <= v1
        assert v1 >= v1
        assert v1 == v1
        assert v1 != v2

    def test_prerelease_comparison(self):
        """Test prerelease version comparison."""
        v1 = Version.parse("1.0.0-alpha")
        v2 = Version.parse("1.0.0-alpha.1")
        v3 = Version.parse("1.0.0-beta")
        v4 = Version.parse("1.0.0")

        assert v1 < v2 < v3 < v4

    def test_version_bump(self):
        """Test version bumping."""
        v = Version.parse("1.2.3")

        major = v.bump(VersionPart.MAJOR)
        assert str(major) == "2.0.0"

        minor = v.bump(VersionPart.MINOR)
        assert str(minor) == "1.3.0"

        patch = v.bump(VersionPart.PATCH)
        assert str(patch) == "1.2.4"

    def test_version_string(self):
        """Test version string representation."""
        assert str(Version(1, 2, 3)) == "1.2.3"
        assert str(Version(1, 0, 0, "alpha")) == "1.0.0-alpha"
        assert str(Version(1, 0, 0, None, "build")) == "1.0.0+build"
        assert str(Version(1, 0, 0, "beta", "123")) == "1.0.0-beta+123"


class TestVersionRange:
    """Test version range specifications."""

    def test_parse_exact_version(self):
        """Test exact version range."""
        r = VersionRange.parse("1.0.0")
        v1 = Version.parse("1.0.0")
        v2 = Version.parse("1.0.1")

        assert r.contains(v1)
        assert not r.contains(v2)

    def test_parse_minimum_version(self):
        """Test minimum version range."""
        r = VersionRange.parse(">=1.0.0")

        assert not r.contains(Version.parse("0.9.0"))
        assert r.contains(Version.parse("1.0.0"))
        assert r.contains(Version.parse("1.0.1"))
        assert r.contains(Version.parse("2.0.0"))

    def test_parse_caret_range(self):
        """Test caret (^) range."""
        r = VersionRange.parse("^1.2.3")

        assert not r.contains(Version.parse("1.2.2"))
        assert r.contains(Version.parse("1.2.3"))
        assert r.contains(Version.parse("1.3.0"))
        assert r.contains(Version.parse("1.9.9"))
        assert not r.contains(Version.parse("2.0.0"))

    def test_parse_tilde_range(self):
        """Test tilde (~) range."""
        r = VersionRange.parse("~1.2.3")

        assert not r.contains(Version.parse("1.2.2"))
        assert r.contains(Version.parse("1.2.3"))
        assert r.contains(Version.parse("1.2.9"))
        assert not r.contains(Version.parse("1.3.0"))

    def test_parse_compound_range(self):
        """Test compound version range."""
        r = VersionRange.parse(">=1.0.0,<2.0.0")

        assert not r.contains(Version.parse("0.9.0"))
        assert r.contains(Version.parse("1.0.0"))
        assert r.contains(Version.parse("1.5.0"))
        assert not r.contains(Version.parse("2.0.0"))

    def test_find_best_version(self):
        """Test finding best version."""
        versions = [
            Version.parse("1.0.0"),
            Version.parse("1.1.0"),
            Version.parse("1.2.0"),
            Version.parse("2.0.0-beta"),
            Version.parse("2.0.0"),
        ]

        # Latest in range
        r1 = VersionRange.parse("^1.0.0")
        best1 = find_best_version(versions, r1)
        assert str(best1) == "1.2.0"

        # Prefer stable
        r2 = VersionRange.parse(">=1.0.0")
        best2 = find_best_version(versions, r2, prefer_stable=True)
        assert str(best2) == "2.0.0"

        # Include prerelease
        best3 = find_best_version(versions, r2, prefer_stable=False)
        assert str(best3) == "2.0.0"  # Still picks stable when available


class TestPackageMetadata:
    """Test package metadata."""

    def test_create_metadata(self):
        """Test creating package metadata."""
        meta = PackageMetadata(
            name="test-brick",
            version="1.0.0",
            description="A test brick",
            author="Test Author",
            email="test@example.com",
            keywords=["test", "brick"],
        )

        assert meta.name == "test-brick"
        assert meta.version == "1.0.0"
        assert meta.description == "A test brick"
        assert meta.author == "Test Author"
        assert meta.keywords == ["test", "brick"]

    def test_metadata_serialization(self):
        """Test metadata serialization."""
        meta = PackageMetadata(
            name="test-brick",
            version="1.0.0",
            description="A test brick",
            author="Test Author",
        )

        # To dict
        data = meta.to_dict()
        assert data["name"] == "test-brick"
        assert data["version"] == "1.0.0"

        # From dict
        meta2 = PackageMetadata.from_dict(data)
        assert meta2.name == meta.name
        assert meta2.version == meta.version

    def test_metadata_toml(self):
        """Test TOML serialization."""
        meta = PackageMetadata(
            name="test-brick",
            version="1.0.0",
            description="A test brick",
            author="Test Author",
        )

        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            path = Path(f.name)

        try:
            # Save to TOML
            meta.to_toml(path)

            # Load from TOML
            meta2 = PackageMetadata.from_toml(path)
            assert meta2.name == meta.name
            assert meta2.version == meta.version
        finally:
            path.unlink()


class TestPackage:
    """Test package creation and management."""

    def test_create_package_from_brick(self):
        """Test creating package from brick."""
        brick = Nanobrick("test", "1.0.0")

        package = create_package_from_brick(
            brick,
            name="test-brick",
            version="1.0.0",
            author="Test Author",
            description="A test brick",
        )

        assert package.metadata.name == "test-brick"
        assert package.metadata.version == "1.0.0"
        assert package.metadata.brick_class.endswith("Nanobrick")
        assert len(package.files) > 0

    def test_package_archive(self):
        """Test package archiving."""
        meta = PackageMetadata(
            name="test-brick",
            version="1.0.0",
            description="A test brick",
            author="Test Author",
        )

        from nanobricks.registry.package import PackageFile

        files = [
            PackageFile(
                path="test.py",
                content=b"print('hello')",
                checksum="abc123",
                size=14,
            )
        ]

        package = Package(metadata=meta, files=files)

        # To archive
        archive = package.to_archive()
        assert isinstance(archive, bytes)
        assert len(archive) > 0

        # From archive
        package2 = Package.from_archive(archive)
        assert package2.metadata.name == package.metadata.name
        assert len(package2.files) == len(package.files)

    def test_package_extraction(self):
        """Test package extraction."""
        meta = PackageMetadata(
            name="test-brick",
            version="1.0.0",
            description="A test brick",
            author="Test Author",
        )

        from nanobricks.registry.package import PackageFile

        files = [
            PackageFile(
                path="src/test.py",
                content=b"print('hello')",
                checksum="abc123",
                size=14,
            )
        ]

        package = Package(metadata=meta, files=files)

        with tempfile.TemporaryDirectory() as tmpdir:
            extract_path = Path(tmpdir) / "extracted"
            package.extract_to(extract_path)

            # Check files
            assert (extract_path / "nanobrick.toml").exists()
            assert (extract_path / "src" / "test.py").exists()

            # Check content
            content = (extract_path / "src" / "test.py").read_text()
            assert content == "print('hello')"


class TestLocalRegistry:
    """Test local registry backend."""

    @pytest.mark.asyncio
    async def test_publish_package(self):
        """Test publishing a package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = LocalRegistry(Path(tmpdir))

            meta = PackageMetadata(
                name="test-brick",
                version="1.0.0",
                description="A test brick",
                author="Test Author",
                keywords=["test", "example"],
            )

            from nanobricks.registry.package import PackageFile

            package = Package(
                metadata=meta,
                files=[
                    PackageFile(
                        path="test.py",
                        content=b"print('hello')",
                        checksum="abc123",
                        size=14,
                    )
                ],
            )

            # Publish
            success = await registry.publish_package(package, "local-dev-key")
            assert success

            # Check index
            assert "test-brick" in registry.index["packages"]
            pkg_info = registry.index["packages"]["test-brick"]
            assert pkg_info["latest_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_search_packages(self):
        """Test searching packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = LocalRegistry(Path(tmpdir))

            # Add test packages
            registry.index["packages"] = {
                "data-processor": {
                    "metadata": {
                        "name": "data-processor",
                        "description": "Process data efficiently",
                        "author": "Alice",
                        "keywords": ["data", "processing"],
                    },
                    "latest_version": "1.0.0",
                    "total_downloads": 100,
                },
                "text-analyzer": {
                    "metadata": {
                        "name": "text-analyzer",
                        "description": "Analyze text data",
                        "author": "Bob",
                        "keywords": ["text", "nlp"],
                    },
                    "latest_version": "2.0.0",
                    "total_downloads": 50,
                },
            }

            # Search by name
            results = await registry.search("data")
            assert len(results) == 2
            assert results[0].name == "data-processor"  # Higher score

            # Search with filter
            results = await registry.search("", author="Alice")
            assert len(results) == 1
            assert results[0].author == "Alice"

    @pytest.mark.asyncio
    async def test_version_management(self):
        """Test version listing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = LocalRegistry(Path(tmpdir))

            # Add package with versions
            registry.index["packages"]["test-brick"] = {
                "versions": ["1.0.0", "1.1.0", "2.0.0-beta", "2.0.0"],
                "latest_version": "2.0.0",
                "latest_stable": "2.0.0",
            }

            versions = await registry.list_versions("test-brick")
            assert len(versions) == 4
            assert str(versions[0]) == "2.0.0"  # Latest first
            assert str(versions[1]) == "2.0.0-beta"


class TestRegistryClient:
    """Test registry client."""

    @pytest.mark.asyncio
    async def test_install_package(self):
        """Test installing a package."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry"
            install_path = Path(tmpdir) / "install"

            # Create registry and publish package
            registry = LocalRegistry(registry_path)
            client = RegistryClient(registry)

            meta = PackageMetadata(
                name="test-brick",
                version="1.0.0",
                description="A test brick",
                author="Test Author",
            )

            from nanobricks.registry.package import PackageFile

            package = Package(
                metadata=meta,
                files=[
                    PackageFile(
                        path="test.py",
                        content=b"print('hello')",
                        checksum="abc123",
                        size=14,
                    )
                ],
            )

            # Publish
            await client.publish(package, "local-dev-key")

            # Install
            installed = await client.install(
                "test-brick",
                version_spec=">=1.0.0",
                target_dir=install_path,
            )

            assert installed is not None
            assert installed.metadata.name == "test-brick"
            assert (install_path / "test.py").exists()

    @pytest.mark.asyncio
    async def test_dependency_resolution(self):
        """Test dependency resolution."""
        available = {
            "brick-a": [
                Version.parse("1.0.0"),
                Version.parse("1.1.0"),
                Version.parse("2.0.0"),
            ],
            "brick-b": [
                Version.parse("0.5.0"),
                Version.parse("1.0.0"),
            ],
        }

        dependencies = {
            "brick-a": "^1.0.0",  # 1.x.x
            "brick-b": ">=0.5.0",  # Any >= 0.5.0
        }

        resolved = resolve_dependencies(dependencies, available)

        assert str(resolved["brick-a"]) == "1.1.0"  # Latest 1.x
        assert str(resolved["brick-b"]) == "1.0.0"  # Latest available
