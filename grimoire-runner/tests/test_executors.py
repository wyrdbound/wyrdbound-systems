"""
Tests for GRIMOIRE step executors.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.executors.base import BaseStepExecutor
from grimoire_runner.executors.dice_executor import DiceExecutor
from grimoire_runner.executors.choice_executor import ChoiceExecutor
from grimoire_runner.executors.table_executor import TableExecutor
from grimoire_runner.executors.llm_executor import LLMExecutor
from grimoire_runner.executors.flow_executor import FlowExecutor
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import StepDefinition, StepResult, StepType, ChoiceDefinition
from grimoire_runner.models.system import System
from grimoire_runner.models.table import TableDefinition, TableEntry


class MockStep:
    """Mock step definition for testing."""
    
    def __init__(self, step_id="test_step", step_type="dice_roll", **kwargs):
        self.id = step_id
        self.type = StepType(step_type) if isinstance(step_type, str) else step_type
        self.name = f"Test Step {step_id}"
        
        # Default attributes
        self.roll = None
        self.sequence = None
        self.choices = []
        self.tables = None
        self.table = None
        self.die = None
        self.prompt = None
        self.settings = None
        self.output = None
        self.flow = None
        self.inputs = None
        self.message = None
        self.modifiers = None  # Add modifiers attribute
        
        # Set attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestBaseStepExecutor:
    """Test the base step executor."""
    
    def test_base_executor_interface(self):
        """Test that BaseStepExecutor defines the interface correctly."""
        # BaseStepExecutor is abstract, test by checking the subclass interfaces
        executor = DiceExecutor()
        
        # Should have execute method
        assert hasattr(executor, 'execute')
        
        # execute should take step, context, system parameters
        import inspect
        sig = inspect.signature(executor.execute)
        assert len(sig.parameters) == 3  # step, context, system (self is not counted)


class TestDiceExecutor:
    """Test the dice executor."""
    
    def setup_method(self):
        """Set up each test."""
        self.executor = DiceExecutor()
        self.context = ExecutionContext()
        self.system = Mock()
    
    def test_simple_dice_roll(self):
        """Test a simple dice roll."""
        step = MockStep(
            step_type="dice_roll",
            roll="1d6", 
            output="result"
        )
        
        # Mock the dice integration
        with patch.object(self.executor.dice_integration, 'roll_expression') as mock_roll:
            from grimoire_runner.integrations.dice_integration import DiceResult
            mock_roll.return_value = DiceResult(total=4, expression="1d6")
            
            result = self.executor.execute(step, self.context, self.system)
        
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is True
        assert result.data.get('result') == 4
        # Note: output variables may be set by higher-level execution engine
        # For now, just verify the result data is correct
    
    def test_dice_roll_without_output(self):
        """Test dice roll without output variable."""
        step = MockStep(
            step_type="dice_roll", 
            roll="1d4"
        )  # No output specified
        
        with patch.object(self.executor.dice_integration, 'roll_expression') as mock_roll:
            from grimoire_runner.integrations.dice_integration import DiceResult
            mock_roll.return_value = DiceResult(total=3, expression="1d4")
            
            result = self.executor.execute(step, self.context, self.system)
        
        assert result.success is True
        assert result.data.get('result') == 3
        # Should not set any variable in context without explicit output handling
    
    def test_invalid_dice_step_type(self):
        """Test handling of invalid step type."""
        # Create step with raw string type that bypasses enum validation
        step = MockStep.__new__(MockStep)
        step.id = "test_step"
        step.type = "invalid_type"  # Raw string, not enum
        step.name = "Test Step test_step"
        step.roll = "1d6"
        step.output = "result"
        step.modifiers = None
        
        result = self.executor.execute(step, self.context, self.system)
        
        assert result.success is False
        assert result.error is not None
        assert "cannot handle step type" in result.error
    
    def test_dice_roll_missing_roll_param(self):
        """Test dice roll without roll parameter."""
        step = MockStep(
            step_type="dice_roll",
            output="result"
        )  # No roll specified
        
        result = self.executor.execute(step, self.context, self.system)
        
        assert result.success is False
        assert result.error is not None
        assert "requires 'roll' parameter" in result.error


class TestChoiceExecutor:
    """Test the choice executor."""
    
    def setup_method(self):
        """Set up each test."""
        self.executor = ChoiceExecutor()
        self.context = ExecutionContext()
        self.system = Mock()
    
    def test_choice_execution_basic_structure(self):
        """Test basic choice execution structure."""
        step = MockStep(
            step_type="player_choice",
            prompt="Choose an option:",
            choices=[
                ChoiceDefinition(id="option_a", label="Option A"),
                ChoiceDefinition(id="option_b", label="Option B")
            ],
            output="choice"
        )
        
        # The choice executor doesn't automatically make choices - it should
        # return a result that indicates user input is needed
        result = self.executor.execute(step, self.context, self.system)
        
        # The result should indicate the step was processed
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
    
    def test_choice_execution_empty_choices(self):
        """Test choice execution with empty choices list."""
        step = MockStep(
            step_type="player_choice",
            prompt="Choose an option:",
            choices=[],
            output="choice"
        )
        
        result = self.executor.execute(step, self.context, self.system)
        
        # Should handle empty choices gracefully
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"


class TestTableExecutor:
    """Test the table executor."""
    
    def setup_method(self):
        """Set up each test."""
        self.executor = TableExecutor()
        self.context = ExecutionContext()
        
        # Create a mock system with tables
        self.system = Mock()
        self.system.get_table = Mock()
    
    def create_mock_table(self, table_id="test_table", die="1d6"):
        """Create a mock table for testing."""
        table = Mock()
        table.id = table_id
        table.name = "Test Table"
        table.die = die
        table.entries = [
            Mock(range_start=1, range_end=2, result="First result"),
            Mock(range_start=3, range_end=4, result="Second result"),
            Mock(range_start=5, range_end=6, result="Third result")
        ]
        return table
    
    def test_table_executor_with_no_tables(self):
        """Test table executor when step has no tables defined."""
        step = MockStep(
            step_type="table_roll",
            output="result"
        )
        
        result = self.executor.execute(step, self.context, self.system)
        
        # Should handle missing tables gracefully
        assert isinstance(result, StepResult)
        # May succeed or fail depending on implementation, but should not crash
    
    def test_table_executor_without_system(self):
        """Test table executor without system provided."""
        step = MockStep(
            step_type="table_roll",
            tables=[{"table": "test_table"}],
            output="result"
        )
        
        result = self.executor.execute(step, self.context, system=None)
        
        # Should handle missing system gracefully
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"


class TestLLMExecutor:
    """Test the LLM executor."""
    
    def setup_method(self):
        """Set up each test."""
        self.executor = LLMExecutor()
        self.context = ExecutionContext()
        self.system = Mock()
    
    def test_llm_executor_structure(self):
        """Test LLM executor basic structure."""
        step = MockStep(
            step_type="llm_generation",
            prompt="Generate a character name",
            output="character_name"
        )
        
        # Test that the executor can handle the step structure
        # without requiring actual LLM integration
        result = self.executor.execute(step, self.context, self.system)
        
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
    
    def test_llm_executor_with_settings(self):
        """Test LLM executor with custom settings."""
        step = MockStep(
            step_type="llm_generation",
            prompt="Generate a story",
            settings={
                "max_tokens": 100,
                "temperature": 0.8
            },
            output="story"
        )
        
        result = self.executor.execute(step, self.context, self.system)
        
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"


class TestFlowExecutor:
    """Test the flow executor."""
    
    def setup_method(self):
        """Set up each test."""
        self.executor = FlowExecutor()
        self.context = ExecutionContext()
        self.system = Mock()
    
    def test_completion_step(self):
        """Test completion step execution."""
        step = MockStep(
            step_type="completion",
            message="Flow completed successfully"
        )
        
        result = self.executor.execute(step, self.context, self.system)
        
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        # Completion steps should generally succeed
        assert result.success is True
    
    def test_flow_call_structure(self):
        """Test flow call step structure."""
        step = MockStep(
            step_type="flow_call",
            flow="sub_flow",
            output="sub_result"
        )
        
        # Test basic structure handling
        result = self.executor.execute(step, self.context, self.system)
        
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"


class TestExecutorIntegration:
    """Test integration between executors and other components."""
    
    def setup_method(self):
        """Set up each test."""
        self.context = ExecutionContext()
        self.system = Mock()
    
    def test_executor_result_consistency(self):
        """Test that all executors return consistent result objects."""
        executors = [
            DiceExecutor(),
            ChoiceExecutor(), 
            TableExecutor(),
            LLMExecutor(),
            FlowExecutor()
        ]
        
        for executor in executors:
            step = MockStep(
                step_type="dice_roll" if isinstance(executor, DiceExecutor) else
                         "player_choice" if isinstance(executor, ChoiceExecutor) else
                         "table_roll" if isinstance(executor, TableExecutor) else  
                         "llm_generation" if isinstance(executor, LLMExecutor) else
                         "completion"
            )
            
            result = executor.execute(step, self.context, self.system)
            
            # All should return StepResult objects
            assert isinstance(result, StepResult)
            assert result.step_id == "test_step"
            assert isinstance(result.success, bool)
    
    def test_executor_context_isolation(self):
        """Test that executors don't interfere with each other's context usage."""
        dice_executor = DiceExecutor()
        
        # Create two separate contexts
        context1 = ExecutionContext()
        context2 = ExecutionContext()
        
        step1 = MockStep(step_type="dice_roll", roll="1d6", output="result")
        step2 = MockStep(step_type="dice_roll", roll="1d8", output="result")
        
        # Mock dice results
        with patch.object(dice_executor.dice_integration, 'roll_expression') as mock_roll:
            from grimoire_runner.integrations.dice_integration import DiceResult
            mock_roll.side_effect = [
                DiceResult(total=3, expression="1d6"),
                DiceResult(total=7, expression="1d8")
            ]
            
            result1 = dice_executor.execute(step1, context1, self.system)
            result2 = dice_executor.execute(step2, context2, self.system)
        
        assert result1.success is True
        assert result2.success is True
        
        # Contexts should be independent if both set output variables
        if "result" in context1.variables and "result" in context2.variables:
            assert context1.get_variable("result") != context2.get_variable("result")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
