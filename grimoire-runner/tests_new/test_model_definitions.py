"""
Tests for GRIMOIRE model definition functionality.

This module tests model definition capabilities, focusing on:
- All attribute types (str, int, float, bool, roll, list, map)
- Range and enum constraints
- Model inheritance (extends)
- Validation rules
- Derived attributes
- Optional attributes
- Model references and nested structures
"""

import pytest
from pathlib import Path
import yaml
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.models.model import ModelDefinition, AttributeDefinition, ValidationRule


class TestBasicModelLoading:
    """Test basic model loading functionality."""

    def test_load_system_with_models(self, test_systems_dir):
        """Test loading a system that contains model definitions."""
        loader = SystemLoader()
        
        model_types_path = test_systems_dir / "model_types"
        system = loader.load_system(model_types_path)
        
        # Verify system loaded
        assert system.id == "model_types"
        
        # Verify models were loaded
        assert len(system.models) == 3
        assert "basic_character" in system.models
        assert "item" in system.models 
        assert "container" in system.models

    def test_basic_model_structure(self, test_systems_dir):
        """Test basic model structure and metadata."""
        loader = SystemLoader()
        
        model_types_path = test_systems_dir / "model_types"
        system = loader.load_system(model_types_path)
        
        character_model = system.models["basic_character"]
        
        # Verify model metadata
        assert character_model.id == "basic_character"
        assert character_model.kind == "model"
        assert character_model.name == "Basic Character"
        assert character_model.description == "Simple character model testing basic attribute types"
        
        # Verify attributes exist
        assert "name" in character_model.attributes
        assert "level" in character_model.attributes
        assert "hit_points" in character_model.attributes
        assert "weight" in character_model.attributes
        assert "is_alive" in character_model.attributes
        assert "hit_dice" in character_model.attributes


class TestAttributeTypes:
    """Test all supported attribute types."""

    def test_string_attributes(self, test_systems_dir):
        """Test string attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        character_model = system.models["basic_character"]
        
        # Get attribute using the model's get_attribute method
        name_attr = character_model.get_attribute("name")
        assert name_attr is not None
        assert name_attr.type == "str"
        assert name_attr.default == "Unnamed Character"
        
        description_attr = character_model.get_attribute("description")
        assert description_attr is not None
        assert description_attr.type == "str"
        assert description_attr.default is None  # No default specified

    def test_integer_attributes(self, test_systems_dir):
        """Test integer attribute definitions with ranges."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        character_model = system.models["basic_character"]
        
        # Test level with bounded range
        level_attr = character_model.get_attribute("level")
        assert level_attr is not None
        assert level_attr.type == "int"
        assert level_attr.range == "1..20"
        assert level_attr.default == 1
        
        # Test hit_points with open-ended range
        hp_attr = character_model.get_attribute("hit_points")
        assert hp_attr is not None
        assert hp_attr.type == "int"
        assert hp_attr.range == "1.."
        assert hp_attr.default is None  # No default specified

    def test_float_attributes(self, test_systems_dir):
        """Test float attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        character_model = system.models["basic_character"]
        weight_attr = character_model.get_attribute("weight")
        
        assert weight_attr is not None
        assert weight_attr.type == "float"
        assert weight_attr.range == "0.1.."
        assert weight_attr.default == 150.0

    def test_boolean_attributes(self, test_systems_dir):
        """Test boolean attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        character_model = system.models["basic_character"]
        
        # Boolean with default
        alive_attr = character_model.get_attribute("is_alive")
        assert alive_attr is not None
        assert alive_attr.type == "bool"
        assert alive_attr.default == True
        
        # Boolean without default
        pc_attr = character_model.get_attribute("is_player_character")
        assert pc_attr is not None
        assert pc_attr.type == "bool"
        assert pc_attr.default is None  # No default specified

    def test_roll_attributes(self, test_systems_dir):
        """Test roll attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        character_model = system.models["basic_character"]
        hit_dice_attr = character_model.get_attribute("hit_dice")
        
        assert hit_dice_attr is not None
        assert hit_dice_attr.type == "roll"
        assert hit_dice_attr.default == "1d8"

    def test_list_attributes(self, test_systems_dir):
        """Test list attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        item_model = system.models["item"]
        tags_attr = item_model.get_attribute("tags")
        
        assert tags_attr is not None
        assert tags_attr.type == "list"
        assert tags_attr.of == "str"

    def test_map_attributes(self, test_systems_dir):
        """Test map attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        item_model = system.models["item"]
        properties_attr = item_model.get_attribute("properties")
        
        assert properties_attr is not None
        assert properties_attr.type == "map"

    def test_model_reference_attributes(self, test_systems_dir):
        """Test attributes that reference other models."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_types")
        
        container_model = system.models["container"]
        contents_attr = container_model.get_attribute("contents")
        
        assert contents_attr is not None
        assert contents_attr.type == "list"
        assert contents_attr.of == "item"


