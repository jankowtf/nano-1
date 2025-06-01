"""Package format and metadata for nanobricks."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import toml

from nanobricks.protocol import NanobrickProtocol


@dataclass
class PackageMetadata:
    """Metadata for a nanobrick package."""

    name: str
    version: str
    description: str
    author: str
    email: str | None = None
    license: str = "MIT"
    homepage: str | None = None
    repository: str | None = None
    keywords: list[str] = field(default_factory=list)
    classifiers: list[str] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    python_requires: str = ">=3.11"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Nanobrick-specific metadata
    brick_class: str | None = None
    skills: list[str] = field(default_factory=list)
    input_type: str | None = None
    output_type: str | None = None
    deps_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "email": self.email,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "keywords": self.keywords,
            "classifiers": self.classifiers,
            "dependencies": self.dependencies,
            "python_requires": self.python_requires,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "brick_class": self.brick_class,
            "skills": self.skills,
            "input_type": self.input_type,
            "output_type": self.output_type,
            "deps_type": self.deps_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PackageMetadata":
        """Create from dictionary."""
        # Convert ISO format dates back to datetime
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)

    @classmethod
    def from_toml(cls, path: Path) -> "PackageMetadata":
        """Load from TOML file."""
        with open(path) as f:
            data = toml.load(f)

        # Extract metadata from appropriate section
        if "package" in data:
            metadata = data["package"]
        elif "tool" in data and "nanobrick" in data["tool"]:
            metadata = data["tool"]["nanobrick"]
        else:
            metadata = data

        return cls.from_dict(metadata)

    def to_toml(self, path: Path):
        """Save to TOML file."""
        data = {"package": self.to_dict()}
        with open(path, "w") as f:
            toml.dump(data, f)


@dataclass
class PackageFile:
    """A file in a nanobrick package."""

    path: str
    content: bytes
    checksum: str
    size: int

    @classmethod
    def from_file(cls, base_path: Path, file_path: Path) -> "PackageFile":
        """Create from file path."""
        relative_path = file_path.relative_to(base_path)
        content = file_path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()

        return cls(
            path=str(relative_path),
            content=content,
            checksum=checksum,
            size=len(content),
        )


@dataclass
class Package:
    """A complete nanobrick package."""

    metadata: PackageMetadata
    files: list[PackageFile]
    checksum: str | None = None

    def __post_init__(self):
        """Calculate package checksum."""
        if not self.checksum:
            # Combine all file checksums
            combined = "".join(
                f.checksum for f in sorted(self.files, key=lambda x: x.path)
            )
            self.checksum = hashlib.sha256(combined.encode()).hexdigest()

    def get_file(self, path: str) -> PackageFile | None:
        """Get file by path."""
        for file in self.files:
            if file.path == path:
                return file
        return None

    def to_archive(self) -> bytes:
        """Create archive format (tar.gz)."""
        import io
        import tarfile

        buffer = io.BytesIO()

        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Add metadata
            metadata_json = json.dumps(self.metadata.to_dict(), indent=2)
            metadata_info = tarfile.TarInfo("nanobrick.json")
            metadata_info.size = len(metadata_json)
            tar.addfile(metadata_info, io.BytesIO(metadata_json.encode()))

            # Add files
            for file in self.files:
                info = tarfile.TarInfo(file.path)
                info.size = file.size
                tar.addfile(info, io.BytesIO(file.content))

        return buffer.getvalue()

    @classmethod
    def from_archive(cls, data: bytes) -> "Package":
        """Create from archive format."""
        import io
        import tarfile

        buffer = io.BytesIO(data)
        files = []
        metadata = None

        with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "nanobrick.json":
                    # Extract metadata
                    f = tar.extractfile(member)
                    if f:
                        metadata_dict = json.loads(f.read().decode())
                        metadata = PackageMetadata.from_dict(metadata_dict)
                else:
                    # Extract file
                    f = tar.extractfile(member)
                    if f:
                        content = f.read()
                        files.append(
                            PackageFile(
                                path=member.name,
                                content=content,
                                checksum=hashlib.sha256(content).hexdigest(),
                                size=len(content),
                            )
                        )

        if not metadata:
            raise ValueError("No metadata found in package")

        return cls(metadata=metadata, files=files)

    @classmethod
    def from_directory(cls, path: Path) -> "Package":
        """Create package from directory."""
        # Load metadata
        metadata_path = path / "nanobrick.toml"
        if not metadata_path.exists():
            raise ValueError(f"No nanobrick.toml found in {path}")

        metadata = PackageMetadata.from_toml(metadata_path)

        # Collect files
        files = []
        ignore_patterns = {
            "__pycache__",
            ".pyc",
            ".pyo",
            ".egg-info",
            ".git",
            ".gitignore",
            ".DS_Store",
            ".venv",
            "*.log",
            "*.tmp",
            "*.bak",
        }

        for file_path in path.rglob("*"):
            if file_path.is_file():
                # Check if should ignore
                should_ignore = False
                for pattern in ignore_patterns:
                    if pattern in str(file_path):
                        should_ignore = True
                        break

                if not should_ignore:
                    files.append(PackageFile.from_file(path, file_path))

        return cls(metadata=metadata, files=files)

    def extract_to(self, path: Path):
        """Extract package to directory."""
        path.mkdir(parents=True, exist_ok=True)

        # Write metadata
        self.metadata.to_toml(path / "nanobrick.toml")

        # Write files
        for file in self.files:
            file_path = path / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file.content)


def create_package_from_brick(
    brick: NanobrickProtocol,
    name: str,
    version: str,
    author: str,
    description: str,
    **kwargs,
) -> Package:
    """Create a package from a nanobrick instance."""
    import inspect

    # Get brick module and source
    module = inspect.getmodule(brick.__class__)
    if not module:
        raise ValueError("Cannot determine brick module")

    source_file = inspect.getsourcefile(brick.__class__)
    if not source_file:
        raise ValueError("Cannot determine brick source file")

    # Create metadata
    metadata = PackageMetadata(
        name=name,
        version=version,
        author=author,
        description=description,
        brick_class=f"{module.__name__}.{brick.__class__.__name__}",
        **kwargs,
    )

    # Get type hints if available
    if hasattr(brick.__class__, "__orig_bases__"):
        for base in brick.__class__.__orig_bases__:
            if hasattr(base, "__args__"):
                args = base.__args__
                if len(args) >= 3:
                    metadata.input_type = str(args[0])
                    metadata.output_type = str(args[1])
                    metadata.deps_type = str(args[2])

    # Create package with source file
    files = []
    source_path = Path(source_file)

    # Add the source file
    files.append(PackageFile.from_file(source_path.parent, source_path))

    # Add __init__.py if it exists
    init_path = source_path.parent / "__init__.py"
    if init_path.exists():
        files.append(PackageFile.from_file(source_path.parent, init_path))

    return Package(metadata=metadata, files=files)


__all__ = [
    "PackageMetadata",
    "PackageFile",
    "Package",
    "create_package_from_brick",
]
