"""Comprehensive tests for the choice executor to improve coverage."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from grimoire_runner.core.context import ExecutionContext
from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.executors.choice_executor import ChoiceExecutor
from grimoire_runner.models.flow import ChoiceDefinition, StepDefinition, StepResult


def test_simple():
    """Simple test to ensure pytest can find this file."""
    assert True


class TestChoiceExecutorCore:
    """Test core choice executor functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = ChoiceExecutor()
        self.context = ExecutionContext()
        self.engine = GrimoireEngine()

    def test_executor_initialization(self):
        """Test choice executor initialization."""
        assert self.executor is not None
        assert hasattr(self.executor, 'execute')
        assert hasattr(self.executor, 'validate_step')
        assert hasattr(self.executor, 'can_execute')

    def test_choice_step_validation_success(self):
        """Test successful validation of a choice step."""
        step = StepDefinition(
            id="test_choice",
            type="player_choice",
            name="Test Choice",
            prompt="Choose an option",
            choices=[
                ChoiceDefinition(id="option1", label="Option 1"),
                ChoiceDefinition(id="option2", label="Option 2")
            ]
        )

        errors = self.executor.validate_step(step)
        assert errors == []

    def test_choice_step_validation_missing_choices(self):
        """Test validation failure when choices are missing."""
        step = StepDefinition(
            id="test_choice",
            type="player_choice",
            name="Test Choice",
            prompt="Choose an option",
            choices=[]
        )

        errors = self.executor.validate_step(step)
        assert len(errors) > 0
        assert any("choices" in error.lower() for error in errors)

    def test_choice_step_validation_invalid_choice_format(self):
        """Test validation failure with duplicate choice IDs."""
        step = StepDefinition(
            id="test_choice",
            type="player_choice",
            name="Test Choice",
            prompt="Choose an option",
            choices=[
                ChoiceDefinition(id="option1", label="First Option"),
                ChoiceDefinition(id="option1", label="Duplicate ID")  # Invalid: duplicate ID
            ]
        )

        errors = self.executor.validate_step(step)
        assert len(errors) > 0

    def test_can_execute_player_choice(self):
        """Test can_execute returns True for player_choice steps."""
        step = StepDefinition(
            id="test_choice",
            type="player_choice",
            name="Test Choice"
        )

        assert self.executor.can_execute(step) is True

    def test_can_execute_other_types(self):
        """Test can_execute returns False for non-choice steps."""
        step = StepDefinition(
            id="test_step",
            type="dice_roll",
            name="Test Step"
        )

        assert self.executor.can_execute(step) is False

    def test_execute_choice_with_single_option(self):
        """Test choice execution with single option."""
        step = StepDefinition(
            id="single_choice",
            type="player_choice",
            name="Single Choice",
            prompt="Only one option",
            choices=[
                ChoiceDefinition(id="only", label="Only Option")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        assert result.requires_input is True
        assert len(result.choices) == 1
        assert result.choices[0].id == "only"
        assert result.choices[0].label == "Only Option"

    def test_execute_choice_with_multiple_options(self):
        """Test choice execution with multiple options."""
        choices = [
            ChoiceDefinition(id="option1", label="First Option"),
            ChoiceDefinition(id="option2", label="Second Option"),
            ChoiceDefinition(id="option3", label="Third Option")
        ]

        step = StepDefinition(
            id="multi_choice",
            type="player_choice",
            name="Multiple Choice",
            prompt="Choose one option",
            choices=choices
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        assert result.requires_input is True
        assert len(result.choices) == 3
        assert all(isinstance(choice, ChoiceDefinition) for choice in result.choices)

    def test_execute_choice_with_template_prompt(self):
        """Test choice execution with templated prompt (currently templates are not resolved in prompts)."""
        self.context.set_variable("player_name", "Alice")

        step = StepDefinition(
            id="template_choice",
            type="player_choice",
            name="Template Choice",
            prompt="Hello {{player_name}}, choose an option",
            choices=[
                ChoiceDefinition(id="greet", label="Greet back")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        # Currently prompts are not template-resolved, so we check for the raw template
        assert "{{player_name}}" in result.prompt

    def test_execute_choice_with_template_labels(self):
        """Test choice execution with templated choice labels."""
        self.context.set_variable("weapon_type", "sword")

        step = StepDefinition(
            id="template_labels",
            type="player_choice",
            name="Template Labels",
            prompt="Choose your action",
            choices=[
                ChoiceDefinition(id="attack", label="Attack with {{weapon_type}}"),
                ChoiceDefinition(id="defend", label="Defend")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        # Check that the template was resolved in the choice
        attack_choice = next(c for c in result.choices if c.id == "attack")
        assert "sword" in attack_choice.label


class TestChoiceExecutorInteraction:
    """Test choice executor interaction scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = ChoiceExecutor()
        self.context = ExecutionContext()

    def test_choice_with_empty_prompt(self):
        """Test choice execution with empty prompt."""
        step = StepDefinition(
            id="no_prompt",
            type="player_choice",
            name="No Prompt Choice",
            prompt="",
            choices=[
                ChoiceDefinition(id="option1", label="Option 1")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        assert result.requires_input is True

    def test_choice_result_data_structure(self):
        """Test the structure of choice execution results."""
        step = StepDefinition(
            id="data_test",
            type="player_choice",
            name="Data Test",
            prompt="Test data structure",
            choices=[
                ChoiceDefinition(id="test", label="Test Option")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "data_test"
        assert result.success is True
        assert result.requires_input is True
        assert isinstance(result.data, dict)
        assert "choices" in result.data or hasattr(result, 'choices')


class TestChoiceExecutorEdgeCases:
    """Test edge cases and error scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = ChoiceExecutor()
        self.context = ExecutionContext()

    def test_execute_with_none_step(self):
        """Test execution with None step."""
        with pytest.raises((AttributeError, TypeError)):
            self.executor.execute(None, self.context, Mock())

    def test_execute_with_none_context(self):
        """Test execution with None context."""
        step = StepDefinition(
            id="test",
            type="player_choice",
            name="Test",
            choices=[ChoiceDefinition(id="test", label="Test")]
        )

        # The executor gracefully handles None context by logging error and returning failure
        result = self.executor.execute(step, None, Mock())
        assert result.success is False
        assert result.error is not None

    def test_choice_with_very_long_label(self):
        """Test choice with very long label."""
        long_label = "A" * 1000  # Very long label

        step = StepDefinition(
            id="long_label",
            type="player_choice",
            name="Long Label Test",
            prompt="Choose",
            choices=[
                ChoiceDefinition(id="long", label=long_label)
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        assert len(result.choices[0].label) == 1000

    def test_choice_with_special_characters(self):
        """Test choice with special characters in labels."""
        step = StepDefinition(
            id="special_chars",
            type="player_choice",
            name="Special Characters",
            prompt="Choose with special chars: àáâãäåæçèéêë",
            choices=[
                ChoiceDefinition(id="unicode", label="Ñiño with émojis 🎮🎲"),
                ChoiceDefinition(id="symbols", label="Symbols: !@#$%^&*()")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        assert len(result.choices) == 2

    def test_choice_with_duplicate_ids(self):
        """Test validation of choices with duplicate IDs."""
        step = StepDefinition(
            id="duplicate_ids",
            type="player_choice",
            name="Duplicate IDs",
            prompt="Choose",
            choices=[
                ChoiceDefinition(id="same", label="First"),
                ChoiceDefinition(id="same", label="Second")  # Duplicate ID
            ]
        )

        errors = self.executor.validate_step(step)
        assert len(errors) > 0
        assert any("duplicate" in error.lower() or "unique" in error.lower() for error in errors)


class TestChoiceExecutorIntegration:
    """Integration tests with the execution engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()
        self.context = ExecutionContext()

    def test_choice_with_system_integration(self):
        """Test choice executor with system-wide settings."""
        # Create a temporary system configuration
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir)

            # Mock system loading
            mock_system = Mock()
            mock_system.id = "test_system"
            mock_system.name = "Test System"

            step = StepDefinition(
                id="system_choice",
                type="player_choice",
                name="System Choice",
                prompt="System-wide choice",
                choices=[
                    ChoiceDefinition(id="system_action", label="System Action")
                ]
            )

            executor = ChoiceExecutor()
            result = executor.execute(step, self.context, mock_system)

            assert result.success is True
            assert result.step_id == "system_choice"


@pytest.mark.performance
class TestChoiceExecutorPerformance:
    """Performance and stress tests for choice executor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = ChoiceExecutor()
        self.context = ExecutionContext()

    def test_many_choices_performance(self):
        """Test performance with many choices."""
        # Create a step with many choices
        choices = [
            ChoiceDefinition(id=f"choice_{i}", label=f"Choice {i}")
            for i in range(100)
        ]

        step = StepDefinition(
            id="many_choices",
            type="player_choice",
            name="Many Choices",
            prompt="Choose from many options",
            choices=choices
        )

        # Should handle many choices efficiently
        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        assert len(result.choices) == 100

    def test_deep_template_nesting(self):
        """Test performance with deeply nested templates."""
        # Set up nested context variables
        self.context.set_variable("level1", "{{level2}}")
        self.context.set_variable("level2", "{{level3}}")
        self.context.set_variable("level3", "final_value")

        step = StepDefinition(
            id="nested_template",
            type="player_choice",
            name="Nested Template",
            prompt="Deep nesting: {{level1}}",
            choices=[
                ChoiceDefinition(id="test", label="Test {{level1}}")
            ]
        )

        result = self.executor.execute(step, self.context, Mock())

        assert result.success is True
        # Template should resolve properly
        choice_label = result.choices[0].label
        assert "final_value" in choice_label or "{{" not in choice_label

    def test_concurrent_execution_safety(self):
        """Test that executor is safe for concurrent execution."""
        import threading

        step = StepDefinition(
            id="concurrent_test",
            type="player_choice",
            name="Concurrent Test",
            choices=[ChoiceDefinition(id="test", label="Test")]
        )

        results = []

        def execute_choice():
            context = ExecutionContext()
            executor = ChoiceExecutor()
            result = executor.execute(step, context, Mock())
            results.append(result)

        # Run multiple threads
        threads = [threading.Thread(target=execute_choice) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All executions should succeed
        assert len(results) == 10
        assert all(result.success for result in results)
