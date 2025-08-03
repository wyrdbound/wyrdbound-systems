"""
Tests for model definition functionality.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.models.model import (
    AttributeDefinition,
    ModelDefinition,
    ValidationRule,
)


class TestAttributeDefinition:
    """Test the AttributeDefinition dataclass."""

    def test_attribute_definition_defaults(self):
        """Test AttributeDefinition with default values."""
        attr = AttributeDefinition(type="str")

        assert attr.type == "str"
        assert attr.default is None
        assert attr.range is None
        assert attr.enum is None
        assert attr.derived is None
        assert attr.required is True
        assert attr.description is None

    def test_attribute_definition_all_fields(self):
        """Test AttributeDefinition with all fields populated."""
        attr = AttributeDefinition(
            type="int",
            default=10,
            range="1..20",
            enum=None,
            derived="{{ base_stat + modifier }}",
            required=False,
            description="A character attribute",
        )

        assert attr.type == "int"
        assert attr.default == 10
        assert attr.range == "1..20"
        assert attr.enum is None
        assert attr.derived == "{{ base_stat + modifier }}"
        assert attr.required is False
        assert attr.description == "A character attribute"

    def test_attribute_definition_enum(self):
        """Test AttributeDefinition with enum values."""
        attr = AttributeDefinition(
            type="str", enum=["small", "medium", "large"], default="medium"
        )

        assert attr.type == "str"
        assert attr.enum == ["small", "medium", "large"]
        assert attr.default == "medium"


class TestValidationRule:
    """Test the ValidationRule dataclass."""

    def test_validation_rule_creation(self):
        """Test ValidationRule creation."""
        rule = ValidationRule(
            expression="strength >= 8", message="Strength must be at least 8"
        )

        assert rule.expression == "strength >= 8"
        assert rule.message == "Strength must be at least 8"


class TestModelDefinition:
    """Test the ModelDefinition class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.basic_model = ModelDefinition(
            id="character", name="Character", description="A basic character model"
        )

        self.complex_model = ModelDefinition(
            id="character",
            name="Character",
            description="A complex character model",
            attributes={
                "name": AttributeDefinition(type="str", description="Character name"),
                "level": AttributeDefinition(type="int", range="1..20", default=1),
                "abilities": {
                    "strength": AttributeDefinition(type="int", range="3..18"),
                    "dexterity": AttributeDefinition(type="int", range="3..18"),
                },
                "size": AttributeDefinition(
                    type="str", enum=["tiny", "small", "medium", "large"]
                ),
                "optional_field": AttributeDefinition(type="str", required=False),
            },
            validations=[
                ValidationRule("level > 0", "Level must be positive"),
                ValidationRule("name.length > 0", "Name cannot be empty"),
            ],
        )

    def test_model_definition_defaults(self):
        """Test ModelDefinition with default values."""
        model = ModelDefinition(id="test", name="Test Model")

        assert model.id == "test"
        assert model.name == "Test Model"
        assert model.kind == "model"
        assert model.description is None
        assert model.version == 1
        assert model.extends == []
        assert model.attributes == {}
        assert model.validations == []

    def test_model_definition_all_fields(self):
        """Test ModelDefinition with all fields."""
        attributes = {"name": AttributeDefinition(type="str")}
        validations = [ValidationRule("name != ''", "Name required")]

        model = ModelDefinition(
            id="character",
            name="Character",
            kind="model",
            description="A character model",
            version=2,
            extends=["base_entity"],
            attributes=attributes,
            validations=validations,
        )

        assert model.id == "character"
        assert model.name == "Character"
        assert model.kind == "model"
        assert model.description == "A character model"
        assert model.version == 2
        assert model.extends == ["base_entity"]
        assert model.attributes == attributes
        assert model.validations == validations

    def test_get_attribute_simple(self):
        """Test getting a simple attribute."""
        attr = self.complex_model.get_attribute("name")

        assert attr is not None
        assert isinstance(attr, AttributeDefinition)
        assert attr.type == "str"
        assert attr.description == "Character name"

    def test_get_attribute_nested(self):
        """Test getting a nested attribute."""
        attr = self.complex_model.get_attribute("abilities.strength")

        assert attr is not None
        assert isinstance(attr, AttributeDefinition)
        assert attr.type == "int"
        assert attr.range == "3..18"

    def test_get_attribute_nonexistent(self):
        """Test getting a non-existent attribute."""
        attr = self.complex_model.get_attribute("nonexistent")
        assert attr is None

        attr = self.complex_model.get_attribute("abilities.nonexistent")
        assert attr is None

    def test_get_attribute_dict_conversion(self):
        """Test that dict attributes are converted to AttributeDefinition."""
        model = ModelDefinition(
            id="test",
            name="Test",
            attributes={"dict_attr": {"type": "int", "default": 5, "required": False}},
        )

        attr = model.get_attribute("dict_attr")

        assert attr is not None
        assert isinstance(attr, AttributeDefinition)
        assert attr.type == "int"
        assert attr.default == 5
        assert attr.required is False

    def test_get_all_attributes_simple(self):
        """Test getting all attributes from a simple model."""
        model = ModelDefinition(
            id="simple",
            name="Simple",
            attributes={
                "name": AttributeDefinition(type="str"),
                "age": AttributeDefinition(type="int"),
            },
        )

        all_attrs = model.get_all_attributes()

        assert len(all_attrs) == 2
        assert "name" in all_attrs
        assert "age" in all_attrs
        assert all_attrs["name"].type == "str"
        assert all_attrs["age"].type == "int"

    def test_get_all_attributes_nested(self):
        """Test getting all attributes including nested ones."""
        all_attrs = self.complex_model.get_all_attributes()

        assert len(all_attrs) >= 5
        assert "name" in all_attrs
        assert "level" in all_attrs
        assert "abilities.strength" in all_attrs
        assert "abilities.dexterity" in all_attrs
        assert "size" in all_attrs
        assert "optional_field" in all_attrs

    def test_get_all_attributes_dict_conversion(self):
        """Test that dict attributes are converted in get_all_attributes."""
        model = ModelDefinition(
            id="test",
            name="Test",
            attributes={
                "dict_attr": {"type": "str", "default": "test"},
                "nested": {"inner": {"type": "int", "range": "1..10"}},
            },
        )

        all_attrs = model.get_all_attributes()

        assert "dict_attr" in all_attrs
        assert "nested.inner" in all_attrs
        assert isinstance(all_attrs["dict_attr"], AttributeDefinition)
        assert isinstance(all_attrs["nested.inner"], AttributeDefinition)
        assert all_attrs["dict_attr"].type == "str"
        assert all_attrs["nested.inner"].range == "1..10"

    def test_validate_instance_required_fields(self):
        """Test instance validation for required fields."""
        instance = {
            "name": "Test Character",
            "level": 5,
            "abilities": {"strength": 15, "dexterity": 12},
            "size": "medium",
        }

        errors = self.complex_model.validate_instance(instance)
        assert len(errors) == 0  # All required fields present

    def test_validate_instance_missing_required(self):
        """Test instance validation with missing required fields."""
        instance = {
            "level": 5,
            # Missing name, abilities
        }

        errors = self.complex_model.validate_instance(instance)

        # Should have errors for missing required fields
        error_messages = " ".join(errors)
        assert "name" in error_messages
        assert "abilities.strength" in error_messages
        assert "abilities.dexterity" in error_messages

    def test_validate_instance_optional_fields(self):
        """Test that optional fields don't cause validation errors."""
        instance = {
            "name": "Test Character",
            "level": 5,
            "abilities": {"strength": 15, "dexterity": 12},
            "size": "medium",
            # optional_field is missing but that's OK
        }

        errors = self.complex_model.validate_instance(instance)
        assert len(errors) == 0

    def test_validate_instance_type_validation(self):
        """Test instance validation for type checking."""
        instance = {
            "name": 123,  # Should be string
            "level": "five",  # Should be int
            "abilities": {"strength": 15.5, "dexterity": 12},  # strength should be int
            "size": "medium",
        }

        errors = self.complex_model.validate_instance(instance)

        error_messages = " ".join(errors)
        assert "name" in error_messages and "string" in error_messages
        assert "level" in error_messages and "integer" in error_messages

    def test_validate_instance_enum_validation(self):
        """Test instance validation for enum values."""
        instance = {
            "name": "Test Character",
            "level": 5,
            "abilities": {"strength": 15, "dexterity": 12},
            "size": "huge",  # Not in enum
        }

        errors = self.complex_model.validate_instance(instance)

        error_messages = " ".join(errors)
        assert "size" in error_messages
        assert "tiny, small, medium, large" in error_messages

    def test_validate_instance_range_validation(self):
        """Test instance validation for range checking."""
        instance = {
            "name": "Test Character",
            "level": 25,  # Out of range (1..20)
            "abilities": {
                "strength": 2,
                "dexterity": 12,
            },  # strength out of range (3..18)
            "size": "medium",
        }

        errors = self.complex_model.validate_instance(instance)

        error_messages = " ".join(errors)
        assert "level" in error_messages
        assert "abilities.strength" in error_messages

    def test_has_nested_value(self):
        """Test _has_nested_value method."""
        instance = {"name": "Test", "abilities": {"strength": 15}}

        assert self.complex_model._has_nested_value(instance, "name")
        assert self.complex_model._has_nested_value(instance, "abilities.strength")
        assert not self.complex_model._has_nested_value(instance, "nonexistent")
        assert not self.complex_model._has_nested_value(
            instance, "abilities.nonexistent"
        )

    def test_get_nested_value(self):
        """Test _get_nested_value method."""
        instance = {
            "name": "Test",
            "abilities": {"strength": 15, "dexterity": 12},
            "level": 5,
        }

        assert self.complex_model._get_nested_value(instance, "name") == "Test"
        assert (
            self.complex_model._get_nested_value(instance, "abilities.strength") == 15
        )
        assert self.complex_model._get_nested_value(instance, "level") == 5

        with pytest.raises(KeyError):
            self.complex_model._get_nested_value(instance, "nonexistent")

    def test_validate_attribute_value_types(self):
        """Test _validate_attribute_value for different types."""
        int_attr = AttributeDefinition(type="int")
        str_attr = AttributeDefinition(type="str")
        float_attr = AttributeDefinition(type="float")
        bool_attr = AttributeDefinition(type="bool")

        # Valid values
        assert (
            len(self.complex_model._validate_attribute_value("test", 5, int_attr)) == 0
        )
        assert (
            len(self.complex_model._validate_attribute_value("test", "hello", str_attr))
            == 0
        )
        assert (
            len(self.complex_model._validate_attribute_value("test", 3.14, float_attr))
            == 0
        )
        assert (
            len(self.complex_model._validate_attribute_value("test", 5, float_attr))
            == 0
        )  # int accepted for float
        assert (
            len(self.complex_model._validate_attribute_value("test", True, bool_attr))
            == 0
        )

        # Invalid values
        assert (
            len(
                self.complex_model._validate_attribute_value(
                    "test", "not_int", int_attr
                )
            )
            > 0
        )
        assert (
            len(self.complex_model._validate_attribute_value("test", 123, str_attr)) > 0
        )
        assert (
            len(
                self.complex_model._validate_attribute_value(
                    "test", "not_float", float_attr
                )
            )
            > 0
        )
        assert (
            len(
                self.complex_model._validate_attribute_value(
                    "test", "not_bool", bool_attr
                )
            )
            > 0
        )

    def test_validate_range(self):
        """Test _validate_range method."""
        # Valid ranges
        assert len(self.complex_model._validate_range("test", 10, "1..20")) == 0
        assert len(self.complex_model._validate_range("test", 1, "1..20")) == 0
        assert len(self.complex_model._validate_range("test", 20, "1..20")) == 0
        assert len(self.complex_model._validate_range("test", 15, "10..")) == 0
        assert len(self.complex_model._validate_range("test", 5, "..10")) == 0
        assert len(self.complex_model._validate_range("test", 5, "5")) == 0

        # Invalid ranges
        assert len(self.complex_model._validate_range("test", 0, "1..20")) > 0
        assert len(self.complex_model._validate_range("test", 21, "1..20")) > 0
        assert len(self.complex_model._validate_range("test", 5, "10..")) > 0
        assert len(self.complex_model._validate_range("test", 15, "..10")) > 0
        assert len(self.complex_model._validate_range("test", 6, "5")) > 0

        # Invalid range specification
        assert len(self.complex_model._validate_range("test", 5, "invalid")) > 0

    def test_model_validation_valid(self):
        """Test model definition validation for valid model."""
        errors = self.complex_model.validate()
        assert len(errors) == 0

    def test_model_validation_invalid(self):
        """Test model definition validation for invalid model."""
        invalid_model = ModelDefinition(
            id="",  # Invalid empty ID
            name="",  # Invalid empty name
            kind="invalid",  # Invalid kind
        )

        errors = invalid_model.validate()

        assert len(errors) >= 3
        error_messages = " ".join(errors)
        assert "ID is required" in error_messages
        assert "name is required" in error_messages
        assert "kind must be 'model'" in error_messages


