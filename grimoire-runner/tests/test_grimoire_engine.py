"""
Tests for the GRIMOIRE Engine.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.executors.base import BaseStepExecutor
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import FlowResult, StepResult
from grimoire_runner.models.system import System


class MockStepExecutor(BaseStepExecutor):
    """Mock step executor for testing."""

    def __init__(self, return_value="mock_result"):
        self.return_value = return_value
        self.executed_steps = []

    def execute(self, step, context, system=None):
        self.executed_steps.append(step)
        result = StepResult(
            step_id=step.id,
            success=True,
            data={"result": self.return_value, "mock": True},
        )
        if hasattr(step, "output") and step.output:
            context.set_variable(step.output, self.return_value)
        return result


class TestGrimoireEngine:
    """Test the GrimoireEngine class."""

    def setup_method(self):
        """Set up each test."""
        self.engine = GrimoireEngine()

    def create_test_system(self, temp_dir: str) -> Path:
        """Create a test system for engine testing."""
        system_dir = Path(temp_dir) / "engine_test_system"
        system_dir.mkdir()

        # Create system.yaml
        system_data = {
            "id": "engine_test_system",
            "name": "Engine Test System",
            "version": "1.0.0",
            "description": "A system for testing the engine",
            "currency": {
                "base_unit": "gold",
                "denominations": {
                    "copper": {"name": "Copper", "symbol": "cp", "value": 1},
                    "gold": {"name": "Gold", "symbol": "gp", "value": 100},
                },
            },
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_dir / subdir).mkdir()

        # Create test flows
        flows_dir = system_dir / "flows"

        # Simple flow
        simple_flow = {
            "id": "simple_flow",
            "name": "Simple Flow",
            "description": "A simple test flow",
            "variables": {"initial_value": 42},
            "steps": [
                {
                    "id": "step1",
                    "name": "First Step",
                    "type": "dice_roll",
                    "roll": "1d6",
                    "output": "dice_result",
                }
            ],
        }

        with open(flows_dir / "simple_flow.yaml", "w") as f:
            yaml.dump(simple_flow, f)

        # Multi-step flow
        multi_step_flow = {
            "id": "multi_step_flow",
            "name": "Multi Step Flow",
            "description": "A flow with multiple steps",
            "steps": [
                {
                    "id": "dice_step",
                    "name": "Roll Dice",
                    "type": "dice_roll",
                    "roll": "2d6",
                    "output": "dice_value",
                },
                {
                    "id": "choice_step",
                    "name": "Make Choice",
                    "type": "player_choice",
                    "prompt": "Choose an option:",
                    "choices": [
                        {"id": "option_a", "label": "Option A"},
                        {"id": "option_b", "label": "Option B"},
                    ],
                    "output": "choice_value",
                },
                {
                    "id": "final_step",
                    "name": "Final Step",
                    "type": "dice_roll",
                    "roll": "1d4",
                    "output": "final_result",
                },
            ],
        }

        with open(flows_dir / "multi_step_flow.yaml", "w") as f:
            yaml.dump(multi_step_flow, f)

        # Flow with variables
        variable_flow = {
            "id": "variable_flow",
            "name": "Variable Flow",
            "description": "A flow that uses variables",
            "variables": {"multiplier": 2, "base_value": 10, "message": "Test message"},
            "steps": [
                {
                    "id": "variable_step",
                    "name": "Variable Step",
                    "type": "dice_roll",
                    "roll": "1d6",
                    "output": "variable_result",
                }
            ],
        }

        with open(flows_dir / "variable_flow.yaml", "w") as f:
            yaml.dump(variable_flow, f)

        return system_dir

    def test_engine_initialization(self):
        """Test that GrimoireEngine initializes correctly."""
        assert isinstance(self.engine.loader, SystemLoader)
        assert isinstance(self.engine.executors, dict)
        assert len(self.engine.executors) > 0
        assert isinstance(self.engine.breakpoints, dict)
        assert self.engine._debug_mode is False

        # Check default executors are registered
        expected_executors = [
            "dice_roll",
            "dice_sequence",
            "player_choice",
            "table_roll",
            "llm_generation",
            "completion",
            "flow_call",
        ]

        for executor_type in expected_executors:
            assert executor_type in self.engine.executors
            assert isinstance(self.engine.executors[executor_type], BaseStepExecutor)

    def test_register_custom_executor(self):
        """Test registering a custom step executor."""
        mock_executor = MockStepExecutor()

        self.engine.register_executor("custom_type", mock_executor)

        assert "custom_type" in self.engine.executors
        assert self.engine.executors["custom_type"] is mock_executor

    def test_load_system(self):
        """Test loading a system through the engine."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)

            system = self.engine.load_system(system_path)

            assert isinstance(system, System)
            assert system.id == "engine_test_system"
            assert system.name == "Engine Test System"

    def test_create_execution_context(self):
        """Test creating execution contexts."""
        # Basic context
        context = self.engine.create_execution_context()
        assert isinstance(context, ExecutionContext)

        # Context with initial data
        context = self.engine.create_execution_context(
            variables={"test_var": "test_value"},
            inputs={"input1": "value1"},
            outputs={"output1": "result1"},
            custom_field="custom_value",
        )

        assert context.get_variable("test_var") == "test_value"
        assert context.inputs["input1"] == "value1"
        assert context.outputs["output1"] == "result1"
        assert context.get_variable("custom_field") == "custom_value"

    def test_execute_simple_flow(self):
        """Test executing a simple flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            # Replace dice executor with mock for predictable results
            mock_executor = MockStepExecutor(return_value=4)
            self.engine.register_executor("dice_roll", mock_executor)

            result = self.engine.execute_flow("simple_flow", context, system)

            assert isinstance(result, FlowResult)
            assert result.flow_id == "simple_flow"
            assert result.success is True
            assert len(result.step_results) == 1
            assert result.step_results[0].step_id == "step1"
            assert context.get_variable("dice_result") == 4
            assert context.get_variable("initial_value") == 42  # Flow variable

    def test_execute_multi_step_flow(self):
        """Test executing a flow with multiple steps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            # Replace executors with mocks
            dice_executor = MockStepExecutor(return_value=8)
            choice_executor = MockStepExecutor(return_value="option_a")

            self.engine.register_executor("dice_roll", dice_executor)
            self.engine.register_executor("player_choice", choice_executor)

            result = self.engine.execute_flow("multi_step_flow", context, system)

            assert result.success is True
            assert len(result.step_results) == 3

            # Check step execution order
            assert result.step_results[0].step_id == "dice_step"
            assert result.step_results[1].step_id == "choice_step"
            assert result.step_results[2].step_id == "final_step"

            # Check variables were set
            assert context.get_variable("dice_value") == 8
            assert context.get_variable("choice_value") == "option_a"
            assert context.get_variable("final_result") == 8  # From mock

    def test_execute_flow_with_variables(self):
        """Test executing a flow that sets variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            mock_executor = MockStepExecutor(return_value=3)
            self.engine.register_executor("dice_roll", mock_executor)

            result = self.engine.execute_flow("variable_flow", context, system)

            assert result.success is True

            # Check flow variables were set in context
            assert context.get_variable("multiplier") == 2
            assert context.get_variable("base_value") == 10
            assert context.get_variable("message") == "Test message"
            assert context.get_variable("variable_result") == 3

    def test_execute_nonexistent_flow(self):
        """Test executing a flow that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            with pytest.raises(ValueError, match="Flow 'nonexistent' not found"):
                self.engine.execute_flow("nonexistent", context, system)

    def test_execute_flow_without_system(self):
        """Test executing a flow without providing a system."""
        context = self.engine.create_execution_context()

        with pytest.raises(ValueError, match="No system loaded"):
            self.engine.execute_flow("any_flow", context)

    def test_execute_flow_with_missing_executor(self):
        """Test flow execution with a step type that has no registered executor."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_minimal_system(temp_dir, "missing_executor_system")
            flows_dir = system_dir / "flows"

            # Create flow with a valid step type but remove its executor
            flow_data = {
                "id": "unregistered_executor_flow",
                "name": "Unregistered Executor Flow",
                "steps": [
                    {
                        "id": "dice_step",
                        "name": "Dice Step",
                        "type": "dice_roll",
                        "roll": "1d6",
                    }
                ],
            }

            with open(flows_dir / "unregistered_executor_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.engine.load_system(system_dir)
            context = self.engine.create_execution_context()

            # Remove the dice_roll executor to simulate missing executor
            del self.engine.executors["dice_roll"]

            with pytest.raises(ValueError, match="No executor found for step type"):
                self.engine.execute_flow("unregistered_executor_flow", context, system)

    def create_minimal_system(
        self, temp_dir: str, system_id: str = "minimal_system"
    ) -> Path:
        """Create a minimal system for testing."""
        system_dir = Path(temp_dir) / system_id
        system_dir.mkdir()

        # Create system.yaml
        system_data = {
            "id": system_id,
            "name": "Minimal Test System",
            "version": "1.0.0",
            "description": "A minimal system for testing",
            "currency": {
                "base_unit": "gold",
                "denominations": {
                    "gold": {"name": "Gold", "symbol": "gp", "value": 100}
                },
            },
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_dir / subdir).mkdir()

        return system_dir

    def test_step_execution_with_error(self):
        """Test flow execution when a step fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            # Create mock executor that fails
            class FailingExecutor(BaseStepExecutor):
                def execute(self, step, context, system=None):
                    return StepResult(
                        step_id=step.id,
                        success=False,
                        error="Mock execution error",
                        data={"failed": True},
                    )

            self.engine.register_executor("dice_roll", FailingExecutor())

            result = self.engine.execute_flow("simple_flow", context, system)

            assert result.success is False
            assert len(result.step_results) == 1
            assert result.step_results[0].success is False
            assert "Mock execution error" in result.step_results[0].error

    def test_execution_iterator(self):
        """Test step-by-step execution using iterator."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            # Replace executors with mocks
            dice_executor = MockStepExecutor(return_value=6)
            choice_executor = MockStepExecutor(return_value="option_b")

            self.engine.register_executor("dice_roll", dice_executor)
            self.engine.register_executor("player_choice", choice_executor)

            # Execute step by step
            step_count = 0
            for step_result in self.engine.execute_flow_steps(
                "multi_step_flow", context, system
            ):
                step_count += 1
                assert isinstance(step_result, StepResult)
                assert step_result.success is True

            assert step_count == 3  # Three steps in multi_step_flow

    def test_debug_mode(self):
        """Test debug mode functionality."""
        assert self.engine._debug_mode is False

        self.engine.set_debug_mode(True)
        assert self.engine._debug_mode is True

        self.engine.set_debug_mode(False)
        assert self.engine._debug_mode is False

    def test_breakpoints(self):
        """Test breakpoint functionality."""
        flow_id = "test_flow"
        step_ids = ["step1", "step2"]

        # Set breakpoints
        self.engine.set_breakpoints(flow_id, step_ids)
        assert flow_id in self.engine.breakpoints
        assert self.engine.breakpoints[flow_id] == step_ids

        # Check breakpoint
        assert self.engine.has_breakpoint(flow_id, "step1") is True
        assert self.engine.has_breakpoint(flow_id, "step3") is False
        assert self.engine.has_breakpoint("other_flow", "step1") is False

        # Clear breakpoints
        self.engine.clear_breakpoints(flow_id)
        assert flow_id not in self.engine.breakpoints

    def test_system_metadata_in_context(self):
        """Test that system metadata is set in execution context."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)
            context = self.engine.create_execution_context()

            mock_executor = MockStepExecutor()
            self.engine.register_executor("dice_roll", mock_executor)

            self.engine.execute_flow("simple_flow", context, system)

            assert hasattr(context, "system_metadata")
            assert context.system_metadata["id"] == "engine_test_system"
            assert context.system_metadata["name"] == "Engine Test System"
            assert context.system_metadata["version"] == "1.0.0"
            assert "currency" in context.system_metadata

    def test_flow_execution_with_initial_context_data(self):
        """Test flow execution with pre-populated context data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)

            # Create context with initial data
            context = self.engine.create_execution_context(
                variables={"pre_existing": "value"}, inputs={"user_input": "test_input"}
            )

            mock_executor = MockStepExecutor()
            self.engine.register_executor("dice_roll", mock_executor)

            result = self.engine.execute_flow("simple_flow", context, system)

            assert result.success is True
            # Pre-existing data should be preserved
            assert context.get_variable("pre_existing") == "value"
            assert context.inputs["user_input"] == "test_input"
            # Flow variables should be added
            assert context.get_variable("initial_value") == 42

    def test_concurrent_flow_execution(self):
        """Test that multiple flows can be executed concurrently with different contexts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)
            system = self.engine.load_system(system_path)

            # Create separate contexts
            context1 = self.engine.create_execution_context()
            context2 = self.engine.create_execution_context()

            # Use different mock values for each execution
            mock_executor1 = MockStepExecutor(return_value=10)
            mock_executor2 = MockStepExecutor(return_value=20)

            # Create separate engines for concurrent execution
            engine1 = GrimoireEngine()
            engine2 = GrimoireEngine()

            engine1.register_executor("dice_roll", mock_executor1)
            engine2.register_executor("dice_roll", mock_executor2)

            # Execute flows
            result1 = engine1.execute_flow("simple_flow", context1, system)
            result2 = engine2.execute_flow("simple_flow", context2, system)

            # Results should be independent
            assert result1.success is True
            assert result2.success is True
            assert context1.get_variable("dice_result") == 10
            assert context2.get_variable("dice_result") == 20


