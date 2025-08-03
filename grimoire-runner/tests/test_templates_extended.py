"""
Additional tests for template handling utilities.
"""

import sys
from pathlib import Path

import pytest
from jinja2 import TemplateError

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.utils.templates import StringTemplateLoader, TemplateHelpers


class TestStringTemplateLoaderExtended:
    """Extended tests for StringTemplateLoader."""

    def setup_method(self):
        """Set up test fixtures."""
        self.loader = StringTemplateLoader()

    def test_loader_initialization(self):
        """Test loader initialization."""
        loader = StringTemplateLoader()
        assert loader.templates == {}

    def test_add_template(self):
        """Test adding a template."""
        self.loader.add_template("test", "Hello {{name}}!")
        assert "test" in self.loader.templates
        assert self.loader.templates["test"] == "Hello {{name}}!"

    def test_get_source_existing_template(self):
        """Test getting source for existing template."""
        from jinja2 import Environment
        env = Environment(loader=self.loader)

        self.loader.add_template("greeting", "Hello {{name}}!")

        source, name, uptodate = self.loader.get_source(env, "greeting")
        assert source == "Hello {{name}}!"
        assert name is None
        assert uptodate() is True

    def test_get_source_nonexistent_template(self):
        """Test getting source for non-existent template."""
        from jinja2 import Environment
        env = Environment(loader=self.loader)

        with pytest.raises(TemplateError, match="Template 'nonexistent' not found"):
            self.loader.get_source(env, "nonexistent")


