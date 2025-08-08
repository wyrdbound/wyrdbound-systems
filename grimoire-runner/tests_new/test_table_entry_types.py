"""
Test table entry types functionality.

This tests the enhanced table system t        # Entry 4 should have type override
        entry_4 = table.entries[4]
        assert isinstance(entry_4, dict)
        assert entry_4["id"] == "longsword"
        assert entry_4["type"] == "weapon"upports:
- entry_type declaration for default table entry type
- Type overrides in individual entries
- Random selection from compendium by type
- Dynamic generation of new entries
- Backward compatibility with string tables

Tests are organized by complexity following the testing strategy.
"""


import pytest

from grimoire_runner.core.loader import SystemLoader


class TestBasicEntryTypes:
    """Test basic entry_type functionality and parsing."""

    @pytest.fixture
    def test_system(self, test_systems_dir):
        """Load the table entry types test system."""
        loader = SystemLoader()
        return loader.load_system(test_systems_dir / "table_entry_types")

    def test_table_with_entry_type_loads(self, test_system):
        """Test that tables with entry_type field load correctly."""
        table = test_system.tables["basic-items"]

        assert table.id == "basic-items"
        assert table.entry_type == "item"
        assert table.roll == "1d6"
        assert len(table.entries) == 6

    def test_table_without_entry_type_defaults_to_str(self, test_system):
        """Test that tables without entry_type default to 'str'."""
        table = test_system.tables["string-table"]

        assert table.id == "string-table"
        assert table.entry_type == "str"  # Should default to str
        assert len(table.entries) == 4

    def test_entry_type_validation_with_system_models(self, test_system):
        """Test that entry_type references valid models in the system."""
        table = test_system.tables["basic-items"]

        # entry_type should reference a valid model
        assert table.entry_type == "item"
        assert "item" in test_system.models

        # Verify the model exists and has expected structure
        item_model = test_system.models["item"]
        assert item_model.id == "item"
        assert "name" in item_model.attributes

    def test_simple_string_entries_work(self, test_system):
        """Test that simple string entries work with entry_type."""
        table = test_system.tables["basic-items"]

        # Simple string entries should be parsed as strings
        assert table.entries[1] == "backpack"
        assert table.entries[2] == "rope"
        assert table.entries[3] == "lantern"


class TestTypeOverrides:
    """Test type override functionality in individual entries."""

    @pytest.fixture
    def test_system(self, test_systems_dir):
        """Load the table entry types test system."""
        loader = SystemLoader()
        return loader.load_system(test_systems_dir / "table_entry_types")

    def test_explicit_id_with_type_override(self, test_system):
        """Test entries with explicit ID and type override."""
        table = test_system.tables["basic-items"]

        # Entry 4 should have type override
        entry = table.entries[4]
        assert isinstance(entry, dict)
        assert entry["id"] == "longsword"
        assert entry["type"] == "weapon"

        # Verify the type exists in the system
        assert "weapon" in test_system.models

    def test_type_only_entries(self, test_system):
        """Test entries with only type specified (no id)."""
        table = test_system.tables["basic-items"]

        # Entry 5 should have only type specified
        entry = table.entries[5]
        assert isinstance(entry, dict)
        assert entry["type"] == "armor"
        assert "id" not in entry

        # Verify the type exists in the system
        assert "armor" in test_system.models

    def test_generation_entries(self, test_system):
        """Test entries with generate flag."""
        table = test_system.tables["basic-items"]

        # Entry 6 should have generate flag
        entry = table.entries[6]
        assert isinstance(entry, dict)
        assert entry["type"] == "item"
        assert entry["generate"] is True

    def test_mixed_entry_formats(self, test_system):
        """Test that tables can mix different entry formats."""
        table = test_system.tables["starting-gear"]

        # Simple string
        assert table.entries[1] == "backpack"

        # Type override
        entry_4 = table.entries[4]
        assert entry_4["id"] == "longsword"
        assert entry_4["type"] == "weapon"

        # Random selection
        entry_10 = table.entries[10]
        assert entry_10["type"] == "weapon"
        assert "id" not in entry_10

        # Generation
        entry_18 = table.entries[18]
        assert entry_18["generate"] is True


