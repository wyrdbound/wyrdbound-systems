"""
Test configuration and fixtures for the new GRIMOIRE test suite.

This module provides common fixtures and utilities for testing GRIMOIRE components
in isolation using minimal test systems.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def temp_system_dir():
    """Create a temporary directory for test systems."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_systems_dir():
    """Path to the test systems directory."""
    return Path(__file__).parent / "systems"


def create_yaml_file(directory: Path, filename: str, content: dict[str, Any]) -> Path:
    """Helper function to create a YAML file in a directory."""
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename
    with open(file_path, "w") as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False)
    return file_path


def load_yaml_file(file_path: Path) -> dict[str, Any]:
    """Helper function to load and parse a YAML file."""
    with open(file_path) as f:
        return yaml.safe_load(f)


class SystemBuilder:
    """Builder class for creating test systems programmatically."""

    def __init__(self, system_id: str, base_dir: Path):
        self.system_id = system_id
        self.base_dir = base_dir
        self.system_dir = base_dir / system_id
        self.system_def = {
            "id": system_id,
            "kind": "system",
            "name": f"Test System: {system_id}",
            "version": "1.0",
        }

    def with_description(self, description: str):
        """Add a description to the system."""
        self.system_def["description"] = description
        return self

    def with_currency(self, base_unit: str, denominations: dict[str, Any]):
        """Add currency system to the system."""
        self.system_def["currency"] = {
            "base_unit": base_unit,
            "denominations": denominations,
        }
        return self

    def with_credits(self, **credits):
        """Add credits information to the system."""
        self.system_def["credits"] = credits
        return self

    def with_default_source(self, source_id: str):
        """Add default source reference."""
        self.system_def["default_source"] = source_id
        return self

    def build(self) -> Path:
        """Create the system files and return the system directory path."""
        create_yaml_file(self.system_dir, "system.yaml", self.system_def)
        return self.system_dir


@pytest.fixture
def system_builder(temp_system_dir):
    """Factory fixture for creating test systems."""

    def _builder(system_id: str) -> SystemBuilder:
        return SystemBuilder(system_id, temp_system_dir)

    return _builder
