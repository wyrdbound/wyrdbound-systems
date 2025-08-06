"""
Test flow definition functionality.

This tests the flow definition system including:
- Flow structure loading and validation
- Step definition types and validation
- Input/output parameter definitions
- Complex flow features (conditions, actions, etc.)
- Integration with other system components

Tests are organized by complexity following the testing strategy.
"""

import pytest
from pathlib import Path
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.models.flow import (
    FlowDefinition, 
    StepDefinition, 
    StepType,
    InputDefinition,
    OutputDefinition,
    ChoiceDefinition,
    TableRollDefinition,
    DiceSequenceDefinition,
    LLMSettingsDefinition
)


@pytest.fixture
def test_system():
    """Load the flow test system."""
    loader = SystemLoader()
    system_path = Path(__file__).parent / "systems" / "flow_test"
    return loader.load_system(system_path)


class TestBasicFlowLoading:
    """Test basic flow loading and structure validation."""
    
    def test_system_loads_with_flows(self, test_system):
        """Test that the system loads and contains flows."""
        assert test_system is not None
        assert hasattr(test_system, 'flows')
        assert len(test_system.flows) > 0
    
    def test_basic_flow_structure(self, test_system):
        """Test basic flow structure is correctly loaded."""
        flow = test_system.flows.get("basic-flow")
        assert flow is not None
        assert isinstance(flow, FlowDefinition)
        assert flow.id == "basic-flow"
        assert flow.name == "Basic Flow"
        assert flow.description == "Simple flow for basic testing"
        assert flow.version == "1.0"
    
    def test_flow_inputs_and_outputs(self, test_system):
        """Test flow input and output definitions."""
        flow = test_system.flows["basic-flow"]
        
        # Test inputs
        assert len(flow.inputs) == 1
        input_def = flow.inputs[0]
        assert isinstance(input_def, InputDefinition)
        assert input_def.id == "player_name"
        assert input_def.type == "str"
        assert input_def.required is True
        assert input_def.description == "Name of the player"
        
        # Test outputs
        assert len(flow.outputs) == 1
        output_def = flow.outputs[0]
        assert isinstance(output_def, OutputDefinition)
        assert output_def.id == "character"
        assert output_def.type == "character"
        assert output_def.description == "Generated character"
    
    def test_flow_variables(self, test_system):
        """Test flow variable definitions."""
        flow = test_system.flows["basic-flow"]
        assert "temp_value" in flow.variables
        assert flow.variables["temp_value"] == "initial"


class TestStepDefinitions:
    """Test step definition parsing and validation."""
    
    def test_completion_step(self, test_system):
        """Test completion step definition."""
        flow = test_system.flows["basic-flow"]
        start_step = flow.get_step("start")
        
        assert start_step is not None
        assert isinstance(start_step, StepDefinition)
        assert start_step.id == "start"
        assert start_step.name == "Starting Step"
        assert start_step.type == StepType.COMPLETION
        assert start_step.prompt == "Welcome {{player_name}}!"
        assert start_step.next_step == "end"
    
    def test_dice_roll_step(self, test_system):
        """Test dice roll step definition."""
        flow = test_system.flows["dice-flow"]
        dice_step = flow.get_step("simple-roll")
        
        assert dice_step is not None
        assert dice_step.type == StepType.DICE_ROLL
        assert dice_step.roll == "1d6"
        assert dice_step.output == "dice_result"
        assert dice_step.next_step == "sequence-roll"
    
    def test_dice_sequence_step(self, test_system):
        """Test dice sequence step definition.""" 
        flow = test_system.flows["dice-flow"]
        sequence_step = flow.get_step("sequence-roll")
        
        assert sequence_step is not None
        assert sequence_step.type == StepType.DICE_SEQUENCE
        assert sequence_step.sequence is not None
        assert isinstance(sequence_step.sequence, DiceSequenceDefinition)
        assert sequence_step.sequence.items == ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        assert sequence_step.sequence.roll == "3d6"
        assert sequence_step.sequence.display_as == "{{ item }}: {{ result }}"
    
    def test_player_choice_step(self, test_system):
        """Test player choice step definition."""
        flow = test_system.flows["choice-flow"]
        choice_step = flow.get_step("character-class")
        
        assert choice_step is not None
        assert choice_step.type == StepType.PLAYER_CHOICE
        assert len(choice_step.choices) == 2
        
        # Test first choice
        warrior_choice = choice_step.choices[0]
        assert isinstance(warrior_choice, ChoiceDefinition)
        assert warrior_choice.id == "warrior"
        assert warrior_choice.label == "Warrior"
        assert warrior_choice.description == "Strong melee fighter"
        assert warrior_choice.next_step == "warrior-setup"
        assert len(warrior_choice.actions) == 1
    
    def test_table_roll_step(self, test_system):
        """Test table roll step definition."""
        flow = test_system.flows["table-flow"]
        table_step = flow.get_step("name-generation")
        
        assert table_step is not None
        assert table_step.type == StepType.TABLE_ROLL
        assert len(table_step.tables) == 1
        
        table_roll = table_step.tables[0]
        assert isinstance(table_roll, TableRollDefinition)
        assert table_roll.table == "simple-names"
        assert table_roll.count == 1
        assert len(table_roll.actions) == 1
    
    def test_llm_generation_step(self, test_system):
        """Test LLM generation step definition."""
        flow = test_system.flows["llm-flow"]
        llm_step = flow.get_step("generate-description")
        
        assert llm_step is not None
        assert llm_step.type == StepType.LLM_GENERATION
        assert llm_step.prompt == "Create a character description"
        assert "character_class" in llm_step.prompt_data
        assert llm_step.llm_settings is not None
        
        settings = llm_step.llm_settings
        assert isinstance(settings, LLMSettingsDefinition)
        assert settings.provider == "anthropic"
        assert settings.model == "claude-3-haiku"
        assert settings.max_tokens == 150
        assert settings.temperature == 0.8