@pytest.mark.performance
class TestGrimoireEnginePerformance:
    """Test GrimoireEngine performance characteristics."""

    def setup_method(self):
        """Set up each test."""
        self.engine = GrimoireEngine()

    def test_large_flow_execution_performance(self):
        """Test performance with flows containing many steps."""
        import time

        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "performance_system"
            system_dir.mkdir()

            # Create system
            system_data = {
                "id": "performance_system",
                "name": "Performance System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories
            flows_dir = system_dir / "flows"
            flows_dir.mkdir()

            # Create flow with many steps
            large_flow = {"id": "large_flow", "name": "Large Flow", "steps": []}

            # Add 100 steps
            for i in range(100):
                large_flow["steps"].append(
                    {
                        "id": f"step_{i}",
                        "name": f"Step {i}",
                        "type": "dice_roll",
                        "roll": "1d6",
                        "output": f"result_{i}",
                    }
                )

            with open(flows_dir / "large_flow.yaml", "w") as f:
                yaml.dump(large_flow, f)

            system = self.engine.load_system(system_dir)
            context = self.engine.create_execution_context()

            # Use fast mock executor
            mock_executor = MockStepExecutor(return_value=1)
            self.engine.register_executor("dice_roll", mock_executor)

            # Time execution
            start_time = time.time()
            result = self.engine.execute_flow("large_flow", context, system)
            execution_time = time.time() - start_time

            assert result.success is True
            assert len(result.step_results) == 100
            assert execution_time < 1.0  # Should complete in under 1 second

    def test_memory_usage_during_execution(self):
        """Test memory usage during flow execution."""
        import gc
        import tracemalloc

        tracemalloc.start()

        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "memory_system"
            system_dir.mkdir()

            # Create system
            system_data = {
                "id": "memory_system",
                "name": "Memory System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories
            flows_dir = system_dir / "flows"
            flows_dir.mkdir()

            # Create flow
            flow_data = {
                "id": "memory_flow",
                "name": "Memory Flow",
                "steps": [
                    {
                        "id": "memory_step",
                        "name": "Memory Step",
                        "type": "dice_roll",
                        "roll": "1d6",
                        "output": "result",
                    }
                ],
            }

            with open(flows_dir / "memory_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.engine.load_system(system_dir)
            mock_executor = MockStepExecutor()
            self.engine.register_executor("dice_roll", mock_executor)

            # Take initial memory snapshot
            snapshot1 = tracemalloc.take_snapshot()

            # Execute flow multiple times
            for i in range(100):
                context = self.engine.create_execution_context()
                self.engine.execute_flow("memory_flow", context, system)

                if i % 20 == 0:
                    gc.collect()  # Force garbage collection

            # Take final memory snapshot
            snapshot2 = tracemalloc.take_snapshot()

            # Check memory growth
            top_stats = snapshot2.compare_to(snapshot1, "lineno")
            total_growth = sum(stat.size_diff for stat in top_stats)

            # Memory growth should be reasonable (less than 5MB)
            assert abs(total_growth) < 5 * 1024 * 1024

        tracemalloc.stop()


class TestGrimoireEngineErrorHandling:
    """Test error handling in GrimoireEngine."""

    def setup_method(self):
        """Set up each test."""
        self.engine = GrimoireEngine()

    def test_executor_exception_handling(self):
        """Test handling of exceptions thrown by executors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "exception_system"
            system_dir.mkdir()

            # Create system
            system_data = {
                "id": "exception_system",
                "name": "Exception System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories
            flows_dir = system_dir / "flows"
            flows_dir.mkdir()

            # Create flow
            flow_data = {
                "id": "exception_flow",
                "name": "Exception Flow",
                "steps": [
                    {
                        "id": "exception_step",
                        "name": "Exception Step",
                        "type": "dice_roll",
                        "roll": "1d6",
                    }
                ],
            }

            with open(flows_dir / "exception_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.engine.load_system(system_dir)
            context = self.engine.create_execution_context()

            # Create executor that throws exception
            class ExceptionExecutor(BaseStepExecutor):
                def execute(self, step, context, system=None):
                    raise RuntimeError("Test exception")

            self.engine.register_executor("dice_roll", ExceptionExecutor())

            # Execution should handle exception gracefully
            result = self.engine.execute_flow("exception_flow", context, system)

            assert result.success is False
            assert len(result.step_results) == 1
            assert result.step_results[0].success is False
            assert "Test exception" in str(result.step_results[0].error)

    def test_corrupted_flow_handling(self):
        """Test handling of corrupted flow definitions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "corrupted_flow_system"
            system_dir.mkdir()

            # Create system
            system_data = {
                "id": "corrupted_flow_system",
                "name": "Corrupted Flow System",
                "version": "1.0.0",
            }

            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)

            # Create directories
            for subdir in ["flows", "models", "compendium", "tables", "sources"]:
                (system_dir / subdir).mkdir()

            flows_dir = system_dir / "flows"

            # Create corrupted flow file
            with open(flows_dir / "corrupted_flow.yaml", "w") as f:
                f.write("invalid: yaml: content: {{{")

            # Loading system should handle corrupted flow gracefully (just log error)
            system = self.engine.load_system(system_dir)

            # System loads successfully but corrupted flow is not included
            assert isinstance(system, System)
            assert len(system.flows) == 0  # No flows loaded due to corruption


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
