"""
Tests for table definition models.
"""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.models.table import TableDefinition, TableEntry


class TestTableEntry:
    """Test the TableEntry model."""

    def test_table_entry_default_weight(self):
        """Test table entry with default weight."""
        entry = TableEntry(value="Test Result")

        assert entry.value == "Test Result"
        assert entry.weight == 1

    def test_table_entry_custom_weight(self):
        """Test table entry with custom weight."""
        entry = TableEntry(value="Rare Result", weight=5)

        assert entry.value == "Rare Result"
        assert entry.weight == 5

    def test_table_entry_various_value_types(self):
        """Test table entry with different value types."""
        # String value
        entry1 = TableEntry(value="String value")
        assert entry1.value == "String value"

        # Integer value
        entry2 = TableEntry(value=42)
        assert entry2.value == 42

        # Dictionary value
        entry3 = TableEntry(value={"name": "Complex", "type": "object"})
        assert entry3.value == {"name": "Complex", "type": "object"}

        # List value
        entry4 = TableEntry(value=["item1", "item2", "item3"])
        assert entry4.value == ["item1", "item2", "item3"]


class TestTableDefinition:
    """Test the TableDefinition model."""

    def setup_method(self):
        """Set up test fixtures."""
        self.simple_table = TableDefinition(
            kind="table",
            name="Simple Table",
            id="simple_test",
            entries={1: "Result One", 2: "Result Two", 3: "Result Three"},
        )

        self.range_table = TableDefinition(
            kind="table",
            name="Range Table",
            id="range_test",
            roll="1d10",
            entries={
                "1-3": "Common Result",
                "4-7": "Uncommon Result",
                "8-9": "Rare Result",
                10: "Legendary Result",
            },
        )

        self.complex_table = TableDefinition(
            kind="table",
            name="Complex Table",
            id="complex_test",
            display_name="Complex Random Table",
            version="2.0",
            roll="2d6",
            description="A table with complex entries",
            entry_type="Equipment",
            entries={
                2: {"name": "Dagger", "damage": "1d4"},
                7: {"name": "Sword", "damage": "1d8"},
                12: {"name": "Greatsword", "damage": "2d6"},
            },
        )

    def test_table_initialization_minimal(self):
        """Test table initialization with minimal parameters."""
        table = TableDefinition(kind="table", name="Test Table")

        assert table.kind == "table"
        assert table.name == "Test Table"
        assert table.id is None
        assert table.display_name is None
        assert table.version == "1.0"
        assert table.roll is None
        assert table.description is None
        assert table.entry_type == "str"  # Now defaults to "str"
        assert table.entries == {}

    def test_table_initialization_full(self):
        """Test table initialization with all parameters."""
        table = TableDefinition(
            kind="table",
            name="Full Table",
            id="full_test",
            display_name="Full Test Table",
            version="3.0",
            roll="1d20",
            description="A fully specified table",
            entry_type="Result",
            entries={1: "Result"},
        )

        assert table.kind == "table"
        assert table.name == "Full Table"
        assert table.id == "full_test"
        assert table.display_name == "Full Test Table"
        assert table.version == "3.0"
        assert table.roll == "1d20"
        assert table.description == "A fully specified table"
        assert table.entry_type == "Result"
        assert table.entries == {1: "Result"}

    def test_get_entry_existing(self):
        """Test getting an existing entry."""
        result = self.simple_table.get_entry(2)
        assert result == "Result Two"

    def test_get_entry_nonexistent(self):
        """Test getting a non-existent entry."""
        result = self.simple_table.get_entry(99)
        assert result is None

    def test_get_entry_string_key(self):
        """Test getting entry with string key."""
        table = TableDefinition(
            kind="table",
            name="String Key Table",
            entries={"key1": "Value 1", "key2": "Value 2"},
        )

        result = table.get_entry("key1")
        assert result == "Value 1"

    def test_get_all_entries(self):
        """Test getting all entries."""
        entries = self.simple_table.get_all_entries()

        assert entries == {1: "Result One", 2: "Result Two", 3: "Result Three"}

        # Should be a copy, not the original
        entries[4] = "New Result"
        assert 4 not in self.simple_table.entries

    def test_get_all_entries_empty(self):
        """Test getting all entries from empty table."""
        empty_table = TableDefinition(kind="table", name="Empty")
        entries = empty_table.get_all_entries()

        assert entries == {}

    def test_get_random_entry(self):
        """Test getting random entry."""
        # Use fixed seed for reproducible test
        rng = random.Random(42)

        # Get multiple random entries
        results = [self.simple_table.get_random_entry(rng) for _ in range(10)]

        # All results should be valid entries
        valid_values = set(self.simple_table.entries.values())
        assert all(result in valid_values for result in results)

        # Should have some variation (not all the same)
        assert len(set(results)) > 1

    def test_get_random_entry_default_rng(self):
        """Test getting random entry with default RNG."""
        result = self.simple_table.get_random_entry()

        valid_values = set(self.simple_table.entries.values())
        assert result in valid_values

    def test_get_random_entry_empty_table(self):
        """Test getting random entry from empty table."""
        empty_table = TableDefinition(kind="table", name="Empty")
        result = empty_table.get_random_entry()

        assert result is None

    def test_get_weighted_random_entry_no_weights(self):
        """Test weighted random with no custom weights (equal weights)."""
        rng = random.Random(42)

        results = [
            self.simple_table.get_weighted_random_entry(rng=rng) for _ in range(10)
        ]

        valid_values = set(self.simple_table.entries.values())
        assert all(result in valid_values for result in results)

    def test_get_weighted_random_entry_custom_weights(self):
        """Test weighted random with custom weights."""
        rng = random.Random(42)

        # Weight entry 1 heavily
        weights = {1: 10, 2: 1, 3: 1}

        results = [
            self.simple_table.get_weighted_random_entry(weights, rng)
            for _ in range(100)
        ]

        # "Result One" should appear much more frequently
        result_one_count = results.count("Result One")
        assert result_one_count > 50  # Should be heavily weighted

    def test_get_weighted_random_entry_empty_table(self):
        """Test weighted random from empty table."""
        empty_table = TableDefinition(kind="table", name="Empty")
        result = empty_table.get_weighted_random_entry()

        assert result is None

    def test_get_entry_by_range_integer_exact_match(self):
        """Test range entry lookup with exact integer match."""
        result = self.range_table.get_entry_by_range(10)
        assert result == "Legendary Result"

    def test_get_entry_by_range_within_range(self):
        """Test range entry lookup within range."""
        result = self.range_table.get_entry_by_range(2)
        assert result == "Common Result"

        result = self.range_table.get_entry_by_range(5)
        assert result == "Uncommon Result"

        result = self.range_table.get_entry_by_range(8)
        assert result == "Rare Result"

    def test_get_entry_by_range_edge_cases(self):
        """Test range entry lookup at edge cases."""
        # Test boundaries
        assert self.range_table.get_entry_by_range(1) == "Common Result"
        assert self.range_table.get_entry_by_range(3) == "Common Result"
        assert self.range_table.get_entry_by_range(4) == "Uncommon Result"
        assert self.range_table.get_entry_by_range(7) == "Uncommon Result"
        assert self.range_table.get_entry_by_range(9) == "Rare Result"

    def test_get_entry_by_range_no_match(self):
        """Test range entry lookup with no match."""
        result = self.range_table.get_entry_by_range(99)
        assert result is None

    def test_get_entry_by_range_invalid_range_format(self):
        """Test range entry with invalid range format."""
        table = TableDefinition(
            kind="table",
            name="Invalid Range Table",
            entries={
                "invalid-range-format": "Should not match",
                "1-": "Incomplete range",
                "-5": "Incomplete range",
                "not-numbers": "Invalid",
            },
        )

        result = table.get_entry_by_range(3)
        assert result is None

    def test_get_entry_by_range_string_match(self):
        """Test range entry with string key exact match."""
        table = TableDefinition(
            kind="table",
            name="String Table",
            entries={"exact": "Exact Match", "1-3": "Range Match"},
        )

        # String key should match exactly
        result = table.get_entry_by_range("exact")
        assert result == "Exact Match"

    def test_validate_valid_table(self):
        """Test validation of valid table."""
        errors = self.simple_table.validate()
        assert errors == []

    def test_validate_valid_table_with_roll(self):
        """Test validation of valid table with roll expression."""
        errors = self.range_table.validate()
        assert errors == []

    def test_validate_wrong_kind(self):
        """Test validation with wrong kind."""
        table = TableDefinition(kind="wrong", name="Test Table", entries={1: "Result"})

        errors = table.validate()
        assert len(errors) == 1
        assert "kind must be 'table'" in errors[0]

    def test_validate_missing_name(self):
        """Test validation with missing name."""
        table = TableDefinition(kind="table", name="", entries={1: "Result"})

        errors = table.validate()
        assert len(errors) == 1
        assert "name is required" in errors[0]

    def test_validate_no_entries(self):
        """Test validation with no entries."""
        table = TableDefinition(kind="table", name="Empty Table", entries={})

        errors = table.validate()
        assert len(errors) == 1
        assert "must have at least one entry" in errors[0]

    def test_validate_invalid_roll_expression(self):
        """Test validation with invalid roll expression."""
        table = TableDefinition(
            kind="table",
            name="Invalid Roll Table",
            roll="invalid_roll",
            entries={1: "Result"},
        )

        errors = table.validate()
        assert len(errors) == 1
        assert "Invalid roll expression" in errors[0]

    def test_validate_valid_roll_expressions(self):
        """Test validation with various valid roll expressions."""
        valid_rolls = ["1d4", "2d6", "1d8", "3d10", "1d12", "1d20", "1d100"]

        for roll in valid_rolls:
            table = TableDefinition(
                kind="table", name="Test Table", roll=roll, entries={1: "Result"}
            )

            errors = table.validate()
            assert errors == [], f"Roll expression '{roll}' should be valid"

    def test_validate_multiple_errors(self):
        """Test validation with multiple errors."""
        table = TableDefinition(kind="wrong", name="", roll="invalid", entries={})

        errors = table.validate()
        assert len(errors) == 4  # All validation errors