class TestFlowValidation:
    """Test flow validation and error handling."""
    
    def test_all_step_types_supported(self, test_system):
        """Test that all step types are properly supported."""
        flows = test_system.flows
        
        # Collect all step types used in test flows
        found_types = set()
        for flow in flows.values():
            for step in flow.steps:
                found_types.add(step.type)
        
        # Verify we have coverage of main step types
        expected_types = {
            StepType.COMPLETION,
            StepType.DICE_ROLL,
            StepType.DICE_SEQUENCE,
            StepType.PLAYER_CHOICE,
            StepType.TABLE_ROLL,
            StepType.LLM_GENERATION,
            StepType.FLOW_CALL
        }
        
        # Check that we're testing the core step types
        assert StepType.COMPLETION in found_types
        assert StepType.DICE_ROLL in found_types
        assert StepType.PLAYER_CHOICE in found_types
        assert StepType.TABLE_ROLL in found_types
    
    def test_flow_step_references(self, test_system):
        """Test that flow step references are valid."""
        flow = test_system.flows["basic-flow"]
        
        # Test step lookup
        start_step = flow.get_step("start")
        assert start_step is not None
        
        end_step = flow.get_step("end")
        assert end_step is not None
        
        # Test step index lookup
        start_index = flow.get_step_index("start")
        assert start_index == 0
        
        end_index = flow.get_step_index("end")
        assert end_index == 1
        
        # Test invalid step
        invalid_step = flow.get_step("nonexistent")
        assert invalid_step is None
        
        invalid_index = flow.get_step_index("nonexistent")
        assert invalid_index is None
    
    def test_table_references_in_flows(self, test_system):
        """Test that table references in flows are valid."""
        flow = test_system.flows["table-flow"]
        table_step = flow.get_step("name-generation")
        
        # Verify table reference exists
        table_name = table_step.tables[0].table
        assert table_name in test_system.tables
        
        # Verify table is properly loaded
        table = test_system.tables[table_name]
        assert table.id == "simple-names"
        assert len(table.entries) == 4


class TestComplexFlowFeatures:
    """Test complex flow features like conditions and flow calls."""
    
    def test_complex_flow_structure(self, test_system):
        """Test complex flow with advanced features."""
        flow = test_system.flows["complex-flow"]
        
        assert flow is not None
        assert len(flow.inputs) == 2
        assert len(flow.outputs) == 2
        assert len(flow.variables) == 2
        assert len(flow.resume_points) == 2
        
        # Test resume points
        assert "character-creation" in flow.resume_points
        assert "final-review" in flow.resume_points
    
    def test_conditional_steps(self, test_system):
        """Test steps with conditions."""
        flow = test_system.flows["complex-flow"]
        
        setup_step = flow.get_step("setup")
        assert setup_step.condition == "inputs.difficulty != 'skip'"
        
        review_step = flow.get_step("final-review")
        assert review_step.condition == "variables.step_counter > 0"
    
    def test_step_actions(self, test_system):
        """Test step action definitions."""
        flow = test_system.flows["complex-flow"]
        setup_step = flow.get_step("setup")
        
        assert len(setup_step.actions) == 1
        action = setup_step.actions[0]
        assert action["type"] == "set_value"
        assert "data" in action
        assert action["data"]["path"] == "variables.step_counter"
        assert action["data"]["value"] == 1
    
    def test_flow_call_step(self, test_system):
        """Test flow call step functionality."""
        flow = test_system.flows["complex-flow"]
        flow_call_step = flow.get_step("character-creation")
        
        assert flow_call_step.type == StepType.FLOW_CALL
        assert len(flow_call_step.actions) == 1
        
        action = flow_call_step.actions[0]
        assert action["type"] == "call_flow"
        assert action["data"]["flow_id"] == "basic-flow"
        assert "inputs" in action["data"]


class TestFlowEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_optional_flow_fields(self, test_system):
        """Test flows with optional fields."""
        # Test flow without description
        flow = test_system.flows["dice-flow"]
        assert flow.description == "Flow demonstrating dice step types"
        assert flow.version is None  # Not specified
        assert len(flow.inputs) == 0  # No inputs specified
        assert len(flow.outputs) == 0  # No outputs specified
    
    def test_optional_step_fields(self, test_system):
        """Test steps with optional fields."""
        flow = test_system.flows["dice-flow"]
        sequence_step = flow.get_step("sequence-roll")
        
        # Should have defaults for optional fields
        assert sequence_step.condition is None
        assert sequence_step.parallel is False
        assert sequence_step.next_step is None
        assert len(sequence_step.actions) == 0
    
    def test_step_type_enum_validation(self, test_system):
        """Test that step types are properly validated as enums."""
        flows = test_system.flows
        
        for flow in flows.values():
            for step in flow.steps:
                assert isinstance(step.type, StepType)
                # Verify it's one of the valid enum values
                assert step.type in [
                    StepType.DICE_ROLL,
                    StepType.DICE_SEQUENCE,
                    StepType.PLAYER_CHOICE,
                    StepType.TABLE_ROLL,
                    StepType.LLM_GENERATION,
                    StepType.COMPLETION,
                    StepType.FLOW_CALL
                ]


class TestFlowIntegration:
    """Test flow integration with other system components."""
    
    def test_system_loads_completely_with_flows(self, test_system):
        """Test that the complete system loads successfully."""
        # Verify all components are loaded
        assert len(test_system.models) == 1  # character model
        assert len(test_system.tables) == 1  # simple-names table
        assert len(test_system.flows) == 6   # all test flows
        
        # Verify flows reference valid system components
        assert "character" in test_system.models
        assert "simple-names" in test_system.tables
    
    def test_flow_model_references(self, test_system):
        """Test that flows properly reference system models."""
        flow = test_system.flows["basic-flow"]
        
        # Check output type references
        character_output = flow.outputs[0]
        assert character_output.type == "character"
        assert character_output.type in test_system.models
    
    def test_flow_cross_references(self, test_system):
        """Test cross-references between flows."""
        complex_flow = test_system.flows["complex-flow"]
        flow_call_step = complex_flow.get_step("character-creation")
        
        # Verify referenced flow exists
        action = flow_call_step.actions[0]
        referenced_flow_id = action["data"]["flow_id"]
        assert referenced_flow_id in test_system.flows
        
        # Verify referenced flow structure
        referenced_flow = test_system.flows[referenced_flow_id]
        assert referenced_flow.id == "basic-flow"
    
    def test_existing_validation_still_works(self, test_system):
        """Test that existing system validation still works with flows."""
        # This ensures flow loading doesn't break other functionality
        assert test_system.id == "flow_test"
        assert test_system.name == "Flow Definition Test System"
        
        # Verify other components still work
        character_model = test_system.models["character"]
        assert character_model.id == "character"
        
        names_table = test_system.tables["simple-names"]
        assert names_table.id == "simple-names"
        assert len(names_table.entries) == 4


# Utility for creating test flows programmatically
class TestFlowBuilder:
    """Test utility for building flows programmatically."""
    
    def test_flow_creation_utility(self):
        """Test programmatic flow creation for testing purposes."""
        flow = FlowDefinition(
            id="test-flow",
            name="Test Flow",
            inputs=[
                InputDefinition(
                    id="test_input",
                    type="str",
                    required=True
                )
            ],
            outputs=[
                OutputDefinition(
                    id="test_output", 
                    type="str"
                )
            ],
            steps=[
                StepDefinition(
                    id="test_step",
                    name="Test Step",
                    type=StepType.COMPLETION,
                    prompt="Test prompt"
                )
            ]
        )
        
        assert flow.id == "test-flow"
        assert len(flow.inputs) == 1
        assert len(flow.outputs) == 1
        assert len(flow.steps) == 1
        
        # Test step lookup
        step = flow.get_step("test_step")
        assert step is not None
        assert step.type == StepType.COMPLETION
    
    def test_step_creation_utility(self):
        """Test programmatic step creation for testing purposes."""
        step = StepDefinition(
            id="utility_step",
            name="Utility Step",
            type=StepType.DICE_ROLL,
            roll="2d6",
            output="roll_result"
        )
        
        assert step.id == "utility_step"
        assert step.type == StepType.DICE_ROLL
        assert step.roll == "2d6"
        assert step.output == "roll_result"
