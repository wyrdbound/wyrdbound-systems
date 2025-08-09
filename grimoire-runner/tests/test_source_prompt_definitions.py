"""
Test source and prompt definition functionality.

This tests:
- Source definition loading and validation
- Prompt definition loading and validation
- Template parsing and structure validation
- Integration with system components
- LLM configuration parsing

This is Phase 1.5 of the testing strategy.
"""

from pathlib import Path

import pytest

from grimoire_runner.core.loader import SystemLoader


@pytest.fixture
def test_systems_dir():
    """Directory containing test systems."""
    return Path(__file__).parent / "systems"


class TestBasicSourceLoading:
    """Test basic source definition loading and validation."""

    def test_load_system_with_sources(self, test_systems_dir):
        """Test that systems with sources load correctly."""
        loader = SystemLoader()
        source_path = test_systems_dir / "source_test"

        system = loader.load_system(source_path)

        # Verify system loads correctly
        assert system is not None
        assert system.id == "source_test"

        # Verify sources are loaded
        assert len(system.sources) > 0

        # Check specific source exists
        assert "test_source" in system.sources

    def test_basic_source_structure(self, test_systems_dir):
        """Test basic source definition structure."""
        loader = SystemLoader()
        source_path = test_systems_dir / "source_test"

        system = loader.load_system(source_path)
        source = system.sources["test_source"]

        # Verify required fields
        assert source.id == "test_source"
        assert source.kind == "source"
        assert source.name == "Test Source"

        # Verify optional fields are handled correctly
        assert hasattr(source, "description")
        assert hasattr(source, "publisher")
        assert hasattr(source, "source_url")

    def test_source_validation_methods(self, test_systems_dir):
        """Test source validation functionality."""
        loader = SystemLoader()
        source_path = test_systems_dir / "source_test"

        system = loader.load_system(source_path)
        source = system.sources["test_source"]

        # Test validation passes for valid source
        errors = source.validate()
        assert len(errors) == 0


class TestBasicPromptLoading:
    """Test basic prompt definition loading and validation."""

    def test_load_system_with_prompts(self, test_systems_dir):
        """Test that systems with prompts load correctly."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)

        # Verify system loads correctly
        assert system is not None
        assert system.id == "prompt_test"

        # Verify prompts are loaded
        assert hasattr(system, "prompts")
        assert len(system.prompts) > 0

        # Check specific prompt exists
        assert "test_prompt" in system.prompts

    def test_basic_prompt_structure(self, test_systems_dir):
        """Test basic prompt definition structure."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)
        prompt = system.prompts["test_prompt"]

        # Verify required fields
        assert prompt.id == "test_prompt"
        assert prompt.kind == "prompt"
        assert prompt.name == "Test Prompt"
        assert prompt.prompt_template is not None

        # Verify optional fields are handled correctly
        assert hasattr(prompt, "description")
        assert hasattr(prompt, "llm")
        assert hasattr(prompt, "version")

    def test_prompt_template_content(self, test_systems_dir):
        """Test prompt template content structure."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)
        prompt = system.prompts["test_prompt"]

        # Verify template contains expected variable patterns
        template = prompt.prompt_template
        assert "{{" in template and "}}" in template  # Has variable substitution
        assert "name" in template  # Contains expected variable

    def test_llm_configuration_parsing(self, test_systems_dir):
        """Test LLM configuration parsing in prompts."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)
        prompt = system.prompts["test_prompt"]

        # Verify LLM configuration is parsed
        assert prompt.llm is not None
        assert hasattr(prompt.llm, "provider")
        assert hasattr(prompt.llm, "model")


class TestPromptValidation:
    """Test prompt validation and error handling."""

    def test_prompt_validation_method(self, test_systems_dir):
        """Test prompt validation functionality."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)
        prompt = system.prompts["test_prompt"]

        # Test validation passes for valid prompt
        errors = prompt.validate()
        assert len(errors) == 0

    def test_prompt_template_validation(self, test_systems_dir):
        """Test prompt template validation."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)
        prompt = system.prompts["test_prompt"]

        # Template should be non-empty
        assert len(prompt.prompt_template.strip()) > 0


