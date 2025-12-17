#!/usr/bin/env python3
"""
Simple prompt version management system for AI agent prompts.

This module provides a file-based versioning system for managing different
versions of system prompts, allowing easy switching, rollback, and comparison
of prompt performance.
"""

import importlib.util
import re
from pathlib import Path
from typing import Dict, List, Optional


class PromptManager:
    """Manages prompt versions using simple file-based storage."""

    def __init__(self, prompts_dir: str = "prompts/"):
        """
        Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing prompt versions and configuration
        """
        self.prompts_dir = Path(prompts_dir)
        self.versions_dir = self.prompts_dir / "versions"
        self.active_version_file = self.prompts_dir / "active_version.txt"

        # Create directories if they don't exist
        self.prompts_dir.mkdir(exist_ok=True)
        self.versions_dir.mkdir(exist_ok=True)

        # Cache for loaded prompts
        self._prompt_cache: Dict[str, str] = {}

        # Get active version
        self.active_version = self._read_active_version()

    def _read_active_version(self) -> str:
        """
        Read the currently active prompt version.

        Returns:
            The active version string (e.g., "v1.0.0")
        """
        if self.active_version_file.exists():
            return self.active_version_file.read_text().strip()

        # Default to first available version or v1.0.0
        versions = self.list_versions()
        return versions[0] if versions else "v1.0.0"

    def get_prompt(self, version: Optional[str] = None) -> str:
        """
        Get the system prompt for a specific version.

        Args:
            version: Version to retrieve (defaults to active version)

        Returns:
            The system prompt text

        Raises:
            FileNotFoundError: If the specified version doesn't exist
            ImportError: If the prompt file is malformed
        """
        version = version or self.active_version

        # Check cache first
        if version in self._prompt_cache:
            return self._prompt_cache[version]

        # Load prompt from file
        prompt_file = self.versions_dir / f"{version}.py"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt version {version} not found at {prompt_file}")

        # Import the module and extract SYSTEM_PROMPT_BASE
        spec = importlib.util.spec_from_file_location(f"prompt_{version}", prompt_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load prompt module from {prompt_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "SYSTEM_PROMPT_BASE"):
            raise ImportError(f"Prompt file {prompt_file} missing SYSTEM_PROMPT_BASE")

        prompt = module.SYSTEM_PROMPT_BASE

        # Cache the loaded prompt
        self._prompt_cache[version] = prompt

        return prompt

    def get_prompt_with_schema(self, schema_info: str, version: Optional[str] = None) -> str:
        """
        Get the system prompt with schema information injected.

        Args:
            schema_info: Database schema information to inject
            version: Version to retrieve (defaults to active version)

        Returns:
            The formatted system prompt with schema
        """
        prompt = self.get_prompt(version)
        return prompt.format(schema_info=schema_info)

    def set_active_version(self, version: str) -> None:
        """
        Set the active prompt version.

        Args:
            version: Version to activate

        Raises:
            ValueError: If the version doesn't exist
        """
        if version not in self.list_versions():
            raise ValueError(f"Version {version} does not exist")

        self.active_version_file.write_text(version)
        self.active_version = version

        # Clear cache when switching versions
        self._prompt_cache.clear()

    def list_versions(self) -> List[str]:
        """
        List all available prompt versions.

        Returns:
            Sorted list of version strings
        """
        versions = []

        for file in self.versions_dir.glob("v*.py"):
            # Extract version from filename (e.g., v1.0.0.py -> v1.0.0)
            version = file.stem
            if re.match(r"^v\d+\.\d+\.\d+$", version):
                versions.append(version)

        return sorted(versions, key=self._version_key)

    def _version_key(self, version: str) -> tuple:
        """
        Create a sortable key from version string.

        Args:
            version: Version string (e.g., "v1.2.10")

        Returns:
            Tuple of integers for sorting
        """
        # Remove 'v' prefix and split by dots
        parts = version[1:].split(".")
        return tuple(int(part) for part in parts)

    def get_version_info(self, version: Optional[str] = None) -> Dict[str, str]:
        """
        Get metadata about a prompt version.

        Args:
            version: Version to query (defaults to active version)

        Returns:
            Dictionary with version metadata
        """
        version = version or self.active_version
        prompt_file = self.versions_dir / f"{version}.py"

        if not prompt_file.exists():
            return {"error": f"Version {version} not found"}

        # Import module to get metadata
        spec = importlib.util.spec_from_file_location(f"prompt_{version}", prompt_file)
        if spec is None or spec.loader is None:
            return {"error": f"Could not load version {version}"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        info = {
            "version": getattr(module, "VERSION", version),
            "release_date": getattr(module, "RELEASE_DATE", "Unknown"),
            "author": getattr(module, "AUTHOR", "Unknown"),
            "status": getattr(module, "STATUS", "Unknown"),
            "description": getattr(module, "DESCRIPTION", "No description"),
        }

        return info

    def get_previous_version(self) -> Optional[str]:
        """
        Get the version before the currently active one.

        Returns:
            Previous version string or None if at first version
        """
        versions = self.list_versions()

        if not versions or self.active_version not in versions:
            return None

        current_index = versions.index(self.active_version)

        if current_index > 0:
            return versions[current_index - 1]

        return None

    def rollback(self) -> Optional[str]:
        """
        Rollback to the previous prompt version.

        Returns:
            The version rolled back to, or None if cannot rollback
        """
        previous = self.get_previous_version()

        if previous:
            self.set_active_version(previous)
            return previous

        return None

    def create_version(self, version: str, prompt_content: str, author: str = "Unknown", description: str = "") -> None:
        """
        Create a new prompt version.

        Args:
            version: Version string (e.g., "v1.1.0")
            prompt_content: The system prompt content
            author: Author of the changes
            description: Description of changes
        """
        if not re.match(r"^v\d+\.\d+\.\d+$", version):
            raise ValueError(f"Invalid version format: {version}. Use vX.Y.Z")

        prompt_file = self.versions_dir / f"{version}.py"

        if prompt_file.exists():
            raise ValueError(f"Version {version} already exists")

        from datetime import date

        content = f'''#!/usr/bin/env python3
"""
Prompt Version {version[1:]}
Released: {date.today().isoformat()}
Author: {author}
Status: draft

{description}
"""

# Base system prompt template
SYSTEM_PROMPT_BASE = """{prompt_content}"""

# Version metadata
VERSION = "{version[1:]}"
RELEASE_DATE = "{date.today().isoformat()}"
AUTHOR = "{author}"
STATUS = "draft"
DESCRIPTION = "{description}"
'''

        prompt_file.write_text(content)

        # Clear cache
        self._prompt_cache.clear()
