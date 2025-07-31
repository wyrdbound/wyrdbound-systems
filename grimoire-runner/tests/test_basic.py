"""
Basic test suite for the GRIMOIRE runner.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner import GrimoireEngine
from grimoire_runner.core.context import ExecutionContext
from grimoire_runner.models.flow import StepDefinition, StepType
from grimoire_runner.models.system import System


class TestGrimoireEngine:
    """Test the core GRIMOIRE engine functionality."""

    def test_engine_creation(self):
        """Test that we can create a GRIMOIRE engine."""
        engine = GrimoireEngine()
        assert engine is not None

    def test_create_execution_context(self):
        """Test that we can create an execution context."""
        engine = GrimoireEngine()
        context = engine.create_execution_context()
        assert isinstance(context, ExecutionContext)
        assert context.variables is not None


class TestSystemLoading:
    """Test system loading functionality."""

    def create_test_system(self, temp_dir):
        """Create a minimal test system in a temporary directory."""
        system_dir = Path(temp_dir) / "test_system"
        system_dir.mkdir()

        # Create system.yaml
        system_data = {
            "id": "test_system",
            "name": "Test System",
            "version": "1.0.0",
            "description": "A test system for unit tests",
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create empty directories
        (system_dir / "flows").mkdir()
        (system_dir / "models").mkdir()
        (system_dir / "compendium").mkdir()
        (system_dir / "tables").mkdir()
        (system_dir / "sources").mkdir()

        return system_dir

    def test_load_minimal_system(self):
        """Test loading a minimal GRIMOIRE system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_system(temp_dir)

            engine = GrimoireEngine()
            system = engine.load_system(system_dir)

            assert isinstance(system, System)
            assert system.id == "test_system"
            assert system.name == "Test System"
            assert system.version == "1.0.0"


class TestFlowExecution:
    """Test flow execution functionality."""

    def create_test_flow(self, temp_dir):
        """Create a minimal test flow."""
        system_dir = self.create_test_system(temp_dir)
        flows_dir = system_dir / "flows"

        # Create a simple flow
        flow_data = {
            "id": "test_flow",
            "name": "Test Flow",
            "description": "A simple test flow",
            "steps": [
                {"id": "step1", "type": "dice_roll", "roll": "1d6", "output": "result"}
            ],
        }

        with open(flows_dir / "test_flow.yaml", "w") as f:
            yaml.dump(flow_data, f)

        return system_dir

    def create_test_system(self, temp_dir):
        """Create a minimal test system in a temporary directory."""
        system_dir = Path(temp_dir) / "test_system"
        system_dir.mkdir()

        # Create system.yaml
        system_data = {
            "id": "test_system",
            "name": "Test System",
            "version": "1.0.0",
            "description": "A test system for unit tests",
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_dir / subdir).mkdir()

        return system_dir

    def test_execute_simple_flow(self):
        """Test executing a simple dice flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_flow(temp_dir)

            engine = GrimoireEngine()
            system = engine.load_system(system_dir)
            context = engine.create_execution_context()

            # Execute the flow
            result = engine.execute_flow("test_flow", context, system)

            assert result is not None
            # Note: We can't test success without dice integration
            # but we can test that the flow was found and attempted


class TestModelValidation:
    """Test data model validation."""

    def test_flow_step_validation(self):
        """Test that flow steps validate correctly."""
        # Valid step
        step_data = {
            "id": "test_step",
            "name": "Test Step",
            "type": StepType.DICE_ROLL,
            "roll": "1d6",
        }
        step = StepDefinition(**step_data)
        assert step.id == "test_step"
        assert step.type == StepType.DICE_ROLL
        assert step.roll == "1d6"

    def test_system_definition(self):
        """Test system definition creation."""
        system_data = {
            "id": "test",
            "name": "Test System",
            "version": "1.0.0",
            "description": "Test",
        }
        system = System(**system_data)
        assert system.id == "test"
        assert system.name == "Test System"


if __name__ == "__main__":
    pytest.main([__file__])