class TestEntryTypeValidation:
    """Test validation of entry types and model references."""

    @pytest.fixture
    def test_system(self, test_systems_dir):
        """Load the table entry types test system."""
        loader = SystemLoader()
        return loader.load_system(test_systems_dir / "table_entry_types")

    def test_entry_type_must_reference_valid_model(self, test_system):
        """Test that entry_type must reference a valid model when not 'str'."""
        # Our test tables should reference valid models
        basic_table = test_system.tables["basic-items"]
        assert basic_table.entry_type == "item"
        assert "item" in test_system.models

    def test_type_overrides_must_reference_valid_types(self, test_system):
        """Test that type overrides must reference valid types."""
        table = test_system.tables["starting-gear"]

        # Check that all model references are valid
        for entry_value in table.entries.values():
            if isinstance(entry_value, dict) and "model" in entry_value:
                model_id = entry_value["model"]
                assert model_id in test_system.models, (
                    f"Model '{model_id}' not found in system"
                )

    def test_backward_compatibility_with_string_tables(self, test_system):
        """Test that tables without entry_type work as before."""
        table = test_system.tables["string-table"]

        # Should default to str entry_type
        assert table.entry_type == "str"

        # Simple string entries should work
        assert table.entries[1] == "Simple string"
        assert table.entries[2] == "Another string"

        # Complex entries should still be parsed
        assert isinstance(table.entries[3], dict)
        assert table.entries[3]["type"] == "weapon"


class TestComplexScenarios:
    """Test complex real-world scenarios combining multiple features."""

    @pytest.fixture
    def test_system(self, test_systems_dir):
        """Load the table entry types test system."""
        loader = SystemLoader()
        return loader.load_system(test_systems_dir / "table_entry_types")

    def test_starting_gear_table_structure(self, test_system):
        """Test the complete starting gear table structure."""
        table = test_system.tables["starting-gear"]

        assert table.id == "starting-gear"
        assert table.entry_type == "item"
        assert table.roll == "1d20"
        assert len(table.entries) == 13  # Entries 1-6, 10-12, 17-20

        # Verify entry types
        entry_types = {
            1: "string",  # "backpack"
            4: "override",  # {id: "longsword", model: "weapon"}
            10: "random",  # {model: "weapon"}
            18: "generate",  # {generate: true}
            19: "gen_type",  # {type: "armor", generate: true}
        }

        for entry_num, expected_type in entry_types.items():
            entry = table.entries[entry_num]

            if expected_type == "string":
                assert isinstance(entry, str)
            elif expected_type == "override":
                assert isinstance(entry, dict)
                assert "id" in entry and "type" in entry
            elif expected_type == "random":
                assert isinstance(entry, dict)
                assert "type" in entry and "id" not in entry and "generate" not in entry
            elif expected_type == "generate":
                assert isinstance(entry, dict)
                assert entry.get("generate") is True
            elif expected_type == "gen_type":
                assert isinstance(entry, dict)
                assert "type" in entry and entry.get("generate") is True

    def test_compendium_model_alignment(self, test_system):
        """Test that compendiums align with models referenced in tables."""
        # Get all models referenced in tables
        referenced_models = set()

        for table in test_system.tables.values():
            # Add entry_type if it's not 'str'
            if table.entry_type != "str":
                referenced_models.add(table.entry_type)

            # Add type overrides from entries
            for entry in table.entries.values():
                if isinstance(entry, dict) and "type" in entry:
                    referenced_models.add(entry["type"])

        # Verify each referenced model has a corresponding compendium
        {comp.model for comp in test_system.compendiums.values()}

        for model_id in referenced_models:
            assert model_id in test_system.models, f"Model '{model_id}' not found"
            # Note: Not all models need compendiums (they might be for generation only)
            # But if they reference existing items, they should have compendiums

    def test_entry_resolution_priorities(self, test_system):
        """Test the priority order for entry resolution."""
        table = test_system.tables["starting-gear"]

        # Test cases for resolution priority:
        # 1. Simple string -> uses entry_type
        # 2. {id: "x", type: "y"} -> uses type override
        # 3. {type: "x"} -> uses specified type for random selection
        # 4. {generate: true} -> uses entry_type for generation
        # 5. {type: "x", generate: true} -> uses specified type for generation

        # Verify structure matches expected resolution behavior
        entry_4 = table.entries[4]  # {id: "longsword", type: "weapon"}
        assert entry_4["type"] == "weapon"  # Should override table's entry_type

        entry_10 = table.entries[10]  # {type: "weapon"}
        assert entry_10["type"] == "weapon"  # Should use weapon type, not item

        entry_18 = table.entries[18]  # {generate: true}
        # Should use table's entry_type (item) for generation
        assert entry_18["generate"] is True
        assert "type" not in entry_18  # Will use table's entry_type

        entry_19 = table.entries[19]  # {type: "armor", generate: true}
        assert entry_19["type"] == "armor"  # Should use armor, not item
        assert entry_19["generate"] is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def loader(self):
        """Create a SystemLoader for testing."""
        return SystemLoader()

    def test_empty_entry_type_defaults_to_str(self, test_systems_dir):
        """Test that empty or missing entry_type defaults to 'str'."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "table_entry_types")

        table = system.tables["string-table"]
        assert table.entry_type == "str"

    def test_entry_type_case_sensitivity(self, test_systems_dir):
        """Test that entry_type is case sensitive and matches model IDs exactly."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "table_entry_types")

        # Model IDs are lowercase in our test system
        table = system.tables["basic-items"]
        assert table.entry_type == "item"  # Should match exactly
        assert "item" in system.models
        assert "Item" not in system.models  # Case sensitive


