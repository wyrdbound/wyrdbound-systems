"""
Tests for compendium definition models.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.models.compendium import CompendiumDefinition


class TestCompendiumDefinition:
    """Test the CompendiumDefinition model."""

    def setup_method(self):
        """Set up test fixtures."""
        self.sample_entries = {
            "sword": {
                "name": "Iron Sword",
                "type": "weapon",
                "damage": "1d8",
                "description": "A sturdy iron blade",
                "tags": ["metal", "melee"],
            },
            "potion": {
                "name": "Healing Potion",
                "type": "consumable",
                "effect": "Restores 2d4+2 hit points",
                "description": "A red liquid that glows softly",
                "rarity": "common",
                "tags": ["healing", "magic"],
            },
            "staff": {
                "name": "Wizard's Staff",
                "type": "weapon",
                "damage": "1d6",
                "description": "A gnarled wooden staff with crystal tip",
                "properties": {
                    "magical": True,
                    "spell_focus": True,
                    "material": "oak"
                },
                "tags": ["magic", "wood"],
            }
        }

        self.compendium = CompendiumDefinition(
            kind="compendium",
            id="items",
            name="Items Compendium",
            model="Item",
            entries=self.sample_entries.copy()
        )

    def test_initialization(self):
        """Test compendium initialization."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test Compendium",
            model="TestModel"
        )

        assert comp.kind == "compendium"
        assert comp.id == "test"
        assert comp.name == "Test Compendium"
        assert comp.model == "TestModel"
        assert comp.entries == {}

    def test_initialization_with_entries(self):
        """Test compendium initialization with entries."""
        entries = {"item1": {"name": "Test Item"}}
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test Compendium",
            model="TestModel",
            entries=entries
        )

        assert comp.entries == entries

    def test_get_entry_existing(self):
        """Test getting an existing entry."""
        entry = self.compendium.get_entry("sword")

        assert entry is not None
        assert entry["name"] == "Iron Sword"
        assert entry["type"] == "weapon"

    def test_get_entry_nonexistent(self):
        """Test getting a non-existent entry."""
        entry = self.compendium.get_entry("nonexistent")

        assert entry is None

    def test_list_entries(self):
        """Test listing all entry IDs."""
        entries = self.compendium.list_entries()

        assert sorted(entries) == ["potion", "staff", "sword"]

    def test_list_entries_empty(self):
        """Test listing entries when compendium is empty."""
        empty_comp = CompendiumDefinition(
            kind="compendium",
            id="empty",
            name="Empty Compendium",
            model="TestModel"
        )

        entries = empty_comp.list_entries()
        assert entries == []

    def test_filter_entries_by_type(self):
        """Test filtering entries by type."""
        def weapon_filter(entry):
            return entry.get("type") == "weapon"
        weapons = self.compendium.filter_entries(weapon_filter)

        assert len(weapons) == 2
        assert "sword" in weapons
        assert "staff" in weapons
        assert "potion" not in weapons

    def test_filter_entries_by_tag(self):
        """Test filtering entries by tag."""
        def magic_filter(entry):
            return "magic" in entry.get("tags", [])
        magic_items = self.compendium.filter_entries(magic_filter)

        assert len(magic_items) == 2
        assert "potion" in magic_items
        assert "staff" in magic_items
        assert "sword" not in magic_items

    def test_filter_entries_complex(self):
        """Test filtering with complex criteria."""
        # Items that are weapons AND have magic tags
        def complex_filter(entry):
            return (
                    entry.get("type") == "weapon" and
                    "magic" in entry.get("tags", [])
                )
        filtered = self.compendium.filter_entries(complex_filter)

        assert len(filtered) == 1
        assert "staff" in filtered

    def test_filter_entries_none_match(self):
        """Test filtering when no entries match."""
        def no_match_filter(entry):
            return entry.get("type") == "armor"
        filtered = self.compendium.filter_entries(no_match_filter)

        assert filtered == {}

    def test_search_entries_simple_text(self):
        """Test searching for simple text."""
        results = self.compendium.search_entries("iron")

        assert len(results) == 1
        assert "sword" in results

    def test_search_entries_case_insensitive(self):
        """Test that search is case insensitive."""
        results = self.compendium.search_entries("HEALING")

        assert len(results) == 1
        assert "potion" in results

    def test_search_entries_in_description(self):
        """Test searching in description field."""
        results = self.compendium.search_entries("wooden")

        assert len(results) == 1
        assert "staff" in results

    def test_search_entries_in_nested_dict(self):
        """Test searching in nested dictionary values."""
        results = self.compendium.search_entries("oak")

        assert len(results) == 1
        assert "staff" in results

    def test_search_entries_in_list(self):
        """Test searching in list values."""
        results = self.compendium.search_entries("melee")

        assert len(results) == 1
        assert "sword" in results

    def test_search_entries_specific_fields(self):
        """Test searching in specific fields only."""
        # Search only in name field - should not find "wooden" from description
        results = self.compendium.search_entries("wooden", fields=["name"])
        assert len(results) == 0

        # Search only in description field
        results = self.compendium.search_entries("wooden", fields=["description"])
        assert len(results) == 1
        assert "staff" in results

    def test_search_entries_multiple_fields(self):
        """Test searching in multiple specific fields."""
        results = self.compendium.search_entries("magic", fields=["description", "tags"])

        # Should find both potion (tags) and staff (description mentions crystal, tags)
        assert len(results) == 2
        assert "potion" in results
        assert "staff" in results

    def test_search_entries_no_matches(self):
        """Test searching with no matches."""
        results = self.compendium.search_entries("nonexistent")

        assert results == {}

    def test_search_entries_empty_search_term(self):
        """Test searching with empty search term."""
        results = self.compendium.search_entries("")

        # Empty string should match everything
        assert len(results) == 3

    def test_search_entries_field_not_exists(self):
        """Test searching in fields that don't exist."""
        results = self.compendium.search_entries("anything", fields=["nonexistent_field"])

        assert results == {}

    def test_validate_valid_compendium(self):
        """Test validation of a valid compendium."""
        errors = self.compendium.validate()

        assert errors == []

    def test_validate_wrong_kind(self):
        """Test validation with wrong kind."""
        comp = CompendiumDefinition(
            kind="wrong",
            id="test",
            name="Test",
            model="TestModel",
            entries={"item": {"name": "test"}}
        )

        errors = comp.validate()
        assert len(errors) == 1
        assert "kind must be 'compendium'" in errors[0]

    def test_validate_missing_id(self):
        """Test validation with missing ID."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="",
            name="Test",
            model="TestModel",
            entries={"item": {"name": "test"}}
        )

        errors = comp.validate()
        assert len(errors) == 1
        assert "id is required" in errors[0]

    def test_validate_missing_name(self):
        """Test validation with missing name."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="",
            model="TestModel",
            entries={"item": {"name": "test"}}
        )

        errors = comp.validate()
        assert len(errors) == 1
        assert "name is required" in errors[0]

    def test_validate_missing_model(self):
        """Test validation with missing model."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test",
            model="",
            entries={"item": {"name": "test"}}
        )

        errors = comp.validate()
        assert len(errors) == 1
        assert "model is required" in errors[0]

    def test_validate_no_entries(self):
        """Test validation with no entries."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test",
            model="TestModel",
            entries={}
        )

        errors = comp.validate()
        assert len(errors) == 1
        assert "must have at least one entry" in errors[0]

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        comp = CompendiumDefinition(
            kind="wrong",
            id="",
            name="",
            model="",
            entries={}
        )

        errors = comp.validate()
        assert len(errors) == 5  # All validation errors


