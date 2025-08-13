"""Test log message formatting consistency."""

from grimoire_runner.executors.action_strategies import LogMessageActionStrategy
from grimoire_runner.models.context_data import ExecutionContext


class TestLogMessageFormatting:
    """Test cases for log message action formatting consistency."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = LogMessageActionStrategy()
        self.context = ExecutionContext()

        # Set up some test data in context
        self.context.set_variable("saving_throw_ability", "dexterity")
        self.context.set_variable("saving_throw_type", "basic")

        # Mock LLM result data by setting it as a variable (how it would be in actual execution)
        self.context.set_variable(
            "llm_result",
            {
                "ability": "dexterity",
                "reason": "Dexterity is needed for quick reactions and balance to avoid falling debris.",
                "type": "basic",
            },
        )

    def test_multiple_log_messages_consistent_formatting(self):
        """Test that multiple log_message actions format consistently as plain text."""
        # Execute first log message action
        action1_data = {
            "message": "Saving Throw Ability: {{ variables.saving_throw_ability }}"
        }

        self.strategy.execute(action1_data, self.context)

        # Execute second log message action
        action2_data = {"message": "Justification: {{ variables.llm_result.reason }}"}

        self.strategy.execute(action2_data, self.context)

        # Get the action messages that were added
        action_messages = self.context.get_and_clear_action_messages()

        # Should have two messages
        assert len(action_messages) == 2

        # Both messages should be formatted as plain text with 📝 emoji
        expected_message1 = "📝 Saving Throw Ability: dexterity"
        expected_message2 = "📝 Justification: Dexterity is needed for quick reactions and balance to avoid falling debris."

        assert action_messages[0] == expected_message1
        assert action_messages[1] == expected_message2

        # Neither message should contain dictionary-like formatting
        for message in action_messages:
            assert not message.startswith("📝 {")
            assert not message.endswith("}")
            assert "': '" not in message

    def test_log_message_with_colon_not_parsed_as_yaml(self):
        """Test that log messages with colons are not parsed as YAML structures."""
        # Test various messages that contain colons but should remain as plain text
        test_cases = [
            (
                "Saving Throw Ability: {{ variables.saving_throw_ability }}",
                "📝 Saving Throw Ability: dexterity",
            ),
            (
                "Saving Throw Type: {{ variables.saving_throw_type }}",
                "📝 Saving Throw Type: basic",
            ),
            ("Roll Result: Success", "📝 Roll Result: Success"),
            ("Damage Type: fire", "📝 Damage Type: fire"),
            ("Dice Roll: 1d20+2", "📝 Dice Roll: 1d20+2"),
        ]

        for input_message, expected_output in test_cases:
            # Clear any previous messages
            self.context.get_and_clear_action_messages()

            action_data = {"message": input_message}
            self.strategy.execute(action_data, self.context)

            messages = self.context.get_and_clear_action_messages()
            assert len(messages) == 1
            assert messages[0] == expected_output

    def test_log_message_template_resolution_preserves_text_format(self):
        """Test that template resolution in log messages preserves text format."""
        # Set up more complex template data
        self.context.set_variable("character_name", "Thorgar")
        self.context.set_variable("spell_name", "Magic Missile")

        test_cases = [
            {
                "message": "Character Name: {{ variables.character_name }}",
                "expected": "📝 Character Name: Thorgar",
            },
            {
                "message": "Casting Spell: {{ variables.spell_name }}",
                "expected": "📝 Casting Spell: Magic Missile",
            },
            {
                "message": "Action: {{ variables.character_name }} casts {{ variables.spell_name }}",
                "expected": "📝 Action: Thorgar casts Magic Missile",
            },
        ]

        for test_case in test_cases:
            # Clear previous messages
            self.context.get_and_clear_action_messages()

            action_data = {"message": test_case["message"]}
            self.strategy.execute(action_data, self.context)

            messages = self.context.get_and_clear_action_messages()
            assert len(messages) == 1
            assert messages[0] == test_case["expected"]

    def test_log_message_does_not_parse_gaming_terms_as_yaml(self):
        """Test that gaming-specific terms in log messages don't get parsed as YAML."""
        # These should all be treated as plain text, not parsed as structured data
        gaming_messages = [
            "Ability Score: Strength",
            "Saving Throw: Constitution",
            "Dice Roll: 2d6+3",
            "Damage Roll: 1d8+2",
            "Initiative Roll: 1d20+1",
            "Attack Roll: Natural 20",
            "Spell Level: 3rd level",
            "Armor Class: 18",
        ]

        for message in gaming_messages:
            # Clear previous messages
            self.context.get_and_clear_action_messages()

            action_data = {"message": message}
            self.strategy.execute(action_data, self.context)

            messages = self.context.get_and_clear_action_messages()
            assert len(messages) == 1

            # Should be plain text with emoji prefix
            expected = f"📝 {message}"
            assert messages[0] == expected

            # Should not be parsed as a dictionary
            assert not messages[0].startswith("📝 {")
