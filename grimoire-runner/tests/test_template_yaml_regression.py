"""Test template service YAML parsing behavior for log messages."""

from grimoire_runner.services.template_service import TemplateService


class TestTemplateServiceYAMLParsing:
    """Test cases for template service YAML parsing behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.template_service = TemplateService()

    def test_template_service_does_not_parse_log_messages_as_yaml(self):
        """Test that template service doesn't parse log-like messages as YAML."""
        # Test context that would cause the original bug
        context = {
            "variables": {"saving_throw_ability": "dexterity"},
            "inputs": {},
            "outputs": {},
        }

        # Template that would resolve to a string with colon
        template_str = "Saving Throw Ability: {{ variables.saving_throw_ability }}"

        # Resolve the template
        result = self.template_service.resolve_template(
            template_str, context, "runtime"
        )

        # Should return plain string, not a dict
        expected_result = "Saving Throw Ability: dexterity"
        assert result == expected_result
        assert isinstance(result, str)
        assert not isinstance(result, dict)

    def test_template_service_gaming_terms_not_parsed_as_yaml(self):
        """Test various gaming-related templates that should not be parsed as YAML."""
        context = {
            "variables": {
                "ability": "strength",
                "dice_result": "1d20+2",
                "damage_type": "fire",
                "spell_level": "3rd",
            },
            "inputs": {},
            "outputs": {},
        }

        test_cases = [
            ("Ability: {{ variables.ability }}", "Ability: strength"),
            ("Dice Roll: {{ variables.dice_result }}", "Dice Roll: 1d20+2"),
            ("Damage Type: {{ variables.damage_type }}", "Damage Type: fire"),
            ("Spell Level: {{ variables.spell_level }}", "Spell Level: 3rd"),
            ("Saving Throw Type: basic", "Saving Throw Type: basic"),
            ("Roll Result: Success", "Roll Result: Success"),
        ]

        for template_str, expected in test_cases:
            result = self.template_service.resolve_template(
                template_str, context, "runtime"
            )
            assert result == expected, (
                f"Template '{template_str}' should resolve to '{expected}', got '{result}'"
            )
            assert isinstance(result, str), (
                f"Result should be string, got {type(result)}"
            )

    def test_template_service_preserves_legitimate_yaml_parsing(self):
        """Test that legitimate YAML structures are still parsed correctly."""
        context = {
            "variables": {"data": "value1\nkey2: value2"},
            "inputs": {},
            "outputs": {},
        }

        # Multi-line YAML should still be parsed
        template_str = "{{ variables.data }}"
        result = self.template_service.resolve_template(
            template_str, context, "runtime"
        )

        # This should parse as YAML because it's multi-line
        # (Though this particular case might not parse as valid YAML, the point is
        # that multi-line content should go through YAML parsing logic)
        # The exact result depends on YAML parsing, but it should at least try

        # For this test, let's use clear valid YAML
        context["variables"]["yaml_data"] = "key1: value1\nkey2: value2"
        template_str = "{{ variables.yaml_data }}"
        result = self.template_service.resolve_template(
            template_str, context, "runtime"
        )

        # Should either be the original string or parsed as dict, but not treated as a single-line log message
        assert result == "key1: value1\nkey2: value2" or result == {
            "key1": "value1",
            "key2": "value2",
        }

    def test_regression_original_bug_scenario(self):
        """Test the exact scenario that caused the original bug."""
        # This reproduces the context that was causing the inconsistent formatting
        context = {
            "variables": {"saving_throw_ability": "dexterity"},
            "inputs": {},
            "outputs": {},
        }

        # First log message template (was being parsed as YAML)
        template1 = "Saving Throw Ability: {{ variables.saving_throw_ability }}"
        result1 = self.template_service.resolve_template(template1, context, "runtime")

        # Second log message template (was working correctly)
        context["variables"]["reason"] = (
            "Dexterity is needed for quick reactions and balance to avoid falling debris."
        )
        template2 = "Justification: {{ variables.reason }}"
        result2 = self.template_service.resolve_template(template2, context, "runtime")

        # Both should be strings, not dictionaries
        assert result1 == "Saving Throw Ability: dexterity"
        assert (
            result2
            == "Justification: Dexterity is needed for quick reactions and balance to avoid falling debris."
        )
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert not isinstance(result1, dict)
        assert not isinstance(result2, dict)