class TestSourcePromptIntegration:
    """Test integration between sources and prompts."""

    def test_load_integrated_system(self, test_systems_dir):
        """Test system loading with both sources and prompts."""
        loader = SystemLoader()
        integration_path = test_systems_dir / "source_prompt_integration"

        system = loader.load_system(integration_path)

        # Verify both sources and prompts are loaded
        assert len(system.sources) > 0
        assert len(system.prompts) > 0

        # Check cross-references work
        assert "integration_source" in system.sources
        assert "integration_prompt" in system.prompts

    def test_system_get_methods(self, test_systems_dir):
        """Test system methods for retrieving sources and prompts."""
        loader = SystemLoader()
        integration_path = test_systems_dir / "source_prompt_integration"

        system = loader.load_system(integration_path)

        # Test source retrieval
        source = system.get_source("integration_source")
        assert source is not None
        assert source.name == "Integration Test Source"

        # Test prompt retrieval
        prompt = system.get_prompt("integration_prompt")
        assert prompt is not None
        assert prompt.name == "Integration Test Prompt"


class TestSourcePromptErrorHandling:
    """Test error handling for malformed sources and prompts."""

    def test_invalid_source_kind(self):
        """Test validation fails for sources with wrong kind."""
        from grimoire_runner.models.source import SourceDefinition

        # Create source with invalid kind
        invalid_source = SourceDefinition(
            id="invalid",
            kind="invalid_kind",  # Should be "source"
            name="Invalid Source",
        )

        errors = invalid_source.validate()
        assert len(errors) > 0
        assert any("kind" in error for error in errors)

    def test_missing_source_name(self):
        """Test validation fails for sources without name."""
        from grimoire_runner.models.source import SourceDefinition

        # Create source without name
        invalid_source = SourceDefinition(
            id="test",
            kind="source",
            name="",  # Required field
        )

        errors = invalid_source.validate()
        assert len(errors) > 0
        assert any("name" in error for error in errors)


class TestPromptTemplateFeatures:
    """Test advanced prompt template features."""

    def test_complex_template_variables(self, test_systems_dir):
        """Test prompts with complex variable structures."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)

        # Check for prompt with complex variables
        if "complex_prompt" in system.prompts:
            prompt = system.prompts["complex_prompt"]
            template = prompt.prompt_template

            # Should contain nested variable access
            assert "character.name" in template or "{{ " in template

    def test_llm_configuration_completeness(self, test_systems_dir):
        """Test comprehensive LLM configuration options."""
        loader = SystemLoader()
        prompt_path = test_systems_dir / "prompt_test"

        system = loader.load_system(prompt_path)

        # Find prompt with complete LLM config
        for prompt in system.prompts.values():
            if prompt.llm:
                # Check all expected LLM fields are accessible
                assert hasattr(prompt.llm, "provider")
                assert hasattr(prompt.llm, "model")
                # Optional fields should be accessible even if None
                assert hasattr(prompt.llm, "temperature")
                assert hasattr(prompt.llm, "max_tokens")
                break


class TestSourcePromptUtilities:
    """Test utility functions for creating sources and prompts."""

    def test_create_simple_source(self):
        """Test creating a simple source definition."""
        from grimoire_runner.models.source import SourceDefinition

        source = SourceDefinition(
            id="test_source",
            kind="source",
            name="Test Source",
            description="A test source for validation",
            publisher="Test Publisher",
        )

        assert source.id == "test_source"
        assert source.kind == "source"
        assert source.name == "Test Source"
        assert len(source.validate()) == 0

    def test_create_simple_prompt(self):
        """Test creating a simple prompt definition."""
        from grimoire_runner.models.prompt import LLMConfig, PromptDefinition

        llm_config = LLMConfig(
            provider="ollama", model="gemma2", temperature=0.7, max_tokens=150
        )

        prompt = PromptDefinition(
            id="test_prompt",
            kind="prompt",
            name="Test Prompt",
            description="A test prompt for validation",
            prompt_template="Generate content for {{ item_name }}",
            llm=llm_config,
        )

        assert prompt.id == "test_prompt"
        assert prompt.kind == "prompt"
        assert prompt.name == "Test Prompt"
        assert "{{ item_name }}" in prompt.prompt_template
        assert len(prompt.validate()) == 0
