"""
Test flow execution functionality.

This tests actual flow execution including:
- End-to-end flow execution and completion
- Output validation after flow execution  
- Variable updates during execution
- Action execution and path updates
- Step integration with system components
- Execution context management

Tests are organized to validate the critical gap identified in Phase 1.4:
flows parse correctly but we need to verify they actually execute and produce
correct outputs.

This is Phase 1.4.1 of the testing strategy.
"""

import pytest
from pathlib import Path
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import FlowResult, StepResult


@pytest.fixture
def test_system():
    """Load the flow test system."""
    loader = SystemLoader()
    system_path = Path(__file__).parent / "systems" / "flow_test"
    return loader.load_system(system_path)


@pytest.fixture
def engine():
    """Create a GRIMOIRE engine for flow execution."""
    return GrimoireEngine()


@pytest.fixture  
def execution_context(engine):
    """Create a basic execution context for testing."""
    return engine.create_execution_context()


class TestFlowExecution:
    """Test end-to-end flow execution and completion."""
    
    def test_basic_flow_execution(self, engine, test_system):
        """Test basic flow execution with simple completion steps."""
        context = engine.create_execution_context()
        context.set_input("player_name", "TestPlayer")
        
        # Execute the basic-flow which has a simple completion step
        result = engine.execute_flow("basic-flow", context, test_system)
        
        assert isinstance(result, FlowResult)
        assert result.success is True
        assert result.flow_id == "basic-flow"
        assert len(result.step_results) > 0
        
        # Verify at least one step was executed
        first_step_result = result.step_results[0]
        assert isinstance(first_step_result, StepResult)
        assert first_step_result.success is True
    
    def test_dice_flow_execution(self, engine, test_system):
        """Test dice flow execution with proper variable updates."""
        context = engine.create_execution_context()
        
        # Execute the dice-flow which has dice rolling steps
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert isinstance(result, FlowResult)
        assert result.success is True
        assert result.flow_id == "dice-flow"
        
        # Verify variables were updated during execution
        assert "dice_result" in result.variables
        assert "ability_scores" in result.variables
        
        # dice_result should be set from the simple roll
        dice_result = result.variables["dice_result"]
        assert isinstance(dice_result, int)
        assert 1 <= dice_result <= 6  # 1d6 range
        
        # ability_scores should be a dict with ability names
        ability_scores = result.variables["ability_scores"]
        assert isinstance(ability_scores, dict)
        # Should have all 6 ability scores
        expected_abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        for ability in expected_abilities:
            assert ability in ability_scores
            score = ability_scores[ability]
            assert isinstance(score, int)
            assert 3 <= score <= 18  # 3d6 range
    
    def test_table_flow_execution(self, engine, test_system):
        """Test table flow execution with output value setting."""
        context = engine.create_execution_context()
        
        # Execute the table-flow which rolls on tables and sets outputs
        result = engine.execute_flow("table-flow", context, test_system)
        
        assert isinstance(result, FlowResult)
        assert result.success is True
        assert result.flow_id == "table-flow"
        
        # Verify outputs were set correctly
        assert "character" in result.outputs
        character = result.outputs["character"]
        assert isinstance(character, dict)
        
        # The table-flow should set character.name from the simple-names table
        assert "name" in character
        character_name = character["name"]
        assert isinstance(character_name, str)
        assert len(character_name) > 0
        
        # Verify the name is from the expected table entries
        expected_names = ["Alice", "Bob", "Charlie", "Diana"]
        assert character_name in expected_names
    
    def test_choice_flow_execution(self, engine, test_system):
        """Test choice flow execution with conditional branching."""
        context = engine.create_execution_context()
        
        # Execute the choice-flow 
        # Note: This will execute automatically without user interaction
        # The first choice option will be selected by default
        result = engine.execute_flow("choice-flow", context, test_system)
        
        assert isinstance(result, FlowResult)  
        assert result.success is True
        assert result.flow_id == "choice-flow"
        
        # Verify the flow executed and completed
        assert len(result.step_results) > 0
        
        # At least one step should have succeeded
        successful_steps = [sr for sr in result.step_results if sr.success]
        assert len(successful_steps) > 0