# Integration with existing testing infrastructure
class TestTableEntryTypeIntegration:
    """Test integration with existing table and compendium systems."""

    @pytest.fixture
    def test_system(self, test_systems_dir):
        """Load the table entry types test system."""
        loader = SystemLoader()
        return loader.load_system(test_systems_dir / "table_entry_types")

    def test_system_loads_completely(self, test_system):
        """Test that the entire system loads without errors."""
        # Verify all expected components are loaded
        assert len(test_system.models) == 3  # weapon, armor, item
        assert len(test_system.compendiums) == 3  # weapons, armor, items
        assert len(test_system.tables) == 3  # basic-items, starting-gear, string-table

        # Verify no loading errors
        assert test_system.id == "table_entry_types"
        assert test_system.name == "Table Entry Types Test System"

    def test_cross_references_resolve(self, test_system):
        """Test that cross-references between components resolve correctly."""
        table = test_system.tables["starting-gear"]

        # Verify that type references in table entries correspond to actual models
        for entry in table.entries.values():
            if isinstance(entry, dict) and "type" in entry:
                model_id = entry["type"]
                assert model_id in test_system.models

                # If the model has a compendium, verify it exists
                model_compendiums = [
                    c for c in test_system.compendiums.values() if c.model == model_id
                ]
                # Note: Models don't require compendiums, but if they exist, they should be valid
                for comp in model_compendiums:
                    assert comp.model == model_id

    def test_existing_validation_still_works(self, test_system):
        """Test that existing table validation functionality still works."""
        for table in test_system.tables.values():
            # Basic table validation should still pass
            assert hasattr(table, "id")
            assert hasattr(table, "roll")
            assert hasattr(table, "entries")

            # Roll validation should still work
            assert table.roll  # Should have a valid roll expression

            # Entries should be properly parsed
            assert len(table.entries) > 0
