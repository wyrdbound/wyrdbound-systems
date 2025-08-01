"""
Tests for template handling and resolution.
"""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.utils.templates import TemplateHelpers


class TestTemplateHelpers:
    """Test the TemplateHelpers utility class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.helpers = TemplateHelpers()

    def test_basic_template_rendering(self):
        """Test basic template rendering functionality."""
        template = "Hello {{ name }}!"
        context = {"name": "World"}
        result = self.helpers.render_template(template, context)
        assert result == "Hello World!"

    def test_template_with_filters(self):
        """Test template rendering with custom filters."""
        template = "{{ text|title }}"
        context = {"text": "hello world"}
        result = self.helpers.render_template(template, context)
        assert result == "Hello World"

    def test_template_with_dice_modifier_filter(self):
        """Test dice modifier filter."""
        template = "Modifier: {{ value|dice_modifier }}"
        context = {"value": 3}
        result = self.helpers.render_template(template, context)
        assert result == "Modifier: +3"

        context = {"value": -2}
        result = self.helpers.render_template(template, context)
        assert result == "Modifier: -2"

    def test_template_error_handling(self):
        """Test template error handling."""
        template = "{{ undefined_variable }}"
        context = {}

        with pytest.raises(ValueError, match="Template error"):
            self.helpers.render_template(template, context)

    def test_is_template_detection(self):
        """Test template detection."""
        assert self.helpers.is_template("{{ variable }}")
        assert self.helpers.is_template("{% if condition %}text{% endif %}")
        assert self.helpers.is_template("{# comment #}")
        assert not self.helpers.is_template("plain text")
        assert not self.helpers.is_template("text with { single braces }")

    def test_extract_variables(self):
        """Test variable extraction from templates."""
        template = "{{ name }} and {{ age }} and {{ name }}"
        variables = self.helpers.extract_variables(template)
        assert variables == {"name", "age"}

        template = "{{ result.strength }} + {{ bonus }}"
        variables = self.helpers.extract_variables(template)
        assert variables == {"result", "bonus"}

    def test_extract_variables_with_filters(self):
        """Test variable extraction with filters."""
        template = "{{ name|title }} is {{ age|int }}"
        variables = self.helpers.extract_variables(template)
        assert variables == {"name", "age"}

    def test_validate_template(self):
        """Test template validation."""
        # Valid template
        assert self.helpers.validate_template("{{ name }}") is None

        # Invalid template syntax
        error = self.helpers.validate_template("{{ name")
        assert error is not None
        assert "expected token" in error or "unexpected end" in error.lower()


class TestSystemLoaderTemplateHandling:
    """Test template handling in the SystemLoader."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = SystemLoader()

    def create_test_system(self, temp_dir: str) -> Path:
        """Create a minimal test system."""
        system_dir = Path(temp_dir) / "test_system"
        system_dir.mkdir()

        # Create system.yaml
        system_data = {"id": "test_system", "name": "Test System", "version": "1.0.0"}

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_dir / subdir).mkdir()

        return system_dir

    def test_load_time_template_resolution(self):
        """Test that load-time templates are resolved during system loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_system(temp_dir)
            flows_dir = system_dir / "flows"

            # Create flow with load-time templates (should be resolved)
            flow_data = {
                "id": "load_time_flow",
                "name": "Flow for {{ system.name }}",
                "description": "System version: {{ system.version }}",
                "steps": [
                    {
                        "id": "load_step",
                        "name": "Step in {{ system.name }}",
                        "type": "dice_roll",
                        "roll": "1d6",
                    }
                ],
            }

            with open(flows_dir / "load_time_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.loader.load_system(system_dir)
            flow = system.get_flow("load_time_flow")

            # Templates should be resolved
            assert flow.name == "Flow for Test System"
            assert flow.description == "System version: 1.0.0"
            assert flow.steps[0].name == "Step in Test System"

    def test_execution_time_template_preservation(self):
        """Test that execution-time templates are NOT resolved during system loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_system(temp_dir)
            flows_dir = system_dir / "flows"

            # Create flow with execution-time templates (should NOT be resolved)
            flow_data = {
                "id": "execution_time_flow",
                "name": "Execution Flow",
                "description": "A flow with execution-time templates",
                "steps": [
                    {
                        "id": "dice_step",
                        "name": "Roll Dice",
                        "type": "dice_roll",
                        "roll": "1d6",
                        "output": "dice_result",
                    },
                    {
                        "id": "result_step",
                        "name": "Show Result",
                        "type": "completion",
                        "prompt": "You rolled: {{ result }}",
                    },
                    {
                        "id": "choice_step",
                        "name": "Make Choice",
                        "type": "player_choice",
                        "prompt": "Select {{ item }}",
                        "choices": [{"id": "choice1", "label": "{{ selected_item }}"}],
                    },
                    {
                        "id": "variable_step",
                        "name": "Use Variables",
                        "type": "completion",
                        "prompt": "HP: {{ variables.hp }}",
                    },
                    {
                        "id": "llm_step",
                        "name": "LLM Result",
                        "type": "completion",
                        "prompt": "Generated: {{ llm_result }}",
                    },
                    {
                        "id": "get_value_step",
                        "name": "Get Value",
                        "type": "completion",
                        "prompt": "Value: {{ get_value('some.path') }}",
                    },
                ],
            }

            with open(flows_dir / "execution_time_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            # This should load without template errors
            system = self.loader.load_system(system_dir)
            flow = system.get_flow("execution_time_flow")

            # Execution-time templates should be preserved as-is
            assert flow.steps[1].prompt == "You rolled: {{ result }}"
            assert flow.steps[2].prompt == "Select {{ item }}"
            assert flow.steps[2].choices[0].label == "{{ selected_item }}"
            assert flow.steps[3].prompt == "HP: {{ variables.hp }}"
            assert flow.steps[4].prompt == "Generated: {{ llm_result }}"
            assert flow.steps[5].prompt == "Value: {{ get_value('some.path') }}"

    def test_mixed_template_handling(self):
        """Test handling of mixed load-time and execution-time templates."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_system(temp_dir)
            flows_dir = system_dir / "flows"

            # Create flow with mixed templates
            flow_data = {
                "id": "mixed_flow",
                "name": "{{ system.name }} Character Creator",  # Load-time
                "description": "Create character for {{ system.name }}",  # Load-time
                "steps": [
                    {
                        "id": "welcome_step",
                        "name": "Welcome to {{ system.name }}",  # Load-time
                        "type": "completion",
                        "prompt": "Welcome! Your result: {{ result }}",  # Execution-time
                    }
                ],
            }

            with open(flows_dir / "mixed_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            system = self.loader.load_system(system_dir)
            flow = system.get_flow("mixed_flow")

            # Load-time templates should be resolved
            assert flow.name == "Test System Character Creator"
            assert flow.description == "Create character for Test System"
            assert flow.steps[0].name == "Welcome to Test System"

            # Execution-time templates should be preserved
            assert flow.steps[0].prompt == "Welcome! Your result: {{ result }}"

    def test_invalid_template_syntax_handling(self):
        """Test handling of invalid template syntax."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_system(temp_dir)
            flows_dir = system_dir / "flows"

            # Create flow with invalid template syntax
            flow_data = {
                "id": "invalid_template_flow",
                "name": "Invalid Flow",
                "steps": [
                    {
                        "id": "invalid_step",
                        "name": "Invalid Template",
                        "type": "completion",
                        "prompt": "{{ invalid || syntax }}",  # Invalid Jinja2 syntax
                    }
                ],
            }

            with open(flows_dir / "invalid_template_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            # Should load without crashing, preserving invalid template as-is
            system = self.loader.load_system(system_dir)
            flow = system.get_flow("invalid_template_flow")

            # Invalid template should be preserved (not resolved)
            assert flow.steps[0].prompt == "{{ invalid || syntax }}"

    def test_execution_time_variables_comprehensive(self):
        """Test comprehensive list of execution-time variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = self.create_test_system(temp_dir)
            flows_dir = system_dir / "flows"

            # Create flow with all execution-time variables
            execution_vars = [
                "result",
                "results",
                "item",
                "selected_item",
                "selected_items",
                "variables",
                "llm_result",
                "key",
                "value",
            ]

            steps = []
            for i, var in enumerate(execution_vars):
                steps.append(
                    {
                        "id": f"step_{i}",
                        "name": f"Step {i}",
                        "type": "completion",
                        "prompt": f"Variable: {{{{ {var} }}}}",
                    }
                )

            # Add steps with execution-time functions
            steps.append(
                {
                    "id": "get_value_step",
                    "name": "Get Value Step",
                    "type": "completion",
                    "prompt": "{{ get_value('path') }}",
                }
            )

            flow_data = {
                "id": "execution_vars_flow",
                "name": "Execution Variables Test",
                "steps": steps,
            }

            with open(flows_dir / "execution_vars_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)

            # Should load without template resolution errors
            system = self.loader.load_system(system_dir)
            flow = system.get_flow("execution_vars_flow")

            # All execution-time templates should be preserved
            for i, var in enumerate(execution_vars):
                assert flow.steps[i].prompt == f"Variable: {{{{ {var} }}}}"

            assert flow.steps[-1].prompt == "{{ get_value('path') }}"


class TestTemplateIntegration:
    """Test template handling in end-to-end scenarios."""

    def test_real_world_character_creation_templates(self):
        """Test templates similar to those in actual character creation flows."""
        helpers = TemplateHelpers()

        # Test common template patterns that should work
        test_cases = [
            # Basic variable substitution
            (
                "Your strength is {{ strength }}",
                {"strength": 15},
                "Your strength is 15",
            ),
            # With filters
            (
                "{{ name|title }}: {{ value|dice_modifier }}",
                {"name": "strength", "value": 3},
                "Strength: +3",
            ),
            # Complex expressions (that should work)
            ("Defense: {{ value + 10 }}", {"value": 5}, "Defense: 15"),
            # Conditional (should work with proper syntax)
            (
                "{% if bonus > 0 %}+{{ bonus }}{% else %}{{ bonus }}{% endif %}",
                {"bonus": 3},
                "+3",
            ),
        ]

        for template, context, expected in test_cases:
            result = helpers.render_template(template, context)
            assert result == expected, (
                f"Template: {template}, Expected: {expected}, Got: {result}"
            )

    def test_problematic_template_patterns(self):
        """Test template patterns that might cause issues."""
        helpers = TemplateHelpers()

        # These should fail gracefully
        problematic_templates = [
            "{{ undefined_var }}",  # Undefined variable
            "{{ value || 'default' }}",  # JavaScript syntax in Jinja2
            "{{ malformed",  # Incomplete template
        ]

        for template in problematic_templates:
            with pytest.raises(ValueError):
                helpers.render_template(template, {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