class TestModelDefinitionIntegration:
    """Integration tests for ModelDefinition with realistic scenarios."""

    def test_rpg_character_model(self):
        """Test a realistic RPG character model."""
        character_model = ModelDefinition(
            id="dnd_character",
            name="D&D Character",
            description="A Dungeons & Dragons character",
            attributes={
                "name": AttributeDefinition(type="str", description="Character name"),
                "race": AttributeDefinition(
                    type="str", enum=["human", "elf", "dwarf", "halfling"]
                ),
                "class": AttributeDefinition(
                    type="str", enum=["fighter", "wizard", "rogue", "cleric"]
                ),
                "level": AttributeDefinition(type="int", range="1..20", default=1),
                "abilities": {
                    "strength": AttributeDefinition(type="int", range="3..18"),
                    "dexterity": AttributeDefinition(type="int", range="3..18"),
                    "constitution": AttributeDefinition(type="int", range="3..18"),
                    "intelligence": AttributeDefinition(type="int", range="3..18"),
                    "wisdom": AttributeDefinition(type="int", range="3..18"),
                    "charisma": AttributeDefinition(type="int", range="3..18"),
                },
                "hit_points": AttributeDefinition(
                    type="int", range="1..", derived="{{ level * 8 + con_modifier }}"
                ),
                "armor_class": AttributeDefinition(
                    type="int",
                    range="1..",
                    derived="{{ 10 + dex_modifier + armor_bonus }}",
                ),
                "background": AttributeDefinition(type="str", required=False),
            },
        )

        # Valid character
        valid_character = {
            "name": "Aragorn",
            "race": "human",
            "class": "fighter",
            "level": 5,
            "abilities": {
                "strength": 16,
                "dexterity": 14,
                "constitution": 15,
                "intelligence": 12,
                "wisdom": 13,
                "charisma": 14,
            },
            "hit_points": 45,
            "armor_class": 16,
        }

        errors = character_model.validate_instance(valid_character)
        assert len(errors) == 0

        # Invalid character
        invalid_character = {
            "name": "Invalid",
            "race": "orc",  # Not in enum
            "level": 25,  # Out of range
            "abilities": {
                "strength": 2,  # Out of range
                "dexterity": 14,
                # Missing required abilities
            },
        }

        errors = character_model.validate_instance(invalid_character)
        assert len(errors) > 0

    def test_nested_model_attributes(self):
        """Test deeply nested model attributes."""
        model = ModelDefinition(
            id="complex",
            name="Complex Model",
            attributes={
                "player": {
                    "info": {
                        "name": AttributeDefinition(type="str"),
                        "email": AttributeDefinition(type="str", required=False),
                    },
                    "preferences": {
                        "theme": AttributeDefinition(
                            type="str", enum=["light", "dark"]
                        ),
                        "volume": AttributeDefinition(type="float", range="0..1"),
                    },
                }
            },
        )

        all_attrs = model.get_all_attributes()

        assert "player.info.name" in all_attrs
        assert "player.info.email" in all_attrs
        assert "player.preferences.theme" in all_attrs
        assert "player.preferences.volume" in all_attrs

        # Test validation
        instance = {
            "player": {
                "info": {"name": "Alice"},
                "preferences": {"theme": "dark", "volume": 0.8},
            }
        }

        errors = model.validate_instance(instance)
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
