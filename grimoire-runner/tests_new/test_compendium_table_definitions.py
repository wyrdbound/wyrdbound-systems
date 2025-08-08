"""
Tests for GRIMOIRE compendium and table definition functionality.

This module tests compendium and table definition capabilities, focusing on:
- Compendium loading and structure validation
- Table loading and structure validation
- Model validation for compendium entries
- Cross-references between compendiums and tables
- Error handling for malformed definitions
- Range-based table entries
- Complex table result types
"""


import pytest
import yaml

from grimoire_runner.core.loader import SystemLoader


class TestBasicCompendiumLoading:
    """Test basic compendium loading functionality."""

    def test_load_system_with_compendiums(self, test_systems_dir):
        """Test loading a system that contains compendium definitions."""
        loader = SystemLoader()

        compendium_test_path = test_systems_dir / "compendium_test"
        system = loader.load_system(compendium_test_path)

        # Verify system loaded
        assert system.id == "compendium_test"

        # Verify compendiums were loaded
        assert len(system.compendiums) == 2
        assert "basic_weapons" in system.compendiums
        assert "basic_items" in system.compendiums

    def test_basic_compendium_structure(self, test_systems_dir):
        """Test basic compendium structure and metadata."""
        loader = SystemLoader()

        compendium_test_path = test_systems_dir / "compendium_test"
        system = loader.load_system(compendium_test_path)

        weapons_compendium = system.compendiums["basic_weapons"]

        # Verify compendium metadata
        assert weapons_compendium.id == "basic_weapons"
        assert weapons_compendium.kind == "compendium"
        assert weapons_compendium.name == "Basic Weapons"
        assert weapons_compendium.model == "weapon"

        # Verify entries exist
        assert "dagger" in weapons_compendium.entries
        assert "shortsword" in weapons_compendium.entries
        assert "shortbow" in weapons_compendium.entries
        assert len(weapons_compendium.entries) == 3

    def test_compendium_entry_structure(self, test_systems_dir):
        """Test compendium entry structure and content."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_test")

        weapons_compendium = system.compendiums["basic_weapons"]
        dagger_entry = weapons_compendium.entries["dagger"]

        # Verify entry structure
        assert dagger_entry["name"] == "Dagger"
        assert dagger_entry["damage"] == "1d4"
        assert dagger_entry["weapon_type"] == "melee"
        assert dagger_entry["cost"] == 200


class TestBasicTableLoading:
    """Test basic table loading functionality."""

    def test_load_system_with_tables(self, test_systems_dir):
        """Test loading a system that contains table definitions."""
        loader = SystemLoader()

        table_test_path = test_systems_dir / "table_test"
        system = loader.load_system(table_test_path)

        # Verify system loaded
        assert system.id == "table_test"

        # Verify tables were loaded
        assert len(system.tables) == 3
        assert "simple_traits" in system.tables
        assert "range_table" in system.tables
        assert "complex_results" in system.tables

    def test_basic_table_structure(self, test_systems_dir):
        """Test basic table structure and metadata."""
        loader = SystemLoader()

        table_test_path = test_systems_dir / "table_test"
        system = loader.load_system(table_test_path)

        traits_table = system.tables["simple_traits"]

        # Verify table metadata
        assert traits_table.id == "simple_traits"
        assert traits_table.kind == "table"
        assert traits_table.name == "Simple Traits"
        assert traits_table.roll == "1d6"
        assert traits_table.description == "Simple character traits for testing"

        # Verify entries exist
        assert len(traits_table.entries) == 6
        assert traits_table.entries[1] == "Brave"
        assert traits_table.entries[6] == "Wise"

    def test_range_table_entries(self, test_systems_dir):
        """Test table with range-based entries."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "table_test")

        range_table = system.tables["range_table"]

        # Verify range entries
        assert range_table.entries["1-5"] == "Common"
        assert range_table.entries["6-15"] == "Uncommon"
        assert range_table.entries["16-19"] == "Rare"
        assert range_table.entries[20] == "Legendary"

    def test_complex_table_entries(self, test_systems_dir):
        """Test table with complex object entries."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "table_test")

        complex_table = system.tables["complex_results"]

        # Verify complex entries
        magic_sword = complex_table.entries[1]
        assert magic_sword["name"] == "Magic Sword"
        assert magic_sword["type"] == "weapon"
        assert magic_sword["power"] == 5

        potion = complex_table.entries[2]
        assert potion["name"] == "Healing Potion"
        assert potion["effect"] == "heal 2d4+2"


class TestCompendiumValidation:
    """Test compendium validation functionality."""

    def test_compendium_model_validation(self, test_systems_dir):
        """Test that compendium entries are validated against their model."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_test")

        # Get compendium and model
        weapons_compendium = system.compendiums["basic_weapons"]
        system.models["weapon"]

        # Verify entries match model requirements
        for _entry_id, entry_data in weapons_compendium.entries.items():
            # Check required attributes exist
            assert "name" in entry_data
            assert "damage" in entry_data
            assert "weapon_type" in entry_data

            # Check enum constraints
            assert entry_data["weapon_type"] in ["melee", "ranged"]

    @pytest.mark.skip(
        reason="ModelDefinition.validate_instance() with custom validation not yet implemented"
    )
    def test_compendium_model_validation_with_validation_engine(self, test_systems_dir):
        """TODO: Test compendium entries using proper model validation engine."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_test")

        # Get compendium and model
        weapons_compendium = system.compendiums["basic_weapons"]
        system.models["weapon"]

        # When model validation is fully implemented, this should work:
        for _entry_id, _entry_data in weapons_compendium.entries.items():
            # This should validate the entry against the weapon model
            # errors = weapon_model.validate_instance(entry_data)
            # assert len(errors) == 0, f"Entry '{entry_id}' should be valid: {errors}"
            pass

        # For now, this test documents the expected behavior
        assert True, "Proper model validation not yet implemented"

    def test_optional_attributes_in_compendium(self, test_systems_dir):
        """Test that optional attributes are handled correctly."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_test")

        items_compendium = system.compendiums["basic_items"]

        # Some entries have description, some don't
        rope_entry = items_compendium.entries["rope"]
        assert "description" in rope_entry

        items_compendium.entries["rations"]
        # rations entry doesn't have description, which should be fine since it's optional

    def test_compendium_validation_method(self, test_systems_dir):
        """Test the compendium validation method."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_test")

        weapons_compendium = system.compendiums["basic_weapons"]

        # Valid compendium should have no errors
        errors = weapons_compendium.validate()
        assert len(errors) == 0


class TestTableValidation:
    """Test table validation functionality."""

    def test_table_validation_method(self, test_systems_dir):
        """Test the table validation method."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "table_test")

        traits_table = system.tables["simple_traits"]

        # Valid table should have no errors
        errors = traits_table.validate()
        assert len(errors) == 0

    def test_table_roll_expression_validation(self, test_systems_dir):
        """Test table roll expression validation."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "table_test")

        # Check various roll expressions
        tables_with_valid_rolls = ["simple_traits", "range_table", "complex_results"]

        for table_id in tables_with_valid_rolls:
            table = system.tables[table_id]
            errors = table.validate()
            assert len(errors) == 0, (
                f"Table {table_id} should have valid roll expression"
            )


class TestCompendiumTableIntegration:
    """Test integration between compendiums and tables."""

    def test_load_integrated_system(self, test_systems_dir):
        """Test loading system with both compendiums and tables."""
        loader = SystemLoader()

        integration_path = test_systems_dir / "compendium_table_integration"
        system = loader.load_system(integration_path)

        # Verify both compendiums and tables loaded
        assert len(system.compendiums) == 1
        assert len(system.tables) == 1
        assert "starting_gear" in system.compendiums
        assert "starting_equipment" in system.tables

    def test_table_entry_type_reference(self, test_systems_dir):
        """Test table with entry_type referring to model."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_table_integration")

        equipment_table = system.tables["starting_equipment"]

        # Verify entry_type is set correctly
        assert equipment_table.entry_type == "gear"

        # Verify entries reference compendium items
        gear_compendium = system.compendiums["starting_gear"]
        for entry_value in equipment_table.entries.values():
            assert entry_value in gear_compendium.entries

    def test_cross_reference_validation(self, test_systems_dir):
        """Test that table entries reference valid compendium items."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_table_integration")

        equipment_table = system.tables["starting_equipment"]
        gear_compendium = system.compendiums["starting_gear"]

        # All table entries should reference valid compendium entries
        for _entry_id, entry_value in equipment_table.entries.items():
            assert entry_value in gear_compendium.entries, (
                f"Table entry '{entry_value}' not found in compendium"
            )


class TestCompendiumTableErrorHandling:
    """Test error handling for malformed compendiums and tables."""

    def test_entry_type_validation_should_fail_for_mismatched_types(
        self, temp_system_dir
    ):
        """Test that entry_type validation should catch type mismatches."""
        loader = SystemLoader()

        system_dir = temp_system_dir / "entry_type_mismatch"
        system_dir.mkdir()
        tables_dir = system_dir / "tables"
        tables_dir.mkdir()
        models_dir = system_dir / "models"
        models_dir.mkdir()

        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(
                {
                    "id": "entry_type_mismatch",
                    "kind": "system",
                    "name": "Entry Type Mismatch Test",
                },
                f,
            )

        # Create a simple model
        model_file = models_dir / "item.yaml"
        with open(model_file, "w") as f:
            yaml.dump(
                {
                    "id": "item",
                    "kind": "model",
                    "name": "Item",
                    "attributes": {
                        "name": {"type": "str"},
                        "value": {"type": "int", "default": 0},
                    },
                },
                f,
            )

        # Create table with entry_type mismatch
        table_file = tables_dir / "mismatched.yaml"
        with open(table_file, "w") as f:
            yaml.dump(
                {
                    "kind": "table",
                    "id": "mismatched",
                    "name": "Mismatched Entry Types",
                    "entry_type": "item",  # Claims entries are item model instances
                    "roll": "1d3",
                    "entries": {
                        1: "simple_string",  # But these are strings, not item instances!
                        2: 42,  # This is an integer, not an item!
                        3: {
                            "name": "Sword",
                            "value": 100,
                        },  # Only this one matches item model
                    },
                },
                f,
            )

        # Load and validate - should catch entry type mismatches
        system = loader.load_system(system_dir)
        table = system.tables["mismatched"]

        errors = table.validate()

        # This test should FAIL until we implement entry_type validation
        # Expected behavior: validation should catch that entries 1 and 2 don't match entry_type
        assert len(errors) >= 2, (
            "Should detect entry type mismatches for string and integer entries"
        )

        error_text = " ".join(errors)
        assert "entry_type" in error_text.lower(), (
            "Errors should mention entry_type validation"
        )

    def test_entry_type_validation_gap(self, test_systems_dir):
        """Test that entry_type validation now properly validates entry values."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "compendium_table_integration")

        equipment_table = system.tables["starting_equipment"]

        # Verify the table structure
        assert equipment_table.entry_type == "gear"

        # The table entries are strings (compendium references), not gear objects
        for entry_value in equipment_table.entries.values():
            assert isinstance(
                entry_value, str
            )  # These are strings, not gear instances!

        # Now with proper entry_type validation, this should detect the mismatch
        errors = equipment_table.validate()
        # The validation should now catch that entry_type says "gear" but entries are strings
        assert len(errors) > 0, "Should detect entry_type mismatch"

        error_text = " ".join(errors)
        assert "entry_type" in error_text.lower(), (
            "Errors should mention entry_type validation"
        )
        assert "gear" in error_text, "Should mention the expected model type"

    def test_missing_compendium_model(self, temp_system_dir):
        """Test error handling for compendium with missing model reference."""
        loader = SystemLoader()

        system_dir = temp_system_dir / "invalid_compendium"
        system_dir.mkdir()
        compendium_dir = system_dir / "compendium"
        compendium_dir.mkdir()

        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(
                {
                    "id": "invalid_compendium",
                    "kind": "system",
                    "name": "Invalid Compendium Test",
                },
                f,
            )

        # Create compendium with missing model reference
        compendium_file = compendium_dir / "invalid.yaml"
        with open(compendium_file, "w") as f:
            yaml.dump(
                {
                    "kind": "compendium",
                    "id": "invalid",
                    "name": "Invalid Compendium",
                    "model": "nonexistent_model",
                    "entries": {"item1": {"name": "Test"}},
                },
                f,
            )

        # Should load but compendium validation should fail
        system = loader.load_system(system_dir)
        compendium = system.compendiums["invalid"]

        # Note: We don't validate model references during loading,
        # but the compendium should still be loaded
        assert compendium.model == "nonexistent_model"

    def test_invalid_table_roll_expression(self, temp_system_dir):
        """Test error handling for table with invalid roll expression."""
        loader = SystemLoader()

        system_dir = temp_system_dir / "invalid_table"
        system_dir.mkdir()
        tables_dir = system_dir / "tables"
        tables_dir.mkdir()

        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(
                {"id": "invalid_table", "kind": "system", "name": "Invalid Table Test"},
                f,
            )

        # Create table with invalid roll expression
        table_file = tables_dir / "invalid.yaml"
        with open(table_file, "w") as f:
            yaml.dump(
                {
                    "kind": "table",
                    "id": "invalid",
                    "name": "Invalid Table",
                    "roll": "invalid_expression",
                    "entries": {1: "Result"},
                },
                f,
            )

        # Should load but table validation should fail
        system = loader.load_system(system_dir)
        table = system.tables["invalid"]

        errors = table.validate()
        assert len(errors) > 0
        assert any("Invalid roll expression" in error for error in errors)

    def test_empty_compendium_entries(self, temp_system_dir):
        """Test error handling for compendium with no entries."""
        loader = SystemLoader()

        system_dir = temp_system_dir / "empty_compendium"
        system_dir.mkdir()
        compendium_dir = system_dir / "compendium"
        compendium_dir.mkdir()

        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(
                {
                    "id": "empty_compendium",
                    "kind": "system",
                    "name": "Empty Compendium Test",
                },
                f,
            )

        # Create compendium with no entries
        compendium_file = compendium_dir / "empty.yaml"
        with open(compendium_file, "w") as f:
            yaml.dump(
                {
                    "kind": "compendium",
                    "id": "empty",
                    "name": "Empty Compendium",
                    "model": "some_model",
                    "entries": {},
                },
                f,
            )

        # Should load but validation should fail
        system = loader.load_system(system_dir)
        compendium = system.compendiums["empty"]

        errors = compendium.validate()
        assert len(errors) > 0
        assert any("must have at least one entry" in error for error in errors)