class TestModelInheritance:
    """Test model inheritance functionality."""

    def test_load_inheritance_system(self, test_systems_dir):
        """Test loading system with model inheritance."""
        loader = SystemLoader()
        
        inheritance_path = test_systems_dir / "model_inheritance"
        system = loader.load_system(inheritance_path)
        
        # Verify all models loaded
        assert len(system.models) == 3
        assert "base_entity" in system.models
        assert "character" in system.models
        assert "weapon" in system.models

    def test_extends_relationship(self, test_systems_dir):
        """Test that extends relationships are parsed correctly."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_inheritance")
        
        character_model = system.models["character"]
        
        # Verify extends is parsed
        assert character_model.extends == ["base_entity"]
        
        # Verify character has its own attributes
        assert "level" in character_model.attributes
        assert "hit_points" in character_model.attributes
        assert "class_name" in character_model.attributes

    def test_enum_constraints(self, test_systems_dir):
        """Test enum constraint parsing."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_inheritance")
        
        character_model = system.models["character"]
        class_attr = character_model.get_attribute("class_name")
        
        assert class_attr is not None
        assert class_attr.type == "str"
        assert class_attr.enum == ["fighter", "wizard", "rogue", "cleric"]

    def test_multiple_extending_models(self, test_systems_dir):
        """Test that multiple models can extend the same base."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_inheritance")
        
        character_model = system.models["character"]
        weapon_model = system.models["weapon"]
        
        # Both should extend base_entity
        assert character_model.extends == ["base_entity"]
        assert weapon_model.extends == ["base_entity"]
        
        # But have different specific attributes
        assert "level" in character_model.attributes
        assert "damage" in weapon_model.attributes
        assert "level" not in weapon_model.attributes
        assert "damage" not in character_model.attributes


class TestValidationRules:
    """Test model validation rules and derived attributes."""

    def test_load_validation_system(self, test_systems_dir):
        """Test loading system with validation rules."""
        loader = SystemLoader()
        
        validation_path = test_systems_dir / "model_validations"
        system = loader.load_system(validation_path)
        
        assert "validated_character" in system.models

    def test_derived_attributes(self, test_systems_dir):
        """Test derived attribute definitions."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_validations")
        
        character_model = system.models["validated_character"]
        
        # Test arithmetic derived attribute
        ac_attr = character_model.get_attribute("armor_class")
        assert ac_attr is not None
        assert ac_attr.type == "int"
        assert ac_attr.derived == "$.armor_class_base + $.dexterity_modifier"
        
        # Test boolean derived attribute
        unconscious_attr = character_model.get_attribute("is_unconscious")
        assert unconscious_attr is not None
        assert unconscious_attr.type == "bool"
        assert unconscious_attr.derived == "$.current_hit_points <= 0"

    def test_validation_rules(self, test_systems_dir):
        """Test validation rule parsing."""
        loader = SystemLoader()
        system = loader.load_system(test_systems_dir / "model_validations")
        
        character_model = system.models["validated_character"]
        
        # Should have validation rules
        assert len(character_model.validations) == 2
        
        # Check first validation rule
        hp_validation = character_model.validations[0]
        assert hp_validation.expression == "$.current_hit_points <= $.max_hit_points"
        assert hp_validation.message == "Current HP cannot exceed maximum HP"
        
        # Check second validation rule
        name_validation = character_model.validations[1]
        assert name_validation.expression == "$.name.length > 0"
        assert name_validation.message == "Character name cannot be empty"