class TestCompendiumSearchBehavior:
    """Test specific search behavior edge cases."""

    def test_search_numeric_values(self):
        """Test searching in numeric values (should not match)."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test",
            model="TestModel",
            entries={
                "item1": {"name": "Item", "level": 5, "cost": 100}
            }
        )

        # Numeric values should not be searched
        results = comp.search_entries("5")
        assert results == {}

        results = comp.search_entries("100")
        assert results == {}

    def test_search_boolean_values(self):
        """Test searching in boolean values (should not match)."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test",
            model="TestModel",
            entries={
                "item1": {"name": "Item", "magical": True, "cursed": False}
            }
        )

        # Boolean values should not be searched
        results = comp.search_entries("true")
        assert results == {}

        results = comp.search_entries("false")
        assert results == {}

    def test_search_none_values(self):
        """Test searching with None values (should not match)."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test",
            model="TestModel",
            entries={
                "item1": {"name": "Item", "special": None}
            }
        )

        # None values should not cause errors
        results = comp.search_entries("none")
        assert results == {}

    def test_search_deeply_nested_structures(self):
        """Test searching in deeply nested structures."""
        comp = CompendiumDefinition(
            kind="compendium",
            id="test",
            name="Test",
            model="TestModel",
            entries={
                "item1": {
                    "name": "Complex Item",
                    "properties": {
                        "magical": {
                            "school": "evocation",
                            "effects": ["fire", "lightning"]
                        },
                        "physical": {
                            "material": "adamantine",
                            "weight": 5
                        }
                    }
                }
            }
        )

        # Should find text in deeply nested structures
        results = comp.search_entries("evocation")
        assert len(results) == 1
        assert "item1" in results

        results = comp.search_entries("adamantine")
        assert len(results) == 1
        assert "item1" in results

        results = comp.search_entries("lightning")
        assert len(results) == 1
        assert "item1" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
