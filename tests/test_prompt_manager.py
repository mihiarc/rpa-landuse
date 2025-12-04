#!/usr/bin/env python3
"""Tests for the prompt versioning system."""

import tempfile
from pathlib import Path

import pytest

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompts.prompt_manager import PromptManager


def test_prompt_manager_initialization():
    """Test that PromptManager initializes correctly."""
    manager = PromptManager()

    assert manager.prompts_dir == Path("prompts/")
    assert manager.active_version == "v1.0.1"
    assert manager.versions_dir.exists()


def test_list_versions():
    """Test listing available versions."""
    manager = PromptManager()
    versions = manager.list_versions()

    assert "v1.0.0" in versions
    assert len(versions) >= 1


def test_get_prompt():
    """Test retrieving a prompt."""
    manager = PromptManager()

    # Get the active version prompt
    prompt = manager.get_prompt()

    assert "land use analytics expert" in prompt
    assert "RPA Assessment database" in prompt
    assert "{schema_info}" in prompt


def test_get_prompt_with_schema():
    """Test retrieving a prompt with schema injection."""
    manager = PromptManager()

    schema_info = "TEST_SCHEMA_INFO"
    prompt = manager.get_prompt_with_schema(schema_info)

    assert "land use analytics expert" in prompt
    assert "TEST_SCHEMA_INFO" in prompt
    assert "{schema_info}" not in prompt


def test_get_version_info():
    """Test retrieving version metadata."""
    manager = PromptManager()

    info = manager.get_version_info("v1.0.0")

    assert info["version"] == "1.0.0"
    assert info["release_date"] == "2025-09-28"
    assert info["author"] == "System"
    assert info["status"] == "production"


def test_version_sorting():
    """Test that versions are sorted correctly."""
    # Create a temporary prompts directory
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        versions_dir = prompts_dir / "versions"
        versions_dir.mkdir(parents=True)

        # Create test version files
        test_versions = ["v1.0.0", "v1.10.0", "v1.2.0", "v2.0.0", "v1.0.10"]
        for version in test_versions:
            (versions_dir / f"{version}.py").write_text(
                f'SYSTEM_PROMPT_BASE = "Test prompt for {version}"'
            )

        # Create active version file
        (prompts_dir / "active_version.txt").write_text("v1.0.0")

        manager = PromptManager(str(prompts_dir))
        versions = manager.list_versions()

        # Check sorting is correct (semantic versioning)
        expected_order = ["v1.0.0", "v1.0.10", "v1.2.0", "v1.10.0", "v2.0.0"]
        assert versions == expected_order


def test_set_active_version():
    """Test setting the active version."""
    # Use a temporary directory to avoid modifying real files
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        versions_dir = prompts_dir / "versions"
        versions_dir.mkdir(parents=True)

        # Create test versions
        (versions_dir / "v1.0.0.py").write_text('SYSTEM_PROMPT_BASE = "Version 1.0.0"')
        (versions_dir / "v1.1.0.py").write_text('SYSTEM_PROMPT_BASE = "Version 1.1.0"')

        # Create active version file
        active_file = prompts_dir / "active_version.txt"
        active_file.write_text("v1.0.0")

        manager = PromptManager(str(prompts_dir))

        # Check initial state
        assert manager.active_version == "v1.0.0"

        # Set new active version
        manager.set_active_version("v1.1.0")

        assert manager.active_version == "v1.1.0"
        assert active_file.read_text() == "v1.1.0"

        # Try to set non-existent version
        with pytest.raises(ValueError):
            manager.set_active_version("v99.0.0")


def test_create_version():
    """Test creating a new version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        versions_dir = prompts_dir / "versions"
        versions_dir.mkdir(parents=True)

        manager = PromptManager(str(prompts_dir))

        # Create a new version
        manager.create_version(
            version="v1.1.0",
            prompt_content="This is a test prompt",
            author="Test Author",
            description="Test version for unit tests"
        )

        # Check the version was created
        assert "v1.1.0" in manager.list_versions()

        # Check the content
        prompt = manager.get_prompt("v1.1.0")
        assert "This is a test prompt" == prompt

        # Check metadata
        info = manager.get_version_info("v1.1.0")
        assert info["author"] == "Test Author"

        # Try to create duplicate version
        with pytest.raises(ValueError):
            manager.create_version("v1.1.0", "Duplicate", "Author", "Description")


def test_rollback():
    """Test rolling back to previous version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"
        versions_dir = prompts_dir / "versions"
        versions_dir.mkdir(parents=True)

        # Create test versions
        (versions_dir / "v1.0.0.py").write_text('SYSTEM_PROMPT_BASE = "Version 1.0.0"')
        (versions_dir / "v1.1.0.py").write_text('SYSTEM_PROMPT_BASE = "Version 1.1.0"')
        (versions_dir / "v1.2.0.py").write_text('SYSTEM_PROMPT_BASE = "Version 1.2.0"')

        # Set active to v1.2.0
        (prompts_dir / "active_version.txt").write_text("v1.2.0")

        manager = PromptManager(str(prompts_dir))

        # Check initial state
        assert manager.active_version == "v1.2.0"

        # Rollback once
        previous = manager.rollback()
        assert previous == "v1.1.0"
        assert manager.active_version == "v1.1.0"

        # Rollback again
        previous = manager.rollback()
        assert previous == "v1.0.0"
        assert manager.active_version == "v1.0.0"

        # Try to rollback when at first version
        previous = manager.rollback()
        assert previous is None
        assert manager.active_version == "v1.0.0"


def test_cache_functionality():
    """Test that prompts are cached correctly."""
    manager = PromptManager()

    # First call should load from file
    prompt1 = manager.get_prompt("v1.0.0")

    # Second call should use cache (we can't directly test this, but ensure consistency)
    prompt2 = manager.get_prompt("v1.0.0")

    assert prompt1 == prompt2

    # Changing active version should clear cache
    if len(manager.list_versions()) > 1:
        manager.set_active_version(manager.list_versions()[1])
        # Cache should be cleared, but we can't directly test this


if __name__ == "__main__":
    pytest.main([__file__, "-v"])