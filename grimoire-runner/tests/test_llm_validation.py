"""Tests for LLM validation functionality."""

import sys
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.append("src")

from grimoire_runner.executors.llm_executor import LLMExecutor
from grimoire_runner.integrations.llm_integration import LLMIntegration
from grimoire_runner.models.step import LLMValidationDefinition


def create_mock_json_response(prompt_template, context, **kwargs):
    """Create a mock JSON response for testing validation."""
    if "JSON" in prompt_template or "json" in prompt_template:
        # Return a valid JSON response for most cases
        return '{"ability": "dexterity", "reason": "dodging the falling boulder"}'
    else:
        # Return a mixed text response that needs JSON extraction
        return """Based on the action, the appropriate saving throw would be:

```json
{"ability": "dexterity", "reason": "dodging requires quick reflexes"}
```

This makes sense because dodging falling objects primarily requires agility."""


def create_mock_invalid_json_response(prompt_template, context, **kwargs):
    """Create a mock invalid JSON response for testing cleanup."""
    if "valid JSON object" in prompt_template or "corrected JSON" in prompt_template:
        # Cleanup call - return valid JSON
        return '{"ability": "strength", "reason": "lifting heavy objects"}'
    else:
        # Initial call - return invalid JSON
        return 'This is not valid JSON: {ability: "strength" reason: missing comma}'


class TestLLMValidation:
    """Test LLM validation functionality."""

    @patch.object(
        LLMIntegration, "generate_content", side_effect=create_mock_json_response
    )
    def test_json_validation_success(self, mock_generate):
        """Test successful JSON validation."""
        executor = LLMExecutor()

        # Create a step with JSON validation
        step = MagicMock()
        step.validation = LLMValidationDefinition(type="json")
        step.prompt = "Generate JSON for a saving throw"
        step.prompt_data = {"action": "dodge boulder"}
        step.llm_settings = MagicMock()
        step.llm_settings.__dict__ = {}

        # Test the validation method directly
        result_json, success, attempts, raw_response, errors = (
            executor._attempt_llm_call_with_validation(
                "Generate JSON response", {}, step.validation, {}
            )
        )

        assert success is True
        assert attempts == 1
        assert "ability" in result_json
        assert "reason" in result_json
        assert result_json["ability"] == "dexterity"
        assert len(errors) == 0

    @patch.object(
        LLMIntegration,
        "generate_content",
        side_effect=create_mock_invalid_json_response,
    )
    def test_json_validation_with_cleanup(self, mock_generate):
        """Test JSON validation with automatic cleanup."""
        executor = LLMExecutor()

        # Create a step with JSON validation
        step = MagicMock()
        step.validation = LLMValidationDefinition(type="json")

        # Test the validation method
        result_json, success, attempts, raw_response, errors = (
            executor._attempt_llm_call_with_validation(
                "Generate JSON response", {}, step.validation, {}
            )
        )

        # Should succeed after cleanup
        assert success is True
        assert attempts >= 1
        assert "ability" in result_json
        assert "reason" in result_json

        # Verify cleanup was called
        assert mock_generate.call_count >= 2  # Initial call + cleanup call

    def test_json_schema_validation_success(self):
        """Test successful JSON schema validation."""
        executor = LLMExecutor()

        # Test data that matches schema
        test_data = {"ability": "dexterity", "reason": "quick reflexes needed"}
        schema = {
            "type": "object",
            "properties": {
                "ability": {
                    "type": "string",
                    "enum": [
                        "strength",
                        "dexterity",
                        "constitution",
                        "intelligence",
                        "wisdom",
                        "charisma",
                    ],
                },
                "reason": {"type": "string", "minLength": 10},
            },
            "required": ["ability", "reason"],
        }

        is_valid, errors = executor._validate_json_schema(test_data, schema)

        assert is_valid is True
        assert len(errors) == 0

    def test_json_schema_validation_failure(self):
        """Test JSON schema validation failure."""
        executor = LLMExecutor()

        # Test data that doesn't match schema
        test_data = {"ability": "invalid_ability", "reason": "short"}
        schema = {
            "type": "object",
            "properties": {
                "ability": {
                    "type": "string",
                    "enum": [
                        "strength",
                        "dexterity",
                        "constitution",
                        "intelligence",
                        "wisdom",
                        "charisma",
                    ],
                },
                "reason": {"type": "string", "minLength": 10},
            },
            "required": ["ability", "reason"],
        }

        is_valid, errors = executor._validate_json_schema(test_data, schema)

        assert is_valid is False
        assert len(errors) > 0

    def test_json_extraction_from_markdown(self):
        """Test JSON extraction from markdown code blocks."""
        executor = LLMExecutor()

        response = """Here's the result:

```json
{"ability": "wisdom", "reason": "resisting mental influence"}
```

This should work for wisdom saving throws."""

        json_data, success = executor._extract_json_from_response(response)

        assert success is True
        assert json_data["ability"] == "wisdom"
        assert json_data["reason"] == "resisting mental influence"

    def test_json_extraction_from_mixed_text(self):
        """Test JSON extraction from mixed text."""
        executor = LLMExecutor()

        response = 'The saving throw should use {"ability": "constitution", "reason": "enduring physical stress"} based on the action.'

        json_data, success = executor._extract_json_from_response(response)

        assert success is True
        assert json_data["ability"] == "constitution"
        assert json_data["reason"] == "enduring physical stress"

    def test_json_extraction_failure(self):
        """Test JSON extraction failure."""
        executor = LLMExecutor()

        response = "This is just plain text with no JSON whatsoever."

        json_data, success = executor._extract_json_from_response(response)

        assert success is False
        assert json_data == {}