class TestTableDefinitionComplexScenarios:
    """Test complex scenarios and edge cases."""

    def test_table_with_complex_entries(self):
        """Test table with complex entry types."""
        table = TableDefinition(
            kind="table",
            name="Complex Entries",
            entries={
                1: {
                    "type": "weapon",
                    "name": "Sword",
                    "stats": {"damage": "1d8", "weight": 3},
                },
                2: ["Multiple", "Items", "List"],
                3: "Simple String",
                4: 42,
                5: True,
            },
        )

        # Test getting different types
        weapon = table.get_entry(1)
        assert weapon["name"] == "Sword"
        assert weapon["stats"]["damage"] == "1d8"

        items_list = table.get_entry(2)
        assert items_list == ["Multiple", "Items", "List"]

        simple = table.get_entry(3)
        assert simple == "Simple String"

        number = table.get_entry(4)
        assert number == 42

        boolean = table.get_entry(5)
        assert boolean is True

    def test_table_entry_keys_mixed_types(self):
        """Test table with mixed key types."""
        table = TableDefinition(
            kind="table",
            name="Mixed Keys",
            entries={1: "Integer Key", "string": "String Key", "1-5": "Range Key"},
        )

        assert table.get_entry(1) == "Integer Key"
        assert table.get_entry("string") == "String Key"
        assert table.get_entry_by_range(3) == "Range Key"

    def test_random_selection_distribution(self):
        """Test that random selection has reasonable distribution."""
        table = TableDefinition(
            kind="table",
            name="Distribution Test",
            entries={i: f"Result {i}" for i in range(1, 11)},  # 10 entries
        )

        rng = random.Random(12345)  # Fixed seed
        results = [table.get_random_entry(rng) for _ in range(1000)]

        # Count occurrences
        counts = {}
        for result in results:
            counts[result] = counts.get(result, 0) + 1

        # Each entry should appear roughly 100 times (1000/10)
        # Allow for some variance (50-150 times is reasonable)
        for count in counts.values():
            assert 50 <= count <= 150, f"Distribution seems off: {counts}"

    def test_weighted_distribution(self):
        """Test weighted random distribution."""
        table = TableDefinition(
            kind="table",
            name="Weighted Test",
            entries={1: "Common", 2: "Rare", 3: "Ultra Rare"},
        )

        # Heavy weighting towards "Common"
        weights = {1: 100, 2: 10, 3: 1}

        rng = random.Random(54321)  # Fixed seed
        results = [table.get_weighted_random_entry(weights, rng) for _ in range(1000)]

        counts = {result: results.count(result) for result in set(results)}

        # "Common" should appear much more frequently
        assert counts["Common"] > 800
        assert counts["Rare"] < 200
        assert counts["Ultra Rare"] < 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
