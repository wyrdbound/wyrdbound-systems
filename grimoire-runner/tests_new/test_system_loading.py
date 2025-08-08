"""
Tests for GRIMOIRE system loading functionality.

This module tests the basic system loading capabilities, focusing on:
- Loading minimal valid systems
- Parsing system.yaml files
- Currency system handling
- Credits and attribution parsing
- Error handling for invalid systems
"""


import pytest
import yaml

from grimoire_runner.core.loader import SystemLoader


class TestBasicSystemLoading:
    """Test basic system loading functionality."""

    def test_load_minimal_system(self, test_systems_dir):
        """Test loading the most minimal valid system."""
        loader = SystemLoader()

        minimal_path = test_systems_dir / "minimal_basic"
        system = loader.load_system(minimal_path)

        # Verify basic system properties
        assert system.id == "minimal_basic"
        assert system.kind == "system"
        assert system.name == "Minimal Basic System"
        assert (
            system.description
            == "Simplest possible valid GRIMOIRE system for testing basic system loading"
        )
        assert system.version == "1.0"

        # Optional fields should be None for minimal system
        assert system.default_source is None
        assert system.currency is None
        assert system.credits is None

        # Collections should be empty but initialized
        assert system.sources == {}
        assert system.models == {}
        assert system.compendiums == {}
        assert system.tables == {}
        assert system.flows == {}

    def test_load_system_with_currency(self, test_systems_dir):
        """Test loading a system with currency configuration."""
        loader = SystemLoader()

        currency_path = test_systems_dir / "currency_test"
        system = loader.load_system(currency_path)

        # Verify system basics
        assert system.id == "currency_test"
        assert system.name == "Currency Test System"

        # Verify currency system
        assert system.currency is not None
        assert system.currency.base_unit == "copper"

        # Check currency denominations
        assert len(system.currency.denominations) == 3

        # Verify copper denomination
        cp = system.currency.denominations["cp"]
        assert cp.name == "copper"
        assert cp.symbol == "cp"
        assert cp.value == 1
        assert cp.weight == 0.05

        # Verify silver denomination
        sp = system.currency.denominations["sp"]
        assert sp.name == "silver"
        assert sp.symbol == "sp"
        assert sp.value == 10
        assert sp.weight == 0.05

        # Verify gold denomination
        gp = system.currency.denominations["gp"]
        assert gp.name == "gold"
        assert gp.symbol == "gp"
        assert gp.value == 100
        assert gp.weight == 0.05

    def test_load_system_with_credits(self, test_systems_dir):
        """Test loading a system with credits and attribution."""
        loader = SystemLoader()

        credits_path = test_systems_dir / "credits_test"
        system = loader.load_system(credits_path)

        # Verify system basics
        assert system.id == "credits_test"
        assert system.name == "Credits Test System"
        assert system.default_source == "test_rulebook"

        # Verify credits
        assert system.credits is not None
        assert system.credits.author == "Test Author"
        assert system.credits.license == "CC BY 4.0"
        assert system.credits.publisher == "Test Publishing"
        assert system.credits.source_url == "https://example.com/test-game"

    def test_system_caching(self, test_systems_dir):
        """Test that systems are cached after loading."""
        loader = SystemLoader()

        minimal_path = test_systems_dir / "minimal_basic"

        # Load system first time
        system1 = loader.load_system(minimal_path)

        # Load same system again - should return cached version
        system2 = loader.load_system(minimal_path)

        # Should be the exact same object
        assert system1 is system2

        # Verify cached systems list
        loaded_systems = loader.list_loaded_systems()
        assert "minimal_basic" in loaded_systems

    def test_invalid_system_path(self):
        """Test error handling for invalid system paths."""
        loader = SystemLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_system("/path/that/does/not/exist")

    def test_missing_system_yaml(self, temp_system_dir):
        """Test error handling when system.yaml is missing."""
        loader = SystemLoader()

        # Create empty directory
        empty_dir = temp_system_dir / "empty_system"
        empty_dir.mkdir()

        with pytest.raises(FileNotFoundError, match="system.yaml not found"):
            loader.load_system(empty_dir)

    def test_invalid_yaml_syntax(self, temp_system_dir):
        """Test error handling for malformed YAML."""
        loader = SystemLoader()

        # Create system with invalid YAML
        bad_system_dir = temp_system_dir / "bad_yaml"
        bad_system_dir.mkdir()

        system_file = bad_system_dir / "system.yaml"
        with open(system_file, "w") as f:
            f.write("id: test\nkind: system\nname: [\ninvalid yaml")

        with pytest.raises(yaml.YAMLError):
            loader.load_system(bad_system_dir)


