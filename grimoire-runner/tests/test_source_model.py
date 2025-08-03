"""
Tests for source definition models.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.models.source import SourceDefinition


class TestSourceDefinition:
    """Test the SourceDefinition model."""

    def test_source_initialization_minimal(self):
        """Test source initialization with minimal parameters."""
        source = SourceDefinition(kind="source", name="Test Source")

        assert source.kind == "source"
        assert source.name == "Test Source"
        assert source.id is None
        assert source.display_name is None
        assert source.edition is None
        assert source.default is None
        assert source.publisher is None
        assert source.description is None
        assert source.source_url is None
        assert source.version == "1.0"

    def test_source_initialization_full(self):
        """Test source initialization with all parameters."""
        source = SourceDefinition(
            kind="source",
            name="Player's Handbook",
            id="phb",
            display_name="Player's Handbook (5th Edition)",
            edition="5e",
            default=True,
            publisher="Wizards of the Coast",
            description="Core rulebook for D&D 5th Edition",
            source_url="https://example.com/phb",
            version="2.0"
        )

        assert source.kind == "source"
        assert source.name == "Player's Handbook"
        assert source.id == "phb"
        assert source.display_name == "Player's Handbook (5th Edition)"
        assert source.edition == "5e"
        assert source.default is True
        assert source.publisher == "Wizards of the Coast"
        assert source.description == "Core rulebook for D&D 5th Edition"
        assert source.source_url == "https://example.com/phb"
        assert source.version == "2.0"

    def test_source_validate_valid(self):
        """Test validation of a valid source."""
        source = SourceDefinition(kind="source", name="Valid Source")

        errors = source.validate()
        assert errors == []

    def test_source_validate_wrong_kind(self):
        """Test validation with wrong kind."""
        source = SourceDefinition(kind="wrong", name="Test Source")

        errors = source.validate()
        assert len(errors) == 1
        assert "kind must be 'source'" in errors[0]

    def test_source_validate_missing_name(self):
        """Test validation with missing name."""
        source = SourceDefinition(kind="source", name="")

        errors = source.validate()
        assert len(errors) == 1
        assert "name is required" in errors[0]

    def test_source_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        source = SourceDefinition(kind="wrong", name="")

        errors = source.validate()
        assert len(errors) == 2
        assert any("kind must be 'source'" in error for error in errors)
        assert any("name is required" in error for error in errors)

    def test_source_default_flag_true(self):
        """Test source with default flag set to True."""
        source = SourceDefinition(
            kind="source",
            name="Core Rules",
            default=True
        )

        assert source.default is True

    def test_source_default_flag_false(self):
        """Test source with default flag set to False."""
        source = SourceDefinition(
            kind="source",
            name="Optional Rules",
            default=False
        )

        assert source.default is False

    def test_source_with_url(self):
        """Test source with URL."""
        source = SourceDefinition(
            kind="source",
            name="Online Reference",
            source_url="https://example.com/rules"
        )

        assert source.source_url == "https://example.com/rules"

    def test_source_with_publisher(self):
        """Test source with publisher information."""
        source = SourceDefinition(
            kind="source",
            name="Third Party Content",
            publisher="Indie Game Studio"
        )

        assert source.publisher == "Indie Game Studio"

    def test_source_with_edition(self):
        """Test source with edition information."""
        source = SourceDefinition(
            kind="source",
            name="Game Rules",
            edition="6th Edition"
        )

        assert source.edition == "6th Edition"

    def test_source_with_description(self):
        """Test source with description."""
        source = SourceDefinition(
            kind="source",
            name="Expansion Pack",
            description="Additional rules and content for advanced play"
        )

        assert source.description == "Additional rules and content for advanced play"

    def test_source_custom_version(self):
        """Test source with custom version."""
        source = SourceDefinition(
            kind="source",
            name="Beta Rules",
            version="0.5-beta"
        )

        assert source.version == "0.5-beta"


class TestSourceDefinitionComplexScenarios:
    """Test complex source definition scenarios."""

    def test_source_game_sourcebook_example(self):
        """Test a realistic game sourcebook source."""
        source = SourceDefinition(
            kind="source",
            name="Monster Manual",
            id="mm",
            display_name="Monster Manual (5th Edition)",
            edition="5e",
            default=False,
            publisher="Wizards of the Coast",
            description="Bestiary containing hundreds of creatures for D&D campaigns",
            source_url="https://dnd.wizards.com/products/monster-manual",
            version="1.0"
        )

        errors = source.validate()
        assert errors == []

        assert source.name == "Monster Manual"
        assert source.id == "mm"
        assert source.default is False
        assert "creatures" in source.description

    def test_source_homebrew_content_example(self):
        """Test a homebrew content source."""
        source = SourceDefinition(
            kind="source",
            name="Custom Campaign Rules",
            id="homebrew_001",
            edition="5e",
            default=False,
            publisher="DM John Smith",
            description="House rules and custom content for the Shadowfall campaign"
        )

        errors = source.validate()
        assert errors == []

        assert source.publisher == "DM John Smith"
        assert "Shadowfall" in source.description

    def test_source_online_resource_example(self):
        """Test an online resource source."""
        source = SourceDefinition(
            kind="source",
            name="SRD Online",
            id="srd_online",
            display_name="System Reference Document (Online)",
            default=True,
            description="Free online reference for core game rules",
            source_url="https://dnd5e.wikidot.com/srd"
        )

        errors = source.validate()
        assert errors == []

        assert source.default is True
        assert source.source_url.startswith("https://")

    def test_source_unicode_support(self):
        """Test source with unicode characters."""
        source = SourceDefinition(
            kind="source",
            name="Règles Françaises",
            publisher="Éditeur International",
            description="Règles de jeu en français avec caractères spéciaux: ñáéíóú 中文"
        )

        errors = source.validate()
        assert errors == []

        assert "Françaises" in source.name
        assert "中文" in source.description


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