class TestTemplateHelpersExtended:
    """Extended tests for TemplateHelpers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.helpers = TemplateHelpers()

    def test_helpers_initialization(self):
        """Test helpers initialization."""
        helpers = TemplateHelpers()
        assert helpers.loader is not None
        assert helpers.env is not None

    def test_custom_filters_title_case(self):
        """Test title_case custom filter."""
        template_str = "{{ text | title_case }}"
        template = self.helpers.env.from_string(template_str)

        result = template.render(text="hello world")
        assert result == "Hello World"

        result = template.render(text="UPPERCASE TEXT")
        assert result == "Uppercase Text"

    def test_custom_filters_snake_case(self):
        """Test snake_case custom filter."""
        template_str = "{{ text | snake_case }}"
        template = self.helpers.env.from_string(template_str)

        result = template.render(text="Hello World")
        assert result == "hello_world"

        result = template.render(text="Special-Characters!@#")
        assert result == "special_characters___"

    def test_dice_modifier_filter(self):
        """Test dice_modifier filter functionality."""
        # Test if dice_modifier filter exists and works
        template_str = "{{ value | dice_modifier }}"
        template = self.helpers.env.from_string(template_str)

        # Positive modifier
        result = template.render(value=3)
        assert result == "+3"

        # Negative modifier
        result = template.render(value=-2)
        assert result == "-2"

        # Zero modifier
        result = template.render(value=0)
        assert result == "+0"

    def test_render_template_success(self):
        """Test successful template rendering."""
        template_str = "Hello {{name}}, you have {{count}} items."
        context = {"name": "Alice", "count": 5}

        result = self.helpers.render_template(template_str, context)
        assert result == "Hello Alice, you have 5 items."

    def test_render_template_with_filters(self):
        """Test template rendering with custom filters."""
        template_str = "{{ name | title_case }} has {{ item_name | snake_case }}"
        context = {"name": "john doe", "item_name": "Magic Sword"}

        result = self.helpers.render_template(template_str, context)
        assert result == "John Doe has magic_sword"

    def test_render_template_undefined_variable(self):
        """Test template rendering with undefined variable."""
        template_str = "Hello {{name}}, you have {{undefined_var}} items."
        context = {"name": "Alice"}

        with pytest.raises(ValueError, match="Template error"):
            self.helpers.render_template(template_str, context)

    def test_render_template_empty_context(self):
        """Test template rendering with empty context."""
        template_str = "Static text without variables"
        context = {}

        result = self.helpers.render_template(template_str, context)
        assert result == "Static text without variables"

    def test_render_template_complex_data(self):
        """Test template rendering with complex data structures."""
        template_str = "{{character.name}} (Level {{character.level}}) has {{len(character.inventory)}} items"
        context = {
            "character": {
                "name": "Gandalf",
                "level": 20,
                "inventory": ["Staff", "Ring", "Robe"]
            }
        }

        result = self.helpers.render_template(template_str, context)
        assert result == "Gandalf (Level 20) has 3 items"

    def test_is_template_true_cases(self):
        """Test template detection for strings that are templates."""
        assert self.helpers.is_template("Hello {{name}}")
        assert self.helpers.is_template("{{ variable }}")
        assert self.helpers.is_template("Text with {{multiple}} {{variables}}")
        assert self.helpers.is_template("{% if condition %}conditional{% endif %}")
        assert self.helpers.is_template("{{ value | filter }}")

    def test_is_template_false_cases(self):
        """Test template detection for strings that are not templates."""
        assert not self.helpers.is_template("Plain text")
        assert not self.helpers.is_template("Text with {single} braces")
        assert not self.helpers.is_template("Text with triple braces but not template")
        assert not self.helpers.is_template("")
        assert not self.helpers.is_template("Just normal text with no template syntax")

    def test_extract_variables_simple(self):
        """Test variable extraction from simple templates."""
        variables = self.helpers.extract_variables("Hello {{name}}")
        assert variables == {"name"}

    def test_extract_variables_multiple(self):
        """Test variable extraction from templates with multiple variables."""
        variables = self.helpers.extract_variables("{{greeting}} {{name}}, you have {{count}} items")
        assert variables == {"greeting", "name", "count"}

    def test_extract_variables_with_filters(self):
        """Test variable extraction from templates with filters."""
        variables = self.helpers.extract_variables("{{ name | title_case }} has {{ item | snake_case }}")
        assert variables == {"name", "item"}

    def test_extract_variables_with_attributes(self):
        """Test variable extraction from templates with attribute access."""
        variables = self.helpers.extract_variables("{{character.name}} is level {{character.level}}")
        assert variables == {"character"}

    def test_extract_variables_no_variables(self):
        """Test variable extraction from templates with no variables."""
        variables = self.helpers.extract_variables("Just plain text")
        assert variables == set()

    def test_extract_variables_complex_expressions(self):
        """Test variable extraction from complex template expressions."""
        template = "{% if user.active %}{{user.name}}{% endif %} has {{items|length}} items"
        variables = self.helpers.extract_variables(template)
        assert variables == {"user", "items"}

    def test_validate_template_valid(self):
        """Test validation of valid templates."""
        assert self.helpers.validate_template("Hello {{name}}") is None
        assert self.helpers.validate_template("{{ value | title_case }}") is None
        assert self.helpers.validate_template("Plain text") is None

    def test_validate_template_invalid_syntax(self):
        """Test validation of templates with invalid syntax."""
        assert self.helpers.validate_template("{{ unclosed variable") is not None
        assert self.helpers.validate_template("{% invalid tag %}") is not None
        assert self.helpers.validate_template("{{ variable | nonexistent_filter }}") is not None

    def test_validate_template_empty(self):
        """Test validation of empty template."""
        assert self.helpers.validate_template("") is None

    def test_environment_configuration(self):
        """Test that Jinja2 environment is properly configured."""
        # Test that trim_blocks and lstrip_blocks are enabled
        template_str = """
        {% if true %}
            Hello World
        {% endif %}
        """
        result = self.helpers.render_template(template_str, {})
        # Should be trimmed due to configuration
        assert result.strip() == "Hello World"

    def test_strict_undefined_behavior(self):
        """Test that StrictUndefined is properly configured."""
        template_str = "Hello {{undefined_variable}}"

        with pytest.raises(ValueError, match="Template error"):
            self.helpers.render_template(template_str, {})


class TestTemplateHelpersIntegration:
    """Integration tests for template helpers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.helpers = TemplateHelpers()

    def test_template_with_all_features(self):
        """Test template using all custom features."""
        template_str = """
        Character: {{ character.name | title_case }}
        Class: {{ character.class | snake_case }}
        Modifier: {{ character.strength_mod | dice_modifier }}
        """

        context = {
            "character": {
                "name": "aragorn son of arathorn",
                "class": "Ranger-Scout",
                "strength_mod": 4
            }
        }

        result = self.helpers.render_template(template_str, context)

        assert "Aragorn Son Of Arathorn" in result
        assert "ranger_scout" in result
        assert "+4" in result

    def test_error_handling_in_complex_template(self):
        """Test error handling in complex templates."""
        template_str = "{{ character.stats.strength | dice_modifier }}"
        context = {"character": {"name": "Test"}}  # Missing stats

        with pytest.raises(ValueError, match="Template error"):
            self.helpers.render_template(template_str, context)

    def test_template_performance_with_large_context(self):
        """Test template performance with large context."""
        # Create a large context
        large_context = {
            "items": [f"item_{i}" for i in range(1000)],
            "character": {"name": "Test", "level": 10}
        }

        template_str = "{{ character.name }} has {{ items|length }} items"

        result = self.helpers.render_template(template_str, large_context)
        assert result == "Test has 1000 items"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