class TestSystemDefinitionParsing:
    """Test parsing of system.yaml file contents."""

    def test_required_fields_validation(self, temp_system_dir):
        """Test validation of required fields in system.yaml."""
        loader = SystemLoader()

        # Test missing 'id' field
        system_dir = temp_system_dir / "missing_id"
        system_dir.mkdir()

        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump({"kind": "system", "name": "Test System"}, f)

        with pytest.raises(KeyError):
            loader.load_system(system_dir)

    def test_optional_fields_handling(self, temp_system_dir):
        """Test that optional fields are handled correctly."""
        loader = SystemLoader()

        # Create system with only required fields (not using system_builder to avoid defaults)
        system_dir = temp_system_dir / "optional_test"
        system_dir.mkdir()

        system_data = {
            "id": "optional_test",
            "kind": "system",
            "name": "Optional Fields Test",
            # No optional fields included
        }

        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(system_data, f)

        system = loader.load_system(system_dir)

        # Optional fields should have sensible defaults
        assert system.description is None
        assert system.version is None
        assert system.default_source is None
        assert system.currency is None
        assert system.credits is None

    def test_currency_parsing_edge_cases(self, temp_system_dir):
        """Test edge cases in currency parsing."""
        loader = SystemLoader()

        # Test currency with minimal denomination data (weight is optional)
        system_dir = temp_system_dir / "currency_minimal"
        system_dir.mkdir()

        system_data = {
            "id": "currency_minimal",
            "kind": "system",
            "name": "Minimal Currency Test",
            "currency": {
                "base_unit": "coin",
                "denominations": {
                    "coin": {
                        "name": "coin",
                        "symbol": "c",
                        "value": 1,
                        # weight is optional - not included
                    }
                },
            },
        }

        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(system_data, f)

        system = loader.load_system(system_dir)

        assert system.currency.base_unit == "coin"
        coin = system.currency.denominations["coin"]
        assert coin.name == "coin"
        assert coin.symbol == "c"
        assert coin.value == 1
        # weight should be None or have a reasonable default when not specified
        assert hasattr(coin, "weight")
        # According to spec, weight is optional, so it should handle None gracefully

    def test_currency_weight_optional(self, temp_system_dir):
        """Test that weight field is truly optional for currency denominations."""
        loader = SystemLoader()

        # Test mixed currency where some denominations have weight, others don't
        system_dir = temp_system_dir / "currency_mixed_weight"
        system_dir.mkdir()

        system_data = {
            "id": "currency_mixed_weight",
            "kind": "system",
            "name": "Mixed Weight Currency Test",
            "currency": {
                "base_unit": "copper",
                "denominations": {
                    "cp": {
                        "name": "copper",
                        "symbol": "cp",
                        "value": 1,
                        "weight": 0.05,  # weight specified
                    },
                    "sp": {
                        "name": "silver",
                        "symbol": "sp",
                        "value": 10,
                        # weight not specified - should be optional
                    },
                    "gp": {
                        "name": "gold",
                        "symbol": "gp",
                        "value": 100,
                        "weight": 0.05,  # weight specified again
                    },
                },
            },
        }

        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(system_data, f)

        system = loader.load_system(system_dir)

        # Verify all denominations loaded correctly
        assert len(system.currency.denominations) == 3

        # Check copper (has weight)
        cp = system.currency.denominations["cp"]
        assert cp.weight == 0.05

        # Check silver (no weight specified - should be None or default)
        sp = system.currency.denominations["sp"]
        assert hasattr(sp, "weight")  # Attribute should exist
        # Weight should be None since not specified in YAML

        # Check gold (has weight)
        gp = system.currency.denominations["gp"]
        assert gp.weight == 0.05

    def test_credits_parsing_edge_cases(self, temp_system_dir):
        """Test edge cases in credits parsing."""
        loader = SystemLoader()

        # Test credits with some fields missing
        system_dir = temp_system_dir / "credits_partial"
        system_dir.mkdir()

        system_data = {
            "id": "credits_partial",
            "kind": "system",
            "name": "Partial Credits Test",
            "credits": {
                "author": "Test Author"
                # Other fields are optional
            },
        }

        system_file = system_dir / "system.yaml"
        with open(system_file, "w") as f:
            yaml.dump(system_data, f)

        system = loader.load_system(system_dir)

        assert system.credits.author == "Test Author"
        # Other fields should be None or have defaults
        assert hasattr(system.credits, "license")
        assert hasattr(system.credits, "publisher")
        assert hasattr(system.credits, "source_url")


class TestSystemBuilderUtility:
    """Test the SystemBuilder utility class from conftest.py."""

    def test_basic_system_builder(self, system_builder):
        """Test basic system builder functionality."""
        system_dir = (
            system_builder("builder_test")
            .with_description("Test system built with builder")
            .build()
        )

        # Verify system.yaml was created
        system_file = system_dir / "system.yaml"
        assert system_file.exists()

        # Load and verify contents
        with open(system_file) as f:
            data = yaml.safe_load(f)

        assert data["id"] == "builder_test"
        assert data["kind"] == "system"
        assert data["name"] == "Test System: builder_test"
        assert data["description"] == "Test system built with builder"
        assert data["version"] == "1.0"

    def test_system_builder_with_currency(self, system_builder):
        """Test system builder with currency configuration."""
        denominations = {
            "gold": {"name": "gold piece", "symbol": "gp", "value": 1, "weight": 0.1}
        }

        system_dir = (
            system_builder("currency_builder_test")
            .with_currency("gold", denominations)
            .with_credits(author="Builder Test", license="MIT")
            .with_default_source("test_book")
            .build()
        )

        # Load the generated system
        loader = SystemLoader()
        system = loader.load_system(system_dir)

        assert system.currency.base_unit == "gold"
        assert len(system.currency.denominations) == 1
        assert system.credits.author == "Builder Test"
        assert system.default_source == "test_book"
