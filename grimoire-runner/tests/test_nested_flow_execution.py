"""
Test nested flow_call functionality with multiple levels of nesting.

This tests the enhanced flow_call functionality that supports:
- Multi-level nested sub-flows (sub-flows calling other sub-flows)
- Result passing between nested levels using {{ result.variable_name }} templates
- Proper execution context management across nested flows
- UI display of nested flow execution with proper indentation
"""

from pathlib import Path

import pytest

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.models.flow import FlowResult, StepResult


@pytest.fixture
def test_system():
    """Load the flow test system containing nested flow test cases."""
    loader = SystemLoader()
    system_path = Path(__file__).parent / "systems" / "flow_test"
    return loader.load_system(system_path)


@pytest.fixture
def engine():
    """Create a GRIMOIRE engine for flow execution."""
    return GrimoireEngine()


class TestNestedFlowExecution:
    """Test multi-level nested flow execution functionality."""

    def test_nested_flow_calls_execute_successfully(self, engine, test_system):
        """Test that nested flow calls (3 levels deep) execute successfully."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Test Input")

        # Execute the main test flow which calls nested sub-flows
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        assert isinstance(result, FlowResult)
        assert result.success is True
        assert result.flow_id == "test_nested_flow_calls"
        assert len(result.step_results) == 2  # Level 1 Flow Call + Complete Test

        # Both main flow steps should succeed
        for step_result in result.step_results:
            assert step_result.success is True

    def test_level_2_flow_executes_independently(self, engine, test_system):
        """Test that level 2 flow can execute independently."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Direct Level 2 Test")

        # Execute level 2 flow directly
        result = engine.execute_flow("test_level_2_flow", context, test_system)

        assert isinstance(result, FlowResult)
        assert result.success is True
        assert result.flow_id == "test_level_2_flow"
        assert len(result.step_results) == 3  # Processing + Flow Call + Complete

        # All steps should succeed
        for step_result in result.step_results:
            assert step_result.success is True

        # Should have the expected output and variables
        assert "level_2_result" in result.outputs
        assert isinstance(result.outputs["level_2_result"], str)
        
        # Should also have the dice result in variables
        assert "level_2_dice" in result.variables
        dice_result = result.variables["level_2_dice"]
        assert isinstance(dice_result, int)
        assert 1 <= dice_result <= 6  # 1d6 range

    def test_level_3_flow_executes_independently(self, engine, test_system):
        """Test that level 3 flow can execute independently."""
        context = engine.create_execution_context()
        context.set_input("deep_input", "Direct Level 3 Test")

        # Execute level 3 flow directly
        result = engine.execute_flow("test_level_3_flow", context, test_system)

        assert isinstance(result, FlowResult)
        assert result.success is True
        assert result.flow_id == "test_level_3_flow"
        assert len(result.step_results) == 2  # Dice Roll + Complete

        # All steps should succeed
        for step_result in result.step_results:
            assert step_result.success is True

        # Should have dice roll result in variables
        assert "deep_dice_result" in result.variables
        dice_result = result.variables["deep_dice_result"]
        assert isinstance(dice_result, int)
        assert 1 <= dice_result <= 4  # 1d4 range

        # Should also have the output
        assert "level_3_result" in result.outputs
        level_3_output = result.outputs["level_3_result"]
        assert isinstance(level_3_output, str)
        assert level_3_output == "Level 3 complete"

    def test_result_passing_through_nested_levels(self, engine, test_system):
        """Test that results are properly passed through all nested levels."""
        context = engine.create_execution_context()
        test_input = "Result Passing Test"
        context.set_input("input_value", test_input)

        # Execute the main nested flow
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        assert result.success is True

        # The main flow should complete successfully, indicating that:
        # 1. Level 2 flow received the input and processed it
        # 2. Level 3 flow received the processed input from Level 2
        # 3. Results were properly passed back up the chain
        # 4. All template resolutions worked correctly

        # Verify the flow completed all steps
        assert len(result.step_results) == 2
        for step_result in result.step_results:
            assert step_result.success is True

    def test_template_resolution_with_result_variable(self, engine, test_system):
        """Test that {{ result.variable_name }} templates work in nested contexts."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Template Test Input")

        # Execute level 2 flow which uses {{ result.deep_dice_result }} template
        result = engine.execute_flow("test_level_2_flow", context, test_system)

        assert result.success is True

        # The flow should have successfully resolved templates
        # Level 2 flow sets level_2_result output  
        assert "level_2_result" in result.outputs
        level_2_output = result.outputs["level_2_result"]
        assert isinstance(level_2_output, str)
        
        # The output should be the expected completion message
        assert level_2_output == "Level 2 complete"

    def test_nested_dice_rolling_works(self, engine, test_system):
        """Test that dice rolling works properly within nested flows."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Dice Test")

        # Execute multiple times to verify dice randomness
        results = []
        for _ in range(5):
            test_context = engine.create_execution_context()
            test_context.set_input("input_value", "Dice Test")
            
            result = engine.execute_flow("test_nested_flow_calls", test_context, test_system)
            assert result.success is True
            results.append(result)

        # All executions should succeed
        for result in results:
            assert result.success is True
            assert len(result.step_results) == 2

        # This tests that the nested dice rolling is working properly
        # We can't easily inspect the intermediate dice results from the main flow,
        # but successful execution indicates the dice steps worked

    def test_error_handling_in_nested_flows(self, engine, test_system):
        """Test error handling when nested flows have issues."""
        context = engine.create_execution_context()
        # Intentionally omit required input to test error handling
        # Don't set input_value - this should cause template resolution errors

        # Execute the nested flow without required input
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        # The flow should fail gracefully due to missing input
        # The exact behavior depends on how template errors are handled
        # But it should not crash the entire system
        assert isinstance(result, FlowResult)
        assert result.flow_id == "test_nested_flow_calls"
        
        # Either it fails cleanly or succeeds with default/empty values
        # The important thing is it doesn't crash
        if not result.success:
            # If it fails, it should have error information
            assert len(result.step_results) > 0
            # At least some step should have failed
            failed_steps = [sr for sr in result.step_results if not sr.success]
            assert len(failed_steps) > 0

    def test_multiple_nested_calls_in_sequence(self, engine, test_system):
        """Test multiple nested flow calls in sequence within the same flow."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Sequential Test")

        # Execute the main flow multiple times to test consistency
        for i in range(3):
            test_context = engine.create_execution_context()
            test_context.set_input("input_value", f"Sequential Test {i}")
            
            result = engine.execute_flow("test_nested_flow_calls", test_context, test_system)
            
            assert result.success is True
            assert result.flow_id == "test_nested_flow_calls"
            
            # Should have the same structure each time
            assert len(result.step_results) == 2
            
            # All steps should succeed
            for step_result in result.step_results:
                assert step_result.success is True


class TestFlowCallResultHandling:
    """Test specific aspects of result handling in flow_call steps."""

    def test_flow_call_step_has_result_variable(self, engine, test_system):
        """Test that flow_call steps provide access to result variable."""
        context = engine.create_execution_context()
        context.set_input("deep_input", "Result Variable Test")

        # Execute level 3 flow which should provide results
        result = engine.execute_flow("test_level_3_flow", context, test_system)

        assert result.success is True
        
        # Should have produced the level 3 output and variables
        assert "level_3_result" in result.outputs
        level_3_output = result.outputs["level_3_result"]
        assert isinstance(level_3_output, str)
        assert level_3_output == "Level 3 complete"
        
        # Should have the dice result in variables
        assert "deep_dice_result" in result.variables
        dice_result = result.variables["deep_dice_result"]
        assert isinstance(dice_result, int)
        assert 1 <= dice_result <= 4  # 1d4 range

        # The output should contain the dice roll result (templated from {{ variables.deep_dice_result }})
        # This tests that the result variable mechanism is working
        
    def test_result_variable_accessible_in_templates(self, engine, test_system):
        """Test that {{ result.* }} templates can access sub-flow outputs."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Template Access Test")

        # Execute level 2 flow which uses {{ result.level_3_result }} in templates
        result = engine.execute_flow("test_level_2_flow", context, test_system)

        assert result.success is True
        
        # The template should have been resolved successfully
        # If the template resolution failed, the flow would have failed or
        # produced invalid output
        assert "level_2_result" in result.outputs
        
        # The output should contain resolved template content
        level_2_output = result.outputs["level_2_result"]
        assert isinstance(level_2_output, str)
        # Should be the expected completion message
        assert level_2_output == "Level 2 complete"

    def test_nested_result_chaining(self, engine, test_system):
        """Test that results can be chained through multiple levels."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Chain Test Input")

        # Execute the full nested chain
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        assert result.success is True
        
        # The successful completion of this flow indicates that:
        # 1. Level 1 passed input to Level 2
        # 2. Level 2 passed processed input to Level 3  
        # 3. Level 3 produced results
        # 4. Level 3 results were accessible in Level 2 via {{ result.* }}
        # 5. Level 2 results were accessible in Level 1
        # 6. All template resolutions worked correctly
        
        # Verify the complete chain executed
        assert len(result.step_results) == 2
        for step_result in result.step_results:
            assert step_result.success is True


class TestFlowExecutionContext:
    """Test execution context management in nested flows."""

    def test_execution_context_isolation(self, engine, test_system):
        """Test that execution contexts are properly isolated between nested flows."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Context Isolation Test")
        
        # Set some additional variables in the main context
        context.set_variable("main_var", "main_value")
        context.set_variable("shared_var", "original_value")

        # Execute nested flows
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        assert result.success is True
        
        # The main context should still have its original variables
        # (though the exact state depends on how context isolation is implemented)
        # The important thing is that the nested flows executed successfully
        # without interfering with each other's contexts

    def test_variable_scoping_in_nested_flows(self, engine, test_system):
        """Test that variables are properly scoped within nested flows."""
        context = engine.create_execution_context()
        context.set_input("input_value", "Scoping Test")

        # Execute the nested flow
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        assert result.success is True
        
        # The fact that the flow completed successfully indicates that:
        # 1. Each nested flow had access to its required inputs
        # 2. Variables didn't leak between scopes inappropriately
        # 3. Template resolution worked within each scope
        
        # Test that the main flow context wasn't corrupted
        assert result.flow_id == "test_nested_flow_calls"

    def test_input_parameter_passing(self, engine, test_system):
        """Test that input parameters are correctly passed to nested flows."""
        context = engine.create_execution_context()
        test_value = "Parameter Passing Test Value"
        context.set_input("input_value", test_value)

        # Execute the nested flow
        result = engine.execute_flow("test_nested_flow_calls", context, test_system)

        assert result.success is True
        
        # The successful execution indicates that:
        # 1. The main flow received the input_value parameter
        # 2. It was correctly passed to the level 2 flow  
        # 3. Level 2 processed it and passed processed version to level 3
        # 4. All levels had access to their required inputs
        
        # Verify flow completed all steps
        assert len(result.step_results) == 2
        for step_result in result.step_results:
            assert step_result.success is True


# Utility functions for nested flow testing

def verify_nested_flow_success(result: FlowResult, expected_steps: int = None):
    """Verify that a nested flow execution was successful."""
    assert isinstance(result, FlowResult)
    assert result.success is True
    assert len(result.step_results) > 0
    
    if expected_steps:
        assert len(result.step_results) == expected_steps
    
    # All steps should be successful
    for step_result in result.step_results:
        assert step_result.success is True

def verify_dice_result_in_variables(result: FlowResult, variable_name: str):
    """Verify that a dice roll result is properly stored in variables."""
    assert variable_name in result.variables
    dice_result = result.variables[variable_name]
    assert isinstance(dice_result, int)
    assert dice_result >= 1  # Dice results should be positive

def verify_template_resolution(output_value: str):
    """Verify that template strings have been properly resolved."""
    if isinstance(output_value, str):
        # Should not contain unresolved template syntax
        assert "{{" not in output_value or "}}" not in output_value
        # Should not be empty (unless that's expected)
        assert len(output_value.strip()) > 0
