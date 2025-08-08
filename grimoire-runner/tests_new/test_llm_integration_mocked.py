"""Tests for LLM integration functionality using mocks."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.append("src")

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.integrations.llm_integration import LLMIntegration


def create_mock_llm_response(prompt_template, context, **kwargs):
    """Create a realistic mock response for testing LLM integration."""
    character_name = context.get("character_name", "TestCharacter")
    character_class = context.get("character_class", "Fighter")

    return f"""Here is a character description:

Name: {character_name}
Class: {character_class}

{character_name} is a seasoned {character_class.lower()} with weathered hands and keen eyes. They carry themselves with the confidence of someone who has faced danger and emerged stronger. Their equipment is well-maintained but shows signs of use, speaking to practical experience rather than mere showmanship.

Personality-wise, {character_name} tends to be cautious but decisive when action is required."""


class TestLLMIntegrationMocked:
    """Test LLM integration functionality with mocked responses."""

    @patch.object(
        LLMIntegration, "generate_content", side_effect=create_mock_llm_response
    )
    def test_llm_integration_direct(self, mock_generate):
        """Test LLM integration directly with mocked calls."""
        integration = LLMIntegration()

        # Test basic generation
        prompt = "Create a character description"
        context = {"character_class": "Fighter", "character_name": "TestCharacter"}

        result = integration.generate_content(prompt, context)

        # Verify mock was called correctly
        mock_generate.assert_called_once_with(prompt, context)

        # Verify response content
        assert "TestCharacter" in result
        assert "Fighter" in result
        assert "character description" in result
        assert len(result) > 50  # Should be substantial content

    @patch.object(
        LLMIntegration, "generate_content", side_effect=create_mock_llm_response
    )
    def test_llm_flow_execution_mocked(self, mock_generate):
        """Test complete LLM flow execution with mocked LLM calls."""
        # Create engine and load test system
        engine = GrimoireEngine()
        system_path = Path(__file__).parent / "systems" / "flow_test"
        engine.load_system(system_path)

        # Create execution context
        context = engine.create_execution_context(
            inputs={"character": {"name": "TestCharacter", "class": "Fighter"}}
        )

        # Execute the LLM flow
        result = engine.execute_flow("llm-flow", context)

        # Verify mock was called
        mock_generate.assert_called_once()

        # Check the arguments passed to the mock using kwargs
        call_kwargs = mock_generate.call_args[1]

        assert (
            call_kwargs["prompt_template"]
            == "Create a character description for {{ character_name }}, a {{ character_class }}. Include their appearance, personality, and background."
        )
        assert call_kwargs["context"]["character_name"] == "TestCharacter"
        assert call_kwargs["context"]["character_class"] == "Fighter"
        assert call_kwargs["provider"] == "ollama"  # Should default to ollama now
        assert call_kwargs["model"] == "gemma2"

        # Verify flow execution results
        assert hasattr(result, "outputs")
        assert "character_with_description" in result.outputs

        character_data = result.outputs["character_with_description"]
        assert "description" in character_data

        description = character_data["description"]
        assert "TestCharacter" in description
        assert "Fighter" in description
        assert len(description) > 100

    @patch.object(LLMIntegration, "generate_content")
    def test_llm_template_resolution(self, mock_generate):
        """Test that template resolution works correctly for LLM prompts."""
        mock_generate.return_value = "Mock LLM Response"

        # Create engine and load test system
        engine = GrimoireEngine()
        system_path = Path(__file__).parent / "systems" / "flow_test"
        engine.load_system(system_path)

        # Create execution context with specific test data
        test_name = "Aragorn"
        test_class = "Ranger"
        context = engine.create_execution_context(
            inputs={"character": {"name": test_name, "class": test_class}}
        )

        # Execute the LLM flow
        engine.execute_flow("llm-flow", context)

        # Verify the mock was called with correctly resolved template values
        mock_generate.assert_called_once()

        # Check the arguments using kwargs
        call_kwargs = mock_generate.call_args[1]
        prompt_context = call_kwargs["context"]

        # The context should have resolved templates {{ inputs.character.name }} -> test_name
        assert prompt_context["character_name"] == test_name
        assert prompt_context["character_class"] == test_class

    def test_template_syntax_validation(self):
        """Test that the simplified template syntax {{ inputs.character.name }} works."""
        # Load the LLM flow and check its template syntax
        engine = GrimoireEngine()
        system_path = Path(__file__).parent / "systems" / "flow_test"
        system = engine.load_system(system_path)

        llm_flow = system.flows["llm-flow"]
        generate_step = llm_flow.get_step("generate-description")

        # Verify the templates use the simplified syntax
        assert (
            generate_step.prompt_data["character_name"] == "{{ inputs.character.name }}"
        )
        assert (
            generate_step.prompt_data["character_class"]
            == "{{ inputs.character.class }}"
        )

        # These should NOT use the old get_value() syntax
        assert "get_value(" not in generate_step.prompt_data["character_name"]
        assert "get_value(" not in generate_step.prompt_data["character_class"]


class TestLLMErrorHandling:
    """Test LLM error handling and explicit failure behavior."""

    @patch("grimoire_runner.integrations.llm_integration.OLLAMA_AVAILABLE", False)
    @patch("grimoire_runner.integrations.llm_integration.ANTHROPIC_AVAILABLE", False)
    @patch("grimoire_runner.integrations.llm_integration.OPENAI_AVAILABLE", False)
    def test_llm_integration_fails_explicitly_when_dependencies_unavailable(self):
        """Test that LLM integration fails explicitly when dependencies are unavailable."""
        with pytest.raises(
            ImportError,
            match="Ollama integration requested but langchain-community is not installed",
        ):
            LLMIntegration(provider="ollama")

    @patch(
        "grimoire_runner.integrations.llm_integration.LLMIntegration._setup_langchain"
    )
    def test_llm_integration_fails_explicitly_on_setup_error(self, mock_setup):
        """Test that LLM integration fails explicitly when setup fails."""
        mock_setup.side_effect = Exception("Setup failed")

        with pytest.raises(
            RuntimeError, match="Failed to initialize LLM integration: Setup failed"
        ):
            LLMIntegration()

    def test_llm_flow_execution_with_mocked_integration(self):
        """Test that LLM flows work correctly with mocked integration."""
        # Mock all LLM calls to avoid hitting actual services
        with patch.object(LLMIntegration, "generate_content") as mock_generate:
            mock_generate.return_value = (
                "A brave Fighter named TestCharacter stands ready for adventure."
            )

            engine = GrimoireEngine()
            system_path = Path(__file__).parent / "systems" / "flow_test"
            engine.load_system(system_path)

            context = engine.create_execution_context(
                inputs={"character": {"name": "TestCharacter", "class": "Fighter"}}
            )

            # Flow should complete with mocked content
            result = engine.execute_flow("llm-flow", context)
            assert result is not None

            # Verify the mock was called with expected parameters
            mock_generate.assert_called_once()

            # Should have output with mocked description
            assert "character_with_description" in result.outputs
            assert "description" in result.outputs["character_with_description"]
