"""Extended tests for the GrimoireEngine to improve coverage."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.executors.base import BaseStepExecutor
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import FlowDefinition, StepDefinition, StepResult
from grimoire_runner.models.system import System


class MockExecutor(BaseStepExecutor):
    """Mock executor for testing."""

    def can_execute(self, step_type: str) -> bool:
        return step_type == "mock_step"

    def validate_step(self, step: StepDefinition) -> list[str]:
        return []

    def execute(self, step: StepDefinition, context: ExecutionContext, system: System):
        return {"result": "mock_executed"}


class TestGrimoireEngineExtended:
    """Extended tests for GrimoireEngine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()

    def test_engine_initialization(self):
        """Test that engine initializes with default executors."""
        expected_executors = {
            "dice_roll",
            "dice_sequence", 
            "player_choice",
            "table_roll",
            "llm_generation",
            "completion",
            "flow_call"
        }
        assert set(self.engine.executors.keys()) == expected_executors
        assert not self.engine._debug_mode
        assert self.engine.breakpoints == {}

    def test_register_custom_executor(self):
        """Test registering a custom executor."""
        mock_executor = MockExecutor()
        self.engine.register_executor("custom_step", mock_executor)
        
        assert "custom_step" in self.engine.executors
        assert self.engine.executors["custom_step"] is mock_executor

    def test_load_system_delegates_to_loader(self):
        """Test that load_system delegates to the loader."""
        with patch.object(self.engine.loader, 'load_system') as mock_load:
            mock_system = Mock(spec=System)
            mock_load.return_value = mock_system
            
            result = self.engine.load_system("/fake/path")
            
            assert result is mock_system
            mock_load.assert_called_once_with("/fake/path")

    def test_create_execution_context_empty(self):
        """Test creating an empty execution context."""
        context = self.engine.create_execution_context()
        
        assert isinstance(context, ExecutionContext)
        assert context.variables == {}
        assert context.inputs == {}
        assert context.outputs == {}

    def test_create_execution_context_with_variables(self):
        """Test creating context with initial variables."""
        context = self.engine.create_execution_context(
            variables={"var1": "value1", "var2": 42}
        )
        
        assert context.variables["var1"] == "value1"
        assert context.variables["var2"] == 42

    def test_create_execution_context_with_inputs_outputs(self):
        """Test creating context with initial inputs and outputs."""
        context = self.engine.create_execution_context(
            inputs={"input1": "test"},
            outputs={"output1": "result"}
        )
        
        assert context.inputs["input1"] == "test"
        assert context.outputs["output1"] == "result"

    def test_create_execution_context_with_custom_keys(self):
        """Test creating context with custom key-value pairs."""
        context = self.engine.create_execution_context(
            custom_var="custom_value",
            another_var=123
        )
        
        assert context.get_variable("custom_var") == "custom_value"
        assert context.get_variable("another_var") == 123

    def test_execute_flow_no_system_no_loaded_systems(self):
        """Test executing flow without system when no systems are loaded."""
        context = self.engine.create_execution_context()
        
        with pytest.raises(ValueError, match="No system loaded and none provided"):
            self.engine.execute_flow("test_flow", context)

    def test_execute_flow_nonexistent_flow(self):
        """Test executing a flow that doesn't exist."""
        mock_system = Mock(spec=System)
        mock_system.get_flow.return_value = None
        context = self.engine.create_execution_context()
        
        with pytest.raises(ValueError, match="Flow 'nonexistent_flow' not found"):
            self.engine.execute_flow("nonexistent_flow", context, mock_system)

    def test_execute_flow_with_system_metadata(self):
        """Test that flow execution sets system metadata in context."""
        # Create a mock system
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        mock_system.models = {}
        
        # Create a mock flow with no steps
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.outputs = []
        mock_flow.steps = []
        
        mock_system.get_flow.return_value = mock_flow
        
        context = self.engine.create_execution_context()
        result = self.engine.execute_flow("test_flow", context, mock_system)
        
        assert result.success is True
        assert context.system_metadata["id"] == "test_system"
        assert context.system_metadata["name"] == "Test System"
        assert context.system_metadata["description"] == "A test system"
        assert context.system_metadata["version"] == "1.0.0"

    def test_execute_flow_with_variables(self):
        """Test that flow execution initializes variables."""
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        mock_system.models = {}
        
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {"flow_var": "flow_value", "number_var": 42}
        mock_flow.outputs = []
        mock_flow.steps = []
        
        mock_system.get_flow.return_value = mock_flow
        
        context = self.engine.create_execution_context()
        result = self.engine.execute_flow("test_flow", context, mock_system)
        
        assert result.success is True
        assert context.get_variable("flow_var") == "flow_value"
        assert context.get_variable("number_var") == 42

    def test_execute_flow_with_model_outputs(self):
        """Test flow execution with model output initialization."""
        from grimoire_runner.models.model import ModelDefinition
        
        # Create a mock model
        mock_model = Mock(spec=ModelDefinition)
        
        # Create a mock system with the model
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        mock_system.models = {"character": mock_model}
        
        # Create a mock flow
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.steps = []
        mock_flow.outputs = []  # Add empty outputs list
        
        mock_system.get_flow.return_value = mock_flow
        
        # Test flow execution
        context = self.engine.create_execution_context()
        result = self.engine.execute_flow("test_flow", context, mock_system)
        
        assert result.success is True

    def test_execute_flow_step_failure(self):
        """Test flow execution when a step fails."""
        from grimoire_runner.models.flow import StepResult
        
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        mock_system.models = {}
        
        # Create a mock step
        mock_step = Mock(spec=StepDefinition)
        mock_step.id = "failing_step"
        
        # Create a mock flow with one failing step
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.outputs = []
        mock_flow.steps = [mock_step]
        mock_flow.get_step.return_value = mock_step
        
        mock_system.get_flow.return_value = mock_flow
        
        # Mock _execute_step to return failure
        with patch.object(self.engine, '_execute_step') as mock_execute:
            mock_execute.return_value = StepResult(
                step_id="failing_step",
                success=False,
                error="Step failed"
            )
            
            context = self.engine.create_execution_context()
            result = self.engine.execute_flow("test_flow", context, mock_system)
            
            assert result.success is False
            assert result.error == "Step failed"
            assert result.completed_at_step == "failing_step"

    def test_execute_flow_step_exception(self):
        """Test flow execution when a step throws an exception."""
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        mock_system.models = {}
        
        # Create a mock step
        mock_step = Mock(spec=StepDefinition)
        mock_step.id = "exception_step"
        
        # Create a mock flow with one step
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.outputs = []
        mock_flow.steps = [mock_step]
        mock_flow.get_step.return_value = mock_step
        
        mock_system.get_flow.return_value = mock_flow
        
        # Mock _execute_step to raise an exception
        with patch.object(self.engine, '_execute_step') as mock_execute:
            mock_execute.side_effect = RuntimeError("Unexpected error")
            
            context = self.engine.create_execution_context()
            result = self.engine.execute_flow("test_flow", context, mock_system)
            
            assert result.success is False
            assert "Unexpected error" in result.error
            assert result.completed_at_step == "exception_step"

    def test_execute_flow_value_error_propagated(self):
        """Test that ValueError exceptions are propagated (not caught)."""
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        mock_system.models = {}
        
        # Create a mock step
        mock_step = Mock(spec=StepDefinition)
        mock_step.id = "error_step"
        
        # Create a mock flow with one step
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.outputs = []
        mock_flow.steps = [mock_step]
        mock_flow.get_step.return_value = mock_step
        
        mock_system.get_flow.return_value = mock_flow
        
        # Mock _execute_step to raise ValueError
        with patch.object(self.engine, '_execute_step') as mock_execute:
            mock_execute.side_effect = ValueError("Configuration error")
            
            context = self.engine.create_execution_context()
            
            with pytest.raises(ValueError, match="Configuration error"):
                self.engine.execute_flow("test_flow", context, mock_system)

    def test_step_through_flow_no_system(self):
        """Test step-through execution without system."""
        context = self.engine.create_execution_context()
        
        with pytest.raises(ValueError, match="No system loaded and none provided"):
            list(self.engine.step_through_flow("test_flow", context))

    def test_step_through_flow_success(self):
        """Test successful step-through flow execution."""
        from grimoire_runner.models.flow import StepResult
        
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        
        # Create mock steps
        mock_step1 = Mock(spec=StepDefinition)
        mock_step1.id = "step1"
        mock_step2 = Mock(spec=StepDefinition)
        mock_step2.id = "step2"
        
        # Create a mock flow with two steps
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.steps = [mock_step1, mock_step2]
        
        def mock_get_step(step_id):
            if step_id == "step1":
                return mock_step1
            elif step_id == "step2":
                return mock_step2
            return None
        
        def mock_get_next_step(step_id):
            if step_id == "step1":
                return "step2"
            return None
        
        mock_flow.get_step.side_effect = mock_get_step
        mock_flow.get_next_step_id.side_effect = mock_get_next_step
        
        mock_system.get_flow.return_value = mock_flow
        
        # Mock _execute_step to return success
        with patch.object(self.engine, '_execute_step') as mock_execute:
            mock_execute.side_effect = [
                StepResult(step_id="step1", success=True),
                StepResult(step_id="step2", success=True)
            ]
            
            context = self.engine.create_execution_context()
            results = list(self.engine.step_through_flow("test_flow", context, mock_system))
            
            assert len(results) == 2
            assert results[0].step_id == "step1"
            assert results[1].step_id == "step2"
            assert all(r.success for r in results)

    def test_step_through_flow_failure(self):
        """Test step-through execution with step failure."""
        from grimoire_runner.models.flow import StepResult
        
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        
        # Create mock step
        mock_step = Mock(spec=StepDefinition)
        mock_step.id = "failing_step"
        
        # Create a mock flow
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.steps = [mock_step]
        mock_flow.get_step.return_value = mock_step
        
        mock_system.get_flow.return_value = mock_flow
        
        # Mock _execute_step to return failure
        with patch.object(self.engine, '_execute_step') as mock_execute:
            mock_execute.return_value = StepResult(
                step_id="failing_step",
                success=False,
                error="Step failed"
            )
            
            context = self.engine.create_execution_context()
            results = list(self.engine.step_through_flow("test_flow", context, mock_system))
            
            assert len(results) == 1
            assert results[0].step_id == "failing_step"
            assert not results[0].success
            assert results[0].error == "Step failed"

    def test_step_through_flow_exception(self):
        """Test step-through execution with exception."""
        from grimoire_runner.models.flow import StepResult
        
        mock_system = Mock(spec=System)
        mock_system.id = "test_system"
        mock_system.name = "Test System"
        mock_system.description = "A test system"
        mock_system.version = "1.0.0"
        
        # Create mock step
        mock_step = Mock(spec=StepDefinition)
        mock_step.id = "exception_step"
        
        # Create a mock flow
        mock_flow = Mock(spec=FlowDefinition)
        mock_flow.name = "Test Flow"
        mock_flow.variables = {}
        mock_flow.steps = [mock_step]
        mock_flow.get_step.return_value = mock_step
        
        mock_system.get_flow.return_value = mock_flow
        
        # Mock _execute_step to raise exception
        with patch.object(self.engine, '_execute_step') as mock_execute:
            mock_execute.side_effect = RuntimeError("Unexpected error")
            
            context = self.engine.create_execution_context()
            results = list(self.engine.step_through_flow("test_flow", context, mock_system))
            
            assert len(results) == 1
            assert results[0].step_id == "exception_step"
            assert not results[0].success
            assert "Unexpected error" in results[0].error