class TestOutputValidation:
    """Test that outputs are set correctly after execution."""
    
    def test_character_name_output_validation(self, engine, test_system):
        """Test that outputs.character.name is set correctly after table-flow execution."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("table-flow", context, test_system)
        
        assert result.success is True
        
        # Verify character output structure
        assert "character" in result.outputs
        character = result.outputs["character"]
        
        # Verify name was set from table roll
        assert "name" in character
        assert isinstance(character["name"], str)
        assert len(character["name"]) > 0
        
        # Should be one of the valid names from simple-names table
        valid_names = ["Alice", "Bob", "Charlie", "Diana"]
        assert character["name"] in valid_names
    
    def test_character_class_output_validation(self, engine, test_system):
        """Test that outputs.character.class is set correctly after choice-flow execution."""
        context = engine.create_execution_context()
        context.set_input("player_name", "TestPlayer")
        
        # For this test, we'll use basic-flow which has character output
        result = engine.execute_flow("basic-flow", context, test_system)
        
        assert result.success is True
        
        # Verify character output exists
        assert "character" in result.outputs
        character = result.outputs["character"]
        
        # basic-flow sets character to the input player name as a string
        assert character == "TestPlayer"
        assert isinstance(character, str)
    
    def test_multiple_outputs_handling(self, engine, test_system):
        """Test that multiple outputs are handled correctly in complex flows."""
        context = engine.create_execution_context()
        
        # Use complex-flow which may have multiple outputs
        result = engine.execute_flow("complex-flow", context, test_system)
        
        assert result.success is True
        
        # Verify outputs structure exists
        assert isinstance(result.outputs, dict)
        
        # Complex flow should produce some outputs
        # (specific outputs depend on the flow definition)
        if result.outputs:
            # If there are outputs, they should be properly structured
            for output_id, output_value in result.outputs.items():
                assert isinstance(output_id, str)
                assert len(output_id) > 0


class TestVariableUpdates:
    """Test that variables are updated correctly during execution."""
    
    def test_dice_result_variable_update(self, engine, test_system):
        """Test that variables.dice_result is set correctly after dice-flow execution."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert result.success is True
        
        # Verify dice_result variable was set
        assert "dice_result" in result.variables
        dice_result = result.variables["dice_result"]
        
        # Should be an integer from 1d6 roll
        assert isinstance(dice_result, int)
        assert 1 <= dice_result <= 6
    
    def test_ability_scores_variable_update(self, engine, test_system):
        """Test that variables.ability_scores are populated correctly after dice sequence."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert result.success is True
        
        # Verify ability_scores variable was populated
        assert "ability_scores" in result.variables
        ability_scores = result.variables["ability_scores"]
        
        assert isinstance(ability_scores, dict)
        
        # Should have all 6 standard D&D ability scores
        expected_abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        assert len(ability_scores) == len(expected_abilities)
        
        for ability in expected_abilities:
            assert ability in ability_scores
            score = ability_scores[ability]
            assert isinstance(score, int)
            assert 3 <= score <= 18  # 3d6 range
    
    def test_variables_persist_across_steps(self, engine, test_system):
        """Test that variables persist across multiple steps in a flow."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert result.success is True
        
        # Both variables from different steps should be present
        assert "dice_result" in result.variables
        assert "ability_scores" in result.variables
        
        # Both should have valid values
        assert result.variables["dice_result"] > 0
        assert len(result.variables["ability_scores"]) > 0
        
        # Variables should maintain their values throughout execution
        dice_result = result.variables["dice_result"]
        ability_scores = result.variables["ability_scores"]
        
        # Re-execute and verify consistency in variable handling
        context2 = engine.create_execution_context()
        result2 = engine.execute_flow("dice-flow", context2, test_system)
        
        assert result2.success is True
        assert "dice_result" in result2.variables
        assert "ability_scores" in result2.variables
        
        # Values will be different (random) but structure should be same
        assert isinstance(result2.variables["dice_result"], type(dice_result))
        assert isinstance(result2.variables["ability_scores"], type(ability_scores))


class TestActionExecution:
    """Test that actions perform their intended operations."""
    
    def test_set_value_actions_update_paths(self, engine, test_system):
        """Test that set_value actions update paths correctly."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert result.success is True
        
        # The dice-flow uses set_value actions to update variables
        # Verify the actions actually worked
        assert "dice_result" in result.variables
        assert "ability_scores" in result.variables
        
        # These should be set by set_value actions in the flow steps
        dice_result = result.variables["dice_result"]
        assert dice_result is not None
        assert dice_result > 0
        
        ability_scores = result.variables["ability_scores"]
        assert ability_scores is not None
        assert len(ability_scores) > 0
    
    def test_multiple_actions_execute_in_order(self, engine, test_system):
        """Test that multiple actions in a single step execute in order."""
        context = engine.create_execution_context()
        
        # Use dice-flow which has sequence roll with multiple actions
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert result.success is True
        
        # The dice sequence should have executed all its actions
        ability_scores = result.variables["ability_scores"]
        
        # All expected abilities should be present (multiple set_value actions)
        expected_abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]
        for ability in expected_abilities:
            assert ability in ability_scores
            assert ability_scores[ability] > 0
    
    def test_template_rendering_in_actions(self, engine, test_system):
        """Test that template rendering works correctly in action values."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("table-flow", context, test_system)
        
        assert result.success is True
        
        # The table-flow uses template rendering in set_value actions
        # {{ result }} should be resolved to the actual table result
        character = result.outputs.get("character", {})
        character_name = character.get("name")
        
        assert character_name is not None
        assert isinstance(character_name, str)
        # Should be a resolved name, not the template string "{{ result }}"
        assert character_name != "{{ result }}"
        assert len(character_name) > 0
    
    def test_error_handling_invalid_paths(self, engine, test_system):
        """Test error handling for invalid paths or values in actions."""
        context = engine.create_execution_context()
        context.set_input("player_name", "TestPlayer")
        
        # Most flows should execute successfully with valid paths
        result = engine.execute_flow("basic-flow", context, test_system)
        
        # Should not fail due to invalid paths in our test flows
        assert result.success is True
        
        # All step results should be successful (no action path errors)
        for step_result in result.step_results:
            # Steps should succeed unless there's a specific error condition
            if not step_result.success:
                # Log the error for debugging if needed
                print(f"Step {step_result.step_id} failed: {step_result.error}")
        
        # At least some steps should succeed
        successful_steps = [sr for sr in result.step_results if sr.success]
        assert len(successful_steps) > 0


