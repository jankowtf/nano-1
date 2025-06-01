"""Version management for nanobrick packages."""

import re
from dataclasses import dataclass
from enum import Enum


class VersionPart(Enum):
    """Parts of a semantic version."""

    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"
    PRERELEASE = "prerelease"
    BUILD = "build"


@dataclass
class Version:
    """Semantic version representation."""

    major: int
    minor: int
    patch: int
    prerelease: str | None = None
    build: str | None = None

    # Regex for parsing semantic versions
    VERSION_PATTERN = re.compile(
        r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
        r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    )

    def __str__(self) -> str:
        """String representation."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Version({str(self)})"

    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """Parse version string."""
        match = cls.VERSION_PATTERN.match(version_string)
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")

        groups = match.groupdict()
        return cls(
            major=int(groups["major"]),
            minor=int(groups["minor"]),
            patch=int(groups["patch"]),
            prerelease=groups.get("prerelease"),
            build=groups.get("build"),
        )

    def bump(self, part: VersionPart) -> "Version":
        """Bump version part."""
        if part == VersionPart.MAJOR:
            return Version(self.major + 1, 0, 0)
        elif part == VersionPart.MINOR:
            return Version(self.major, self.minor + 1, 0)
        elif part == VersionPart.PATCH:
            return Version(self.major, self.minor, self.patch + 1)
        else:
            raise ValueError(f"Cannot bump {part}")

    def is_prerelease(self) -> bool:
        """Check if this is a prerelease version."""
        return self.prerelease is not None

    def _compare_prerelease(self, other: "Version") -> int:
        """Compare prerelease versions."""
        # No prerelease is greater than any prerelease
        if self.prerelease is None and other.prerelease is not None:
            return 1
        if self.prerelease is not None and other.prerelease is None:
            return -1
        if self.prerelease is None and other.prerelease is None:
            return 0

        # Compare prerelease parts
        self_parts = self.prerelease.split(".")
        other_parts = other.prerelease.split(".")

        for i in range(max(len(self_parts), len(other_parts))):
            if i >= len(self_parts):
                return -1
            if i >= len(other_parts):
                return 1

            self_part = self_parts[i]
            other_part = other_parts[i]

            # Numeric comparison if both are numeric
            if self_part.isdigit() and other_part.isdigit():
                result = int(self_part) - int(other_part)
                if result != 0:
                    return result
            else:
                # Lexical comparison
                if self_part < other_part:
                    return -1
                elif self_part > other_part:
                    return 1

        return 0

    def __lt__(self, other: "Version") -> bool:
        """Less than comparison."""
        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        ):
            return True
        if (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        ):
            return False

        # Same version, compare prerelease
        return self._compare_prerelease(other) < 0

    def __le__(self, other: "Version") -> bool:
        """Less than or equal comparison."""
        return self < other or self == other

    def __gt__(self, other: "Version") -> bool:
        """Greater than comparison."""
        return not self <= other

    def __ge__(self, other: "Version") -> bool:
        """Greater than or equal comparison."""
        return not self < other

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Version):
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
            and self.build == other.build
        )

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.major, self.minor, self.patch, self.prerelease, self.build))


@dataclass
class VersionRange:
    """Version range specification."""

    min_version: Version | None = None
    max_version: Version | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True

    def contains(self, version: Version) -> bool:
        """Check if version is in range."""
        if self.min_version:
            if self.min_inclusive:
                if version < self.min_version:
                    return False
            else:
                if version <= self.min_version:
                    return False

        if self.max_version:
            if self.max_inclusive:
                if version > self.max_version:
                    return False
            else:
                if version >= self.max_version:
                    return False

        return True

    @classmethod
    def parse(cls, spec: str) -> "VersionRange":
        """Parse version range specification.

        Examples:
            ">=1.0.0" - At least 1.0.0
            "^1.0.0" - Compatible with 1.0.0 (>=1.0.0, <2.0.0)
            "~1.2.0" - Approximately 1.2.0 (>=1.2.0, <1.3.0)
            ">1.0.0,<2.0.0" - Between 1.0.0 and 2.0.0
        """
        # Handle caret (^) - compatible versions
        if spec.startswith("^"):
            base = Version.parse(spec[1:])
            return cls(
                min_version=base,
                max_version=Version(base.major + 1, 0, 0),
                min_inclusive=True,
                max_inclusive=False,
            )

        # Handle tilde (~) - approximately equal
        if spec.startswith("~"):
            base = Version.parse(spec[1:])
            return cls(
                min_version=base,
                max_version=Version(base.major, base.minor + 1, 0),
                min_inclusive=True,
                max_inclusive=False,
            )

        # Handle compound specifications
        if "," in spec:
            parts = spec.split(",")
            range_obj = cls()

            for part in parts:
                part = part.strip()
                if part.startswith(">="):
                    range_obj.min_version = Version.parse(part[2:])
                    range_obj.min_inclusive = True
                elif part.startswith(">"):
                    range_obj.min_version = Version.parse(part[1:])
                    range_obj.min_inclusive = False
                elif part.startswith("<="):
                    range_obj.max_version = Version.parse(part[2:])
                    range_obj.max_inclusive = True
                elif part.startswith("<"):
                    range_obj.max_version = Version.parse(part[1:])
                    range_obj.max_inclusive = False
                elif part.startswith("=="):
                    version = Version.parse(part[2:])
                    range_obj.min_version = version
                    range_obj.max_version = version
                    range_obj.min_inclusive = True
                    range_obj.max_inclusive = True

            return range_obj

        # Handle single specifications
        if spec.startswith(">="):
            return cls(
                min_version=Version.parse(spec[2:]),
                min_inclusive=True,
            )
        elif spec.startswith(">"):
            return cls(
                min_version=Version.parse(spec[1:]),
                min_inclusive=False,
            )
        elif spec.startswith("<="):
            return cls(
                max_version=Version.parse(spec[2:]),
                max_inclusive=True,
            )
        elif spec.startswith("<"):
            return cls(
                max_version=Version.parse(spec[1:]),
                max_inclusive=False,
            )
        elif spec.startswith("=="):
            version = Version.parse(spec[2:])
            return cls(
                min_version=version,
                max_version=version,
                min_inclusive=True,
                max_inclusive=True,
            )
        else:
            # Assume exact version
            version = Version.parse(spec)
            return cls(
                min_version=version,
                max_version=version,
                min_inclusive=True,
                max_inclusive=True,
            )

    def __str__(self) -> str:
        """String representation."""
        if (
            self.min_version
            and self.max_version
            and self.min_version == self.max_version
        ):
            return f"=={self.min_version}"

        parts = []
        if self.min_version:
            op = ">=" if self.min_inclusive else ">"
            parts.append(f"{op}{self.min_version}")
        if self.max_version:
            op = "<=" if self.max_inclusive else "<"
            parts.append(f"{op}{self.max_version}")

        return ",".join(parts)


def find_best_version(
    available: list[Version],
    constraint: VersionRange,
    prefer_stable: bool = True,
) -> Version | None:
    """Find the best version matching constraints.

    Args:
        available: List of available versions
        constraint: Version range constraint
        prefer_stable: Prefer stable over prerelease versions

    Returns:
        Best matching version or None
    """
    # Filter matching versions
    matching = [v for v in available if constraint.contains(v)]

    if not matching:
        return None

    # Sort by version (highest first)
    matching.sort(reverse=True)

    # Prefer stable versions if requested
    if prefer_stable:
        stable = [v for v in matching if not v.is_prerelease()]
        if stable:
            return stable[0]

    return matching[0]


def resolve_dependencies(
    dependencies: dict[str, str],
    available_packages: dict[str, list[Version]],
) -> dict[str, Version]:
    """Simple dependency resolver.

    Args:
        dependencies: Package name to version constraint mapping
        available_packages: Package name to available versions mapping

    Returns:
        Resolved package name to version mapping

    Raises:
        ValueError: If dependencies cannot be resolved
    """
    resolved = {}

    for package, constraint_str in dependencies.items():
        if package not in available_packages:
            raise ValueError(f"Package not found: {package}")

        constraint = VersionRange.parse(constraint_str)
        available = available_packages[package]

        best_version = find_best_version(available, constraint)
        if not best_version:
            raise ValueError(
                f"No version of {package} satisfies constraint {constraint_str}"
            )

        resolved[package] = best_version

    return resolved


__all__ = [
    "Version",
    "VersionPart",
    "VersionRange",
    "find_best_version",
    "resolve_dependencies",
]