class TestGrimoireEngineDebugMode:
    """Tests for debug mode functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()

    def test_debug_mode_initially_disabled(self):
        """Test that debug mode is initially disabled."""
        assert not self.engine._debug_mode

    def test_enable_debug_mode(self):
        """Test enabling debug mode."""
        self.engine.enable_debug_mode()
        assert self.engine._debug_mode

    def test_disable_debug_mode(self):
        """Test disabling debug mode."""
        self.engine.enable_debug_mode()
        self.engine.disable_debug_mode()
        assert not self.engine._debug_mode

    def test_set_breakpoint(self):
        """Test setting breakpoints."""
        self.engine.set_breakpoint("test_flow", "step1")
        self.engine.set_breakpoint("test_flow", "step2")
        
        assert "test_flow" in self.engine.breakpoints
        assert "step1" in self.engine.breakpoints["test_flow"]
        assert "step2" in self.engine.breakpoints["test_flow"]

    def test_clear_breakpoints_for_flow(self):
        """Test clearing breakpoints for a specific flow."""
        self.engine.set_breakpoint("flow1", "step1")
        self.engine.set_breakpoint("flow2", "step1")
        
        self.engine.clear_breakpoints("flow1")
        
        assert "flow1" not in self.engine.breakpoints
        assert "flow2" in self.engine.breakpoints

    def test_clear_all_breakpoints(self):
        """Test clearing all breakpoints."""
        self.engine.set_breakpoint("flow1", "step1")
        self.engine.set_breakpoint("flow2", "step1")
        
        self.engine.clear_breakpoints()
        
        assert self.engine.breakpoints == {}

    def test_has_breakpoint(self):
        """Test checking for breakpoints."""
        self.engine.set_breakpoint("test_flow", "step1")
        
        assert self.engine._has_breakpoint("test_flow", "step1")
        assert not self.engine._has_breakpoint("test_flow", "step2")
        assert not self.engine._has_breakpoint("other_flow", "step1")


class TestGrimoireEngineExecuteStep:
    """Tests for step execution functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()

    def test_execute_step_unknown_executor(self):
        """Test executing step with unknown executor type."""
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "unknown_type"
        mock_step.id = "test_step"
        
        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)
        
        with pytest.raises(ValueError, match="No executor found for step type: unknown_type"):
            self.engine._execute_step(mock_step, context, system)

    def test_execute_step_validation_failure(self):
        """Test executing step that fails validation."""
        # Register a mock executor that raises validation error
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.execute.side_effect = ValueError("Validation failed: Invalid input")
        
        self.engine.register_executor("test_type", mock_executor)
        
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = None
        mock_step.actions = []
        
        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)
        
        result = self.engine._execute_step(mock_step, context, system)
        
        assert not result.success
        assert "Validation failed" in result.error

    def test_execute_step_success(self):
        """Test successful step execution."""
        # Create a simple test executor class
        class TestExecutor(BaseStepExecutor):
            def execute(self, step, context, system):
                return StepResult(
                    step_id=step.id, 
                    success=True,
                    data={"result": "test_result"}
                )
        
        self.engine.register_executor("test_type", TestExecutor())
        
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"  # Make sure this is a string, not a mock
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = "result"
        mock_step.actions = []
        
        # Ensure these attributes are properly configured
        mock_step.configure_mock(**{
            'type': "test_type",
            'id': "test_step", 
            'condition': None,
            'output': "result",
            'actions': []
        })
        
        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)
        
        result = self.engine._execute_step(mock_step, context, system)
        
        assert result.success
        assert result.step_id == "test_step"
        context.set_variable.assert_called_once_with("result", "test_result")

    def test_execute_step_no_output_variable(self):
        """Test step execution without output variable."""
        # Create a simple test executor class
        class TestExecutor(BaseStepExecutor):
            def execute(self, step, context, system):
                return StepResult(
                    step_id=step.id, 
                    success=True,
                    data={"result": "test_result"}
                )
        
        self.engine.register_executor("test_type", TestExecutor())
        
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = None  # No output variable
        mock_step.actions = []
        
        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)
        
        result = self.engine._execute_step(mock_step, context, system)
        
        assert result.success
        assert result.step_id == "test_step"
        # Should not call set_variable when no output variable is specified
        context.set_variable.assert_not_called()

    def test_execute_step_execution_exception(self):
        """Test step execution that throws an exception."""
        # Register a mock executor that throws an exception
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.validate_step.return_value = []
        mock_executor.execute.side_effect = RuntimeError("Execution failed")
        
        self.engine.register_executor("test_type", mock_executor)
        
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        
        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)
        
        result = self.engine._execute_step(mock_step, context, system)
        
        assert not result.success
        assert "Execution failed" in result.error