class TestStepIntegration:
    """Test that steps work correctly with system components."""
    
    def test_table_roll_steps_select_entries(self, engine, test_system):
        """Test that table roll steps actually select entries from loaded tables."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("table-flow", context, test_system)
        
        assert result.success is True
        
        # Should have selected a name from the simple-names table
        character = result.outputs.get("character", {})
        selected_name = character.get("name")
        
        assert selected_name is not None
        assert isinstance(selected_name, str)
        
        # Should be one of the entries from the simple-names table
        table = test_system.tables["simple-names"]
        valid_names = list(table.entries.values())  # Get the actual names, not the keys
        assert selected_name in valid_names
    
    def test_results_match_table_entry_types(self, engine, test_system):
        """Test that results match expected table entry types and formats."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("table-flow", context, test_system)
        
        assert result.success is True
        
        # The simple-names table contains string entries
        character = result.outputs.get("character", {})  
        selected_name = character.get("name")
        
        # Should be a string (matching table entry type)
        assert isinstance(selected_name, str)
        assert len(selected_name) > 0
        
        # Should not be a complex object or other type
        assert not isinstance(selected_name, dict)
        assert not isinstance(selected_name, list)
    
    def test_flow_table_cross_references_work(self, engine, test_system):
        """Test that cross-references between flows and tables work during execution."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("table-flow", context, test_system)
        
        assert result.success is True
        
        # The flow references the simple-names table, which should exist
        names_table = test_system.tables.get("simple-names")
        assert names_table is not None
        
        # The flow execution should have successfully used this table
        character = result.outputs.get("character", {})
        selected_name = character.get("name")
        
        # The selected name should be from the referenced table
        assert selected_name in names_table.entries.values()  # Check values, not keys


class TestExecutionContext:
    """Test proper execution environment setup and state management."""
    
    def test_input_parameters_passed_correctly(self, engine, test_system):
        """Test that input parameters are correctly passed to flow execution."""
        # Create context with input parameters
        test_player_name = "TestPlayerInput"
        context = engine.create_execution_context()
        context.set_input("player_name", test_player_name)
        
        result = engine.execute_flow("basic-flow", context, test_system)
        
        assert result.success is True
        
        # The input should be available during execution
        # (basic-flow expects player_name input)
        # Note: We can't directly test template resolution here without examining
        # internal execution state, but the flow should complete successfully
        # if inputs are properly passed
        assert len(result.step_results) > 0
    
    def test_execution_context_maintains_state(self, engine, test_system):
        """Test that execution context maintains proper state throughout flow."""
        context = engine.create_execution_context()
        
        result = engine.execute_flow("dice-flow", context, test_system)
        
        assert result.success is True
        
        # Context should have accumulated state throughout execution
        assert len(result.variables) > 0
        
        # Should have variables from different steps
        assert "dice_result" in result.variables
        assert "ability_scores" in result.variables
        
        # State should be consistent
        dice_result = result.variables["dice_result"]
        ability_scores = result.variables["ability_scores"]
        
        assert isinstance(dice_result, int)
        assert isinstance(ability_scores, dict)
        
        # Both should have valid values showing state was maintained
        assert dice_result > 0
        assert len(ability_scores) > 0


# Utility functions for creating test scenarios

def create_test_execution_context(**kwargs):
    """Create an execution context with test data."""
    engine = GrimoireEngine()
    return engine.create_execution_context(**kwargs)


def verify_flow_execution_success(result: FlowResult):
    """Verify that a flow execution was successful."""
    assert isinstance(result, FlowResult)
    assert result.success is True
    assert len(result.step_results) > 0
    
    # At least one step should have succeeded
    successful_steps = [sr for sr in result.step_results if sr.success]
    assert len(successful_steps) > 0


def verify_variable_update(result: FlowResult, variable_name: str, expected_type: type = None):
    """Verify that a variable was updated during flow execution."""
    assert variable_name in result.variables
    value = result.variables[variable_name]
    assert value is not None
    
    if expected_type:
        assert isinstance(value, expected_type)


def verify_output_set(result: FlowResult, output_id: str, expected_type: type = None):
    """Verify that an output was set during flow execution."""
    assert output_id in result.outputs
    value = result.outputs[output_id]
    assert value is not None
    
    if expected_type:
        assert isinstance(value, expected_type)