class TestModelLoadingEdgeCases:
    """Test edge cases and error handling in model loading."""

    def test_missing_required_fields(self, temp_system_dir):
        """Test error handling for models missing required fields."""
        loader = SystemLoader()
        
        # Create system with invalid model (missing 'id')
        system_dir = temp_system_dir / "invalid_model"
        system_dir.mkdir()
        models_dir = system_dir / "models"
        models_dir.mkdir()
        
        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, 'w') as f:
            yaml.dump({
                "id": "invalid_model",
                "kind": "system",
                "name": "Invalid Model Test"
            }, f)
        
        # Create invalid model (missing id field)
        model_file = models_dir / "invalid.yaml"
        with open(model_file, 'w') as f:
            yaml.dump({
                "kind": "model",
                "name": "Invalid Model",
                "attributes": {}
            }, f)
        
        # Should handle the error gracefully
        system = loader.load_system(system_dir)
        # The model should not be loaded due to missing id
        assert "invalid" not in system.models

    def test_optional_attribute_field(self, temp_system_dir):
        """Test optional attribute functionality."""
        loader = SystemLoader()
        
        system_dir = temp_system_dir / "optional_attrs"
        system_dir.mkdir()
        models_dir = system_dir / "models"
        models_dir.mkdir()
        
        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, 'w') as f:
            yaml.dump({
                "id": "optional_attrs",
                "kind": "system",
                "name": "Optional Attributes Test"
            }, f)
        
        # Create model with optional attribute
        model_file = models_dir / "test.yaml"
        with open(model_file, 'w') as f:
            yaml.dump({
                "id": "test",
                "kind": "model",
                "name": "Test Model",
                "attributes": {
                    "required_field": {
                        "type": "str"
                    },
                    "optional_field": {
                        "type": "str",
                        "optional": True
                    }
                }
            }, f)
        
        system = loader.load_system(system_dir)
        test_model = system.models["test"]
        
        required_attr = test_model.get_attribute("required_field")
        optional_attr = test_model.get_attribute("optional_field")
        
        assert required_attr is not None
        assert required_attr.type == "str"
        assert optional_attr is not None
        assert optional_attr.type == "str"
        assert optional_attr.optional == True

    def test_empty_model_attributes(self, temp_system_dir):
        """Test model with no attributes."""
        loader = SystemLoader()
        
        system_dir = temp_system_dir / "empty_model"
        system_dir.mkdir()
        models_dir = system_dir / "models"
        models_dir.mkdir()
        
        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, 'w') as f:
            yaml.dump({
                "id": "empty_model",
                "kind": "system",
                "name": "Empty Model Test"
            }, f)
        
        # Create model with empty attributes
        model_file = models_dir / "empty.yaml"
        with open(model_file, 'w') as f:
            yaml.dump({
                "id": "empty",
                "kind": "model",
                "name": "Empty Model",
                "attributes": {}
            }, f)
        
        system = loader.load_system(system_dir)
        empty_model = system.models["empty"]
        
        assert empty_model.id == "empty"
        assert empty_model.attributes == {}


class TestModelBuilderUtility:
    """Test utility functions for creating models in tests."""

    def test_create_simple_model_yaml(self, temp_system_dir):
        """Test creating a simple model programmatically."""
        # This tests our ability to create models for testing
        model_data = {
            "id": "test_model",
            "kind": "model", 
            "name": "Test Model",
            "attributes": {
                "name": {"type": "str"},
                "value": {"type": "int", "default": 0}
            }
        }
        
        system_dir = temp_system_dir / "model_builder_test"
        system_dir.mkdir()
        models_dir = system_dir / "models"
        models_dir.mkdir()
        
        # Create system.yaml
        system_file = system_dir / "system.yaml"
        with open(system_file, 'w') as f:
            yaml.dump({
                "id": "model_builder_test",
                "kind": "system",
                "name": "Model Builder Test"
            }, f)
        
        # Create model
        model_file = models_dir / "test_model.yaml"
        with open(model_file, 'w') as f:
            yaml.dump(model_data, f)
        
        # Test loading
        loader = SystemLoader()
        system = loader.load_system(system_dir)
        
        test_model = system.models["test_model"]
        assert test_model.id == "test_model"
        assert test_model.name == "Test Model"
        assert "name" in test_model.attributes
        assert "value" in test_model.attributes
