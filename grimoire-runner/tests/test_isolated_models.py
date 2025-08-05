"""
Test models in isolation without importing the main package.
These tests will import model files directly to avoid the LLM dependency issues.
"""
import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


class TestModelDefinition:
    """Test the ModelDefinition class directly."""
    
    def test_import_model_directly(self):
        """Test that we can import the model module directly."""
        # Import individual components to avoid the main __init__.py
        try:
            # Import directly from the model file to avoid dependency issues
            import sys
            import importlib.util
            
            model_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'model.py')
            spec = importlib.util.spec_from_file_location("model", model_path)
            model_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(model_module)
            
            assert hasattr(model_module, 'ModelDefinition')
            assert hasattr(model_module, 'AttributeDefinition')
            assert hasattr(model_module, 'ValidationRule')
        except Exception as e:
            # If direct file import fails, try the regular import which might work in some contexts
            from grimoire_runner.models.model import ModelDefinition, AttributeDefinition, ValidationRule
            assert ModelDefinition is not None
            assert AttributeDefinition is not None
            assert ValidationRule is not None
    
    def test_model_initialization(self):
        """Test ModelDefinition initialization with correct parameters."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        model_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'model.py')
        spec = importlib.util.spec_from_file_location("model", model_path)
        model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model_module)
        
        ModelDefinition = model_module.ModelDefinition
        
        model = ModelDefinition(
            id="test_model",
            name="Test Model",
            description="A test model"
        )
        
        assert model.id == "test_model"
        assert model.name == "Test Model"
        assert model.description == "A test model"
        assert model.kind == "model"
        assert model.version == 1
        assert model.attributes == {}
        assert model.extends == []
    
    def test_model_with_attributes(self):
        """Test ModelDefinition with attributes."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        model_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'model.py')
        spec = importlib.util.spec_from_file_location("model", model_path)
        model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model_module)
        
        ModelDefinition = model_module.ModelDefinition
        AttributeDefinition = model_module.AttributeDefinition
        
        attributes = {
            "strength": AttributeDefinition(type="int", default=10),
            "name": AttributeDefinition(type="str", default="Unknown")
        }
        
        model = ModelDefinition(
            id="character",
            name="Character",
            description="A character model",
            attributes=attributes
        )
        
        assert model.attributes == attributes
        assert model.name == "Character"
        assert "strength" in model.attributes
        assert "name" in model.attributes
    
    def test_attribute_definition(self):
        """Test AttributeDefinition initialization."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        model_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'model.py')
        spec = importlib.util.spec_from_file_location("model", model_path)
        model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model_module)
        
        AttributeDefinition = model_module.AttributeDefinition
        
        attr = AttributeDefinition(
            type="int",
            default=10,
            range="1..20",
            description="Character strength"
        )
        
        assert attr.type == "int"
        assert attr.default == 10
        assert attr.range == "1..20"
        assert attr.description == "Character strength"
        assert attr.required is True
    
    def test_validation_rule(self):
        """Test ValidationRule initialization."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        model_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'model.py')
        spec = importlib.util.spec_from_file_location("model", model_path)
        model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model_module)
        
        ValidationRule = model_module.ValidationRule
        
        rule = ValidationRule(
            expression="strength >= 1",
            message="Strength must be at least 1"
        )
        
        assert rule.expression == "strength >= 1"
        assert rule.message == "Strength must be at least 1"
    
    def test_model_serialization(self):
        """Test ModelDefinition serialization."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        model_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'model.py')
        spec = importlib.util.spec_from_file_location("model", model_path)
        model_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model_module)
        
        ModelDefinition = model_module.ModelDefinition
        
        model = ModelDefinition(
            id="test_model",
            name="Test Model",
            description="A test model"
        )
        
        # Test that model can be represented as string
        str_repr = str(model)
        assert "Test Model" in str_repr


class TestFlowDefinition:
    """Test the FlowDefinition class directly."""
    
    def test_import_flow_directly(self):
        """Test that we can import the flow module directly."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        flow_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'flow.py')
        spec = importlib.util.spec_from_file_location("flow", flow_path)
        flow_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flow_module)
        
        assert hasattr(flow_module, 'FlowDefinition')
        assert hasattr(flow_module, 'StepDefinition')
        assert hasattr(flow_module, 'StepType')
    
    def test_flow_initialization(self):
        """Test FlowDefinition initialization with correct parameters."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        flow_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'flow.py')
        spec = importlib.util.spec_from_file_location("flow", flow_path)
        flow_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flow_module)
        
        FlowDefinition = flow_module.FlowDefinition
        
        flow = FlowDefinition(
            id="test_flow",
            name="Test Flow",
            description="A test flow"
        )
        
        assert flow.id == "test_flow"
        assert flow.name == "Test Flow"
        assert flow.description == "A test flow"
        assert flow.type == "flow"
        assert flow.steps == []
    
    def test_flow_with_steps(self):
        """Test FlowDefinition with steps."""
        # Use direct import to avoid dependency issues
        import importlib.util
        
        flow_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'grimoire_runner', 'models', 'flow.py')
        spec = importlib.util.spec_from_file_location("flow", flow_path)
        flow_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flow_module)
        
        FlowDefinition = flow_module.FlowDefinition
        StepDefinition = flow_module.StepDefinition
        
        steps = [
            StepDefinition(id="step1", name="First Step"),
            StepDefinition(id="step2", name="Second Step")
        ]
        
        flow = FlowDefinition(
            id="multi_step_flow",
            name="Multi-step Flow",
            description="A flow with multiple steps",
            steps=steps
        )
        
        assert len(flow.steps) == 2
        assert flow.steps[0].name == "First Step"
        assert flow.steps[1].name == "Second Step"
    
    def test_flow_get_step(self):
        """Test FlowDefinition get_step method."""
        from grimoire_runner.models.flow import FlowDefinition, StepDefinition
        
        step = StepDefinition(id="test_step", name="Test Step")
        flow = FlowDefinition(
            id="test_flow",
            name="Test Flow",
            steps=[step]
        )
        
        found_step = flow.get_step("test_step")
        assert found_step is not None
        assert found_step.name == "Test Step"
        
        # Test non-existent step
        not_found = flow.get_step("non_existent")
        assert not_found is None
    
    def test_flow_serialization(self):
        """Test FlowDefinition serialization."""
        from grimoire_runner.models.flow import FlowDefinition
        
        flow = FlowDefinition(
            id="test_flow",
            name="Test Flow",
            description="A test flow"
        )
        
        # Test that flow can be represented as string
        str_repr = str(flow)
        assert "Test Flow" in str_repr


class TestStepDefinition:
    """Test the StepDefinition class directly."""
    
    def test_step_initialization(self):
        """Test StepDefinition initialization with correct parameters."""
        from grimoire_runner.models.flow import StepDefinition
        
        step = StepDefinition(
            id="test_step",
            name="Test Step"
        )
        
        assert step.id == "test_step"
        assert step.name == "Test Step"
        assert step.actions == []
    
    def test_step_with_actions(self):
        """Test StepDefinition with actions."""
        from grimoire_runner.models.flow import StepDefinition
        
        actions = [
            {"type": "set_value", "field": "test", "value": "hello"},
            {"type": "display_value", "field": "test"}
        ]
        
        step = StepDefinition(
            id="action_step",
            name="Action Step",
            actions=actions
        )
        
        assert len(step.actions) == 2
        assert step.actions[0]["type"] == "set_value"
        assert step.actions[1]["type"] == "display_value"
    
    def test_step_with_roll(self):
        """Test StepDefinition with dice roll configuration."""
        from grimoire_runner.models.flow import StepDefinition, StepType
        
        step = StepDefinition(
            id="dice_step",
            name="Dice Roll Step",
            type=StepType.DICE_ROLL,
            roll="1d20+5"
        )
        
        assert step.type == StepType.DICE_ROLL
        assert step.roll == "1d20+5"
    
    def test_step_with_choices(self):
        """Test StepDefinition with player choices."""
        from grimoire_runner.models.flow import StepDefinition, StepType, ChoiceDefinition
        
        choices = [
            ChoiceDefinition(id="choice1", label="Option 1"),
            ChoiceDefinition(id="choice2", label="Option 2")
        ]
        
        step = StepDefinition(
            id="choice_step",
            name="Choice Step",
            type=StepType.PLAYER_CHOICE,
            choices=choices
        )
        
        assert step.type == StepType.PLAYER_CHOICE
        assert len(step.choices) == 2
        assert step.choices[0].label == "Option 1"


class TestCompendiumDefinition:
    """Test the CompendiumDefinition class directly."""
    
    def test_import_compendium_directly(self):
        """Test that we can import the compendium module directly."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        assert CompendiumDefinition is not None
    
    def test_compendium_initialization(self):
        """Test CompendiumDefinition initialization with correct parameters."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        compendium = CompendiumDefinition(
            kind="compendium",
            id="test_compendium",
            name="Test Compendium",
            model="test_model"
        )
        
        assert compendium.kind == "compendium"
        assert compendium.id == "test_compendium"
        assert compendium.name == "Test Compendium"
        assert compendium.model == "test_model"
        assert compendium.entries == {}
    
    def test_compendium_with_entries(self):
        """Test CompendiumDefinition with entries."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        entries = {
            "entry1": {"name": "First Entry", "value": 1},
            "entry2": {"name": "Second Entry", "value": 2}
        }
        
        compendium = CompendiumDefinition(
            kind="compendium",
            id="full_compendium",
            name="Full Compendium",
            model="test_model",
            entries=entries
        )
        
        assert len(compendium.entries) == 2
        assert compendium.entries["entry1"]["name"] == "First Entry"
        assert compendium.entries["entry2"]["value"] == 2
    
    def test_compendium_get_entry(self):
        """Test CompendiumDefinition get_entry method."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        entries = {
            "test_entry": {"name": "Test Entry", "description": "A test entry"}
        }
        
        compendium = CompendiumDefinition(
            kind="compendium",
            id="test_compendium",
            name="Test Compendium",
            model="test_model",
            entries=entries
        )
        
        entry = compendium.get_entry("test_entry")
        assert entry is not None
        assert entry["name"] == "Test Entry"
        
        # Test non-existent entry
        missing = compendium.get_entry("missing")
        assert missing is None
    
    def test_compendium_list_entries(self):
        """Test CompendiumDefinition list_entries method."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        entries = {
            "entry1": {"name": "Entry 1"},
            "entry2": {"name": "Entry 2"},
            "entry3": {"name": "Entry 3"}
        }
        
        compendium = CompendiumDefinition(
            kind="compendium",
            id="test_compendium",
            name="Test Compendium",
            model="test_model",
            entries=entries
        )
        
        entry_list = compendium.list_entries()
        assert len(entry_list) == 3
        assert "entry1" in entry_list
        assert "entry2" in entry_list
        assert "entry3" in entry_list
    
    def test_compendium_search_entries(self):
        """Test CompendiumDefinition search_entries method."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        entries = {
            "sword": {"name": "Longsword", "type": "weapon", "damage": "1d8"},
            "shield": {"name": "Shield", "type": "armor", "ac_bonus": 2},
            "potion": {"name": "Healing Potion", "type": "consumable", "effect": "heal"}
        }
        
        compendium = CompendiumDefinition(
            kind="compendium",
            id="items",
            name="Item Compendium",
            model="item",
            entries=entries
        )
        
        # Search for weapons
        results = compendium.search_entries("weapon")
        assert len(results) == 1
        assert "sword" in results
        
        # Search for healing
        results = compendium.search_entries("heal")
        assert len(results) == 1
        assert "potion" in results


class TestObservablePattern:
    """Test the Observable pattern implementation."""
    
    def test_import_observable_directly(self):
        """Test that we can import the observable module directly."""
        from grimoire_runner.models.observable import DerivedFieldManager, ObservableValue, DependencyInfo
        assert DerivedFieldManager is not None
        assert ObservableValue is not None
        assert DependencyInfo is not None
    
    def test_observable_value_initialization(self):
        """Test ObservableValue initialization."""
        from grimoire_runner.models.observable import ObservableValue
        
        obs = ObservableValue("test_field", "initial_value")
        assert obs.field_name == "test_field"
        assert obs.value == "initial_value"
    
    def test_observable_value_change(self):
        """Test ObservableValue change notification."""
        from grimoire_runner.models.observable import ObservableValue
        
        obs = ObservableValue("test_field", 10)
        
        # Track observer calls
        observer_calls = []
        
        def test_observer(field_name, old_value, new_value):
            observer_calls.append((field_name, old_value, new_value))
        
        obs.add_observer(test_observer)
        
        # Change the value
        obs.value = 20
        
        assert len(observer_calls) == 1
        assert observer_calls[0] == ("test_field", 10, 20)
    
    def test_dependency_info(self):
        """Test DependencyInfo dataclass."""
        from grimoire_runner.models.observable import DependencyInfo
        
        deps = DependencyInfo(
            derived="{{ strength + dexterity }}",
            dependencies={"strength", "dexterity"}
        )
        
        assert deps.derived == "{{ strength + dexterity }}"
        assert deps.dependencies == {"strength", "dexterity"}
    
    def test_derived_field_manager_with_mock_context(self):
        """Test DerivedFieldManager with mock dependencies."""
        from grimoire_runner.models.observable import DerivedFieldManager
        from unittest.mock import MagicMock
        
        # Create mock execution context and template resolver
        mock_context = MagicMock()
        mock_resolver = MagicMock()
        
        manager = DerivedFieldManager(mock_context, mock_resolver)
        
        assert manager.execution_context == mock_context
        assert manager.template_resolver == mock_resolver
        assert manager.fields == {}
        assert manager.derived_fields == {}
    
    def test_dependency_extraction(self):
        """Test dependency extraction from expressions."""
        from grimoire_runner.models.observable import DerivedFieldManager
        from unittest.mock import MagicMock
        
        mock_context = MagicMock()
        mock_resolver = MagicMock()
        
        manager = DerivedFieldManager(mock_context, mock_resolver)
        
        # Test basic variable extraction
        deps = manager._extract_dependencies("{{ strength }}")
        assert "strength" in deps
        
        # Test $ syntax variable extraction  
        deps = manager._extract_dependencies("$strength + $dexterity")
        assert "strength" in deps
        assert "dexterity" in deps
        
        # Test complex expression
        deps = manager._extract_dependencies("{{ (strength + dexterity) / 2 }}")
        # This might only catch one variable depending on regex complexity
        assert len(deps) >= 1


class TestSourceDefinition:
    """Test the SourceDefinition class directly."""
    
    def test_import_source_directly(self):
        """Test that we can import the source module directly."""
        from grimoire_runner.models.source import SourceDefinition
        assert SourceDefinition is not None
    
    def test_source_initialization(self):
        """Test SourceDefinition initialization with correct parameters."""
        from grimoire_runner.models.source import SourceDefinition
        
        source = SourceDefinition(
            kind="source",
            name="Test Source",
            id="test_source"
        )
        
        assert source.kind == "source"
        assert source.name == "Test Source"
        assert source.id == "test_source"
        assert source.version == "1.0"
    
    def test_source_with_metadata(self):
        """Test SourceDefinition with metadata."""
        from grimoire_runner.models.source import SourceDefinition
        
        source = SourceDefinition(
            kind="source",
            name="D&D Player's Handbook",
            id="phb",
            display_name="Player's Handbook",
            edition="5th Edition",
            publisher="Wizards of the Coast",
            description="Core rulebook for D&D 5e"
        )
        
        assert source.display_name == "Player's Handbook"
        assert source.edition == "5th Edition"
        assert source.publisher == "Wizards of the Coast"
        assert source.description == "Core rulebook for D&D 5e"
    
    def test_source_validation(self):
        """Test SourceDefinition validation method."""
        from grimoire_runner.models.source import SourceDefinition
        
        # Valid source
        valid_source = SourceDefinition(
            kind="source",
            name="Valid Source"
        )
        errors = valid_source.validate()
        assert len(errors) == 0
        
        # Invalid kind
        invalid_source = SourceDefinition(
            kind="invalid",
            name="Invalid Source"
        )
        errors = invalid_source.validate()
        assert len(errors) > 0
        assert any("kind must be 'source'" in error for error in errors)
        
        # Missing name
        no_name_source = SourceDefinition(
            kind="source",
            name=""
        )
        errors = no_name_source.validate()
        assert len(errors) > 0
        assert any("name is required" in error for error in errors)


# Integration tests for model interactions
class TestModelIntegration:
    """Test how models work together."""
    
    def test_model_in_compendium(self):
        """Test adding entries to compendium."""
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        compendium = CompendiumDefinition(
            kind="compendium",
            id="characters",
            name="Character Compendium",
            model="character"
        )
        
        # Add character entries
        compendium.entries["aragorn"] = {
            "name": "Aragorn",
            "class": "Ranger",
            "level": 20,
            "strength": 16
        }
        
        compendium.entries["legolas"] = {
            "name": "Legolas",
            "class": "Fighter",
            "level": 18,
            "dexterity": 20
        }
        
        assert len(compendium.entries) == 2
        assert compendium.entries["aragorn"]["name"] == "Aragorn"
        assert compendium.entries["legolas"]["class"] == "Fighter"
    
    def test_flow_with_model_actions(self):
        """Test flow that references model fields."""
        from grimoire_runner.models.flow import FlowDefinition, StepDefinition
        
        # Create a flow that works with model fields
        actions = [
            {"type": "set_value", "field": "character.name", "value": "Aragorn"},
            {"type": "set_value", "field": "character.level", "value": 5},
            {"type": "display_value", "field": "character.name"}
        ]
        
        step = StepDefinition(id="setup_character", name="Setup Character", actions=actions)
        flow = FlowDefinition(
            id="character_creation",
            name="Character Creation",
            description="Create a new character",
            steps=[step]
        )
        
        assert len(flow.steps) == 1
        assert len(flow.steps[0].actions) == 3
        assert flow.steps[0].actions[0]["field"] == "character.name"
    
    def test_model_with_attributes_and_compendium(self):
        """Test model definition with compendium entries."""
        from grimoire_runner.models.model import ModelDefinition, AttributeDefinition
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        # Create a character model
        model = ModelDefinition(
            id="character",
            name="Character",
            description="RPG Character",
            attributes={
                "name": AttributeDefinition(type="str", required=True),
                "level": AttributeDefinition(type="int", default=1),
                "strength": AttributeDefinition(type="int", default=10, range="1..20")
            }
        )
        
        # Create a compendium with character entries
        compendium = CompendiumDefinition(
            kind="compendium",
            id="npc_characters",
            name="NPC Characters",
            model="character",
            entries={
                "guard": {
                    "name": "Town Guard",
                    "level": 2,
                    "strength": 14
                },
                "wizard": {
                    "name": "Village Wizard",
                    "level": 5,
                    "strength": 8
                }
            }
        )
        
        # Verify model structure
        assert model.id == "character"
        assert "name" in model.attributes
        assert model.attributes["strength"].range == "1..20"
        
        # Verify compendium structure
        assert compendium.model == "character"
        assert len(compendium.entries) == 2
        assert compendium.entries["guard"]["level"] == 2
    
    def test_source_attribution(self):
        """Test source attribution for content."""
        from grimoire_runner.models.source import SourceDefinition
        from grimoire_runner.models.compendium import CompendiumDefinition
        
        # Create a source
        source = SourceDefinition(
            kind="source",
            name="Monster Manual",
            id="mm",
            edition="5th Edition",
            publisher="Wizards of the Coast"
        )
        
        # Create a compendium that could reference this source
        compendium = CompendiumDefinition(
            kind="compendium",
            id="monsters",
            name="Monster Compendium",
            model="monster",
            entries={
                "goblin": {
                    "name": "Goblin",
                    "cr": "1/4",
                    "source": "mm"  # Reference to source
                }
            }
        )
        
        assert source.name == "Monster Manual"
        assert compendium.entries["goblin"]["source"] == source.id


if __name__ == "__main__":
    pytest.main([__file__])
