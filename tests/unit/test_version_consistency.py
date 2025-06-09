"""Test version consistency across the project."""

import re
from pathlib import Path

import pytest


def get_version_from_pyproject():
    """Extract version from pyproject.toml."""
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    content = pyproject_path.read_text()
    match = re.search(r'^version = "([0-9]+\.[0-9]+\.[0-9]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Version not found in pyproject.toml")


def get_version_from_init():
    """Extract version from __init__.py."""
    init_path = Path(__file__).parent.parent.parent / "src" / "nanobricks" / "__init__.py"
    content = init_path.read_text()
    match = re.search(r'^__version__ = "([0-9]+\.[0-9]+\.[0-9]+)"', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise ValueError("Version not found in __init__.py")


def test_version_consistency():
    """Test that versions are consistent across all files."""
    pyproject_version = get_version_from_pyproject()
    init_version = get_version_from_init()
    
    assert pyproject_version == init_version, (
        f"Version mismatch: pyproject.toml has {pyproject_version}, "
        f"but __init__.py has {init_version}"
    )


def test_version_format():
    """Test that version follows semantic versioning format."""
    version = get_version_from_pyproject()
    
    # Check format: MAJOR.MINOR.PATCH
    pattern = re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
    assert pattern.match(version), f"Version {version} does not follow semantic versioning"
    
    # Parse version components
    major, minor, patch = map(int, version.split('.'))
    
    # All components should be non-negative
    assert major >= 0, f"Major version cannot be negative: {major}"
    assert minor >= 0, f"Minor version cannot be negative: {minor}"
    assert patch >= 0, f"Patch version cannot be negative: {patch}"


def test_version_is_reset():
    """Test that version has been reset to 0.1.0."""
    version = get_version_from_pyproject()
    
    # After reset, version should be 0.1.0
    assert version == "0.1.0", (
        f"Expected version 0.1.0 after reset, but got {version}. "
        "If this is intentional, update this test."
    )


def test_no_dev_versions():
    """Test that we don't have development version suffixes."""
    version = get_version_from_pyproject()
    
    # Should not contain dev, alpha, beta, rc suffixes
    assert "dev" not in version, "Development versions should not be in pyproject.toml"
    assert "alpha" not in version, "Alpha versions should not be in pyproject.toml"
    assert "beta" not in version, "Beta versions should not be in pyproject.toml"
    assert "rc" not in version, "Release candidate versions should not be in pyproject.toml"


def test_changelog_version_reference():
    """Test that CHANGELOG.md references are consistent."""
    changelog_path = Path(__file__).parent.parent.parent / "CHANGELOG.md"
    if not changelog_path.exists():
        pytest.skip("CHANGELOG.md not found")
    
    content = changelog_path.read_text()
    current_version = get_version_from_pyproject()
    
    # Check if current version is mentioned (might be in Unreleased section)
    # This is a soft check - we mainly want to ensure no wrong versions
    version_pattern = re.compile(r'\[([0-9]+\.[0-9]+\.[0-9]+)\]')
    versions_in_changelog = version_pattern.findall(content)
    
    # If we find version references higher than current, that's suspicious
    for found_version in versions_in_changelog:
        found_parts = list(map(int, found_version.split('.')))
        current_parts = list(map(int, current_version.split('.')))
        
        # Compare versions
        if found_parts > current_parts:
            pytest.fail(
                f"CHANGELOG.md contains version {found_version} which is higher "
                f"than current version {current_version}. This might indicate "
                f"the version reset was not properly reflected in documentation."
            )


if __name__ == "__main__":
    # Allow running directly for debugging
    test_version_consistency()
    test_version_format()
    test_version_is_reset()
    test_no_dev_versions()
    test_changelog_version_reference()
    print("✅ All version consistency tests passed!")