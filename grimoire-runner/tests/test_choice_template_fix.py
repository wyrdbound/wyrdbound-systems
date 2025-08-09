"""Test for choice executor template resolution bug fix."""

import pytest
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow_namespace import FlowNamespaceManager
from grimoire_runner.executors.choice_executor import ChoiceExecutor
from grimoire_runner.models.flow import StepDefinition, StepType


def test_choice_executor_display_format_template_resolution():
    """Test that display_format in choice_source resolves templates correctly."""
    
    # Create a mock system (minimal)
    class MockSystem:
        def get_compendium(self, name):
            return None
        def get_table(self, name):
            return None
    
    system = MockSystem()
    
    # Create execution context with sample data similar to character creation
    context = ExecutionContext()
    
    # Set up abilities data like what character creation produces
    context.set_output("knave.abilities.strength.bonus", 2)
    context.set_output("knave.abilities.dexterity.bonus", 1)
    context.set_output("knave.abilities.constitution.bonus", 3)
    context.set_output("knave.abilities.intelligence.bonus", 0)
    context.set_output("knave.abilities.wisdom.bonus", -1)
    context.set_output("knave.abilities.charisma.bonus", 1)
    
    # Create step definition similar to the character creation flow
    step = StepDefinition(
        id="test_step",
        type=StepType.PLAYER_CHOICE,
        prompt="Test choice",
        choice_source={
            "table_from_values": "outputs.knave.abilities",
            "selection_count": 2,
            "display_format": "{{ key|title }}: +{{ value.bonus }}"
        }
    )
    executor = ChoiceExecutor()
    
    # Execute the step
    result = executor.execute(step, context, system)
    
    # Should get RequiresInput with properly formatted choices
    assert result.requires_input == True
    assert result.choices is not None
    assert len(result.choices) == 6  # 6 abilities
    
    # Check that the display format was resolved properly
    choice_labels = [choice.label for choice in result.choices]
    
    # Should have resolved templates like "Strength: +2", not raw template syntax
    assert "Strength: +2" in choice_labels
    assert "Dexterity: +1" in choice_labels
    assert "Constitution: +3" in choice_labels
    assert "Intelligence: +0" in choice_labels
    assert "Wisdom: +-1" in choice_labels  # This will show as +-1
    assert "Charisma: +1" in choice_labels
    
    # Make sure no raw template syntax is present
    for label in choice_labels:
        assert "{{" not in label
        assert "}}" not in label
        assert "key" not in label
        assert "value.bonus" not in label


def test_choice_executor_template_with_context_method():
    """Test the new resolve_template_with_context method directly."""
    
    context = ExecutionContext()
    context.set_variable("base", "test")
    
    # Test that additional context overrides/adds to existing context
    additional = {
        "key": "strength", 
        "value": {"bonus": 2}
    }
    
    template = "{{ key|title }}: +{{ value.bonus }}"
    result = context.resolve_template_with_context(template, additional)
    
    assert result == "Strength: +2"
    
    # Test that base context is still available
    template_with_base = "{{ base }} - {{ key|title }}: +{{ value.bonus }}"
    result_with_base = context.resolve_template_with_context(template_with_base, additional)
    
    assert result_with_base == "test - Strength: +2"


if __name__ == "__main__":
    pytest.main([__file__])