class TestCompendiumTableUtilities:
    """Test utility functions for creating compendiums and tables in tests."""

    def test_create_simple_compendium(self, temp_system_dir):
        """Test creating a simple compendium programmatically."""
        compendium_data = {
            "kind": "compendium",
            "id": "test_compendium",
            "name": "Test Compendium",
            "model": "test_model",
            "entries": {
                "item1": {"name": "Item One", "value": 100},
                "item2": {"name": "Item Two", "value": 200},
            },
        }

        system_dir = temp_system_dir / "compendium_builder_test"
        system_dir.mkdir()
        compendium_dir = system_dir / "compendium"
        compendium_dir.mkdir()

        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(
                {
                    "id": "compendium_builder_test",
                    "kind": "system",
                    "name": "Compendium Builder Test",
                },
                f,
            )

        # Create compendium
        compendium_file = compendium_dir / "test_compendium.yaml"
        with open(compendium_file, "w") as f:
            yaml.dump(compendium_data, f)

        # Test loading
        loader = SystemLoader()
        system = loader.load_system(system_dir)

        test_compendium = system.compendiums["test_compendium"]
        assert test_compendium.id == "test_compendium"
        assert test_compendium.name == "Test Compendium"
        assert "item1" in test_compendium.entries
        assert "item2" in test_compendium.entries

    def test_create_simple_table(self, temp_system_dir):
        """Test creating a simple table programmatically."""
        table_data = {
            "kind": "table",
            "id": "test_table",
            "name": "Test Table",
            "roll": "1d4",
            "entries": {
                1: "Result One",
                2: "Result Two",
                3: "Result Three",
                4: "Result Four",
            },
        }

        system_dir = temp_system_dir / "table_builder_test"
        system_dir.mkdir()
        tables_dir = system_dir / "tables"
        tables_dir.mkdir()

        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(
                {
                    "id": "table_builder_test",
                    "kind": "system",
                    "name": "Table Builder Test",
                },
                f,
            )

        # Create table
        table_file = tables_dir / "test_table.yaml"
        with open(table_file, "w") as f:
            yaml.dump(table_data, f)

        # Test loading
        loader = SystemLoader()
        system = loader.load_system(system_dir)

        test_table = system.tables["test_table"]
        assert test_table.id == "test_table"
        assert test_table.name == "Test Table"
        assert test_table.roll == "1d4"
        assert len(test_table.entries) == 4
