"""
Tests for base executor interface.
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.executors.base import BaseStepExecutor


class ConcreteExecutor(BaseStepExecutor):
    """Concrete implementation for testing."""

    def execute(self, step, context, system):
        """Test implementation."""
        from grimoire_runner.models.flow import StepResult

        return StepResult(step_id=step.id, success=True)


class TestBaseStepExecutor:
    """Test the BaseStepExecutor abstract class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseStepExecutor cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseStepExecutor()

    def test_concrete_implementation(self):
        """Test concrete implementation can be instantiated."""
        executor = ConcreteExecutor()
        assert executor is not None

    def test_can_execute_default_behavior(self):
        """Test default can_execute behavior."""
        executor = ConcreteExecutor()
        step = Mock()

        # Default implementation returns True
        assert executor.can_execute(step) is True

    def test_validate_step_default_behavior(self):
        """Test default validate_step behavior."""
        executor = ConcreteExecutor()
        step = Mock()

        # Default implementation returns empty list
        errors = executor.validate_step(step)
        assert errors == []

    def test_execute_method_exists(self):
        """Test that execute method exists and is callable."""
        executor = ConcreteExecutor()
        assert hasattr(executor, "execute")
        assert callable(executor.execute)

    def test_abstract_methods_enforced(self):
        """Test that abstract methods are enforced."""
        # Class without execute method should fail
        with pytest.raises(TypeError):

            class IncompleteExecutor(BaseStepExecutor):
                pass

            IncompleteExecutor()


class CustomExecutor(BaseStepExecutor):
    """Custom executor for testing overridden methods."""

    def execute(self, step, context, system):
        """Custom execute implementation."""
        from grimoire_runner.models.flow import StepResult

        return StepResult(step_id=step.id, success=True, data={"custom": True})

    def can_execute(self, step):
        """Custom can_execute implementation."""
        return step.type == "custom_type"

    def validate_step(self, step):
        """Custom validate_step implementation."""
        errors = []
        if not hasattr(step, "custom_param"):
            errors.append("Missing custom_param")
        return errors


class TestCustomExecutor:
    """Test custom executor implementations."""

    def test_custom_can_execute(self):
        """Test custom can_execute implementation."""
        executor = CustomExecutor()

        # Should return True for custom_type
        step1 = Mock()
        step1.type = "custom_type"
        assert executor.can_execute(step1) is True

        # Should return False for other types
        step2 = Mock()
        step2.type = "other_type"
        assert executor.can_execute(step2) is False

    def test_custom_validate_step(self):
        """Test custom validate_step implementation."""
        executor = CustomExecutor()

        # Step with custom_param should be valid
        step1 = Mock()
        step1.custom_param = "value"
        errors = executor.validate_step(step1)
        assert errors == []

        # Step without custom_param should have error
        step2 = Mock()
        del step2.custom_param  # Remove the attribute
        errors = executor.validate_step(step2)
        assert len(errors) == 1
        assert "Missing custom_param" in errors[0]

    def test_custom_execute(self):
        """Test custom execute implementation."""
        executor = CustomExecutor()
        step = Mock()
        step.id = "test_step"
        context = Mock()
        system = Mock()

        result = executor.execute(step, context, system)

        assert result.step_id == "test_step"
        assert result.success is True
        assert result.data["custom"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
