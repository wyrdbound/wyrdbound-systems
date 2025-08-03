"""
Tests for RNG integration functionality.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.integrations.rng_integration import RNGIntegration


class TestRNGIntegrationWithoutPackage:
    """Test RNG integration when wyrdbound-rng package is not available."""

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_initialization_without_package(self):
        """Test RNG integration initialization when package is not available."""
        rng = RNGIntegration()

        assert not rng.is_available()
        assert rng.generators == {}

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_load_generator_without_package(self):
        """Test loading generator when package is not available."""
        rng = RNGIntegration()

        result = rng.load_name_generator("/fake/path.json")
        assert result is None

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_generate_name_fallback(self):
        """Test name generation using fallback when package is not available."""
        rng = RNGIntegration()

        # Test basic fallback name generation
        name = rng.generate_name("test_generator")
        assert isinstance(name, str)
        assert " " in name  # Should be "FirstName LastName" format

        # Test multiple generations to ensure randomness works
        names = {rng.generate_name("test_generator") for _ in range(20)}
        assert len(names) > 1  # Should generate different names

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_generate_name_with_kwargs(self):
        """Test name generation with keyword arguments in fallback mode."""
        rng = RNGIntegration()

        # Kwargs should be ignored in fallback mode
        name = rng.generate_name("test_generator", type="character", culture="elven")
        assert isinstance(name, str)
        assert " " in name

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_list_generators_empty(self):
        """Test listing generators when none are loaded."""
        rng = RNGIntegration()

        generators = rng.list_generators()
        assert generators == []


class TestRNGIntegrationWithPackage:
    """Test RNG integration when wyrdbound-rng package is available (mocked)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_generator = Mock()
        self.mock_generator.generate.return_value = "Test Generated Name"

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_initialization_with_package(self, mock_wyrdbound_rng):
        """Test RNG integration initialization when package is available."""
        rng = RNGIntegration()

        assert rng.is_available()
        assert rng.generators == {}

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_initialization_with_package_error(self, mock_wyrdbound_rng):
        """Test RNG integration initialization when package throws error."""
        # Simulate an error during initialization
        mock_wyrdbound_rng.Generator.side_effect = Exception("Import error")

        with patch.object(
            RNGIntegration, "__init__", side_effect=Exception("Init error")
        ):
            with pytest.raises(Exception, match="Init error"):
                RNGIntegration()

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_load_generator_success(self, mock_wyrdbound_rng):
        """Test successful generator loading."""
        mock_wyrdbound_rng.Generator.from_file.return_value = self.mock_generator

        rng = RNGIntegration()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = rng.load_name_generator(tmp_path)

            assert result == self.mock_generator
            assert tmp_path in rng.generators
            assert rng.generators[tmp_path] == self.mock_generator
            mock_wyrdbound_rng.Generator.from_file.assert_called_once_with(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_load_generator_cached(self, mock_wyrdbound_rng):
        """Test that generators are cached."""
        mock_wyrdbound_rng.Generator.from_file.return_value = self.mock_generator

        rng = RNGIntegration()
        test_path = "/test/path.json"

        # First load
        result1 = rng.load_name_generator(test_path)

        # Second load should return cached version
        result2 = rng.load_name_generator(test_path)

        assert result1 == result2 == self.mock_generator
        # Should only call from_file once due to caching
        mock_wyrdbound_rng.Generator.from_file.assert_called_once_with(test_path)

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_load_generator_error(self, mock_wyrdbound_rng):
        """Test generator loading with error."""
        mock_wyrdbound_rng.Generator.from_file.side_effect = Exception("File not found")

        rng = RNGIntegration()

        result = rng.load_name_generator("/nonexistent/path.json")
        assert result is None

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    def test_generate_name_with_loaded_generator(self):
        """Test name generation using loaded generator."""
        rng = RNGIntegration()
        rng.generators["test_gen"] = self.mock_generator

        result = rng.generate_name("test_gen", type="character")

        assert result == "Test Generated Name"
        self.mock_generator.generate.assert_called_once_with(type="character")

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    def test_generate_name_generator_not_loaded(self):
        """Test name generation when generator is not loaded."""
        rng = RNGIntegration()

        # Should fall back to fallback generation
        result = rng.generate_name("nonexistent_generator")

        assert isinstance(result, str)
        assert " " in result  # Fallback format

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    def test_generate_name_with_generation_error(self):
        """Test name generation when generator throws error."""
        rng = RNGIntegration()
        self.mock_generator.generate.side_effect = Exception("Generation error")
        rng.generators["error_gen"] = self.mock_generator

        # Should fall back to fallback generation
        result = rng.generate_name("error_gen")

        assert isinstance(result, str)
        assert " " in result  # Fallback format

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    def test_list_generators(self):
        """Test listing loaded generators."""
        rng = RNGIntegration()
        rng.generators["gen1"] = self.mock_generator
        rng.generators["gen2"] = Mock()

        generators = rng.list_generators()

        assert sorted(generators) == ["gen1", "gen2"]


class TestRNGFallbackGeneration:
    """Test the fallback name generation functionality."""

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_fallback_name_format(self):
        """Test fallback name format."""
        rng = RNGIntegration()

        name = rng._generate_fallback_name("test")

        assert isinstance(name, str)
        parts = name.split(" ")
        assert len(parts) == 2  # First and last name
        assert all(part.isalpha() for part in parts)  # Only letters
        assert all(part[0].isupper() for part in parts)  # Capitalized

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_fallback_name_randomness(self):
        """Test that fallback names are random."""
        rng = RNGIntegration()

        # Generate multiple names
        names = {rng._generate_fallback_name("test") for _ in range(50)}

        # Should have multiple different names
        assert len(names) > 10  # Reasonable expectation of variety

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    def test_fallback_name_with_kwargs(self):
        """Test fallback name generation ignores kwargs."""
        rng = RNGIntegration()

        # Should work the same regardless of kwargs
        name1 = rng._generate_fallback_name("test")
        name2 = rng._generate_fallback_name("test", type="character", culture="human")

        # Both should be valid names (can't test equality due to randomness)
        assert isinstance(name1, str) and " " in name1
        assert isinstance(name2, str) and " " in name2


class TestRNGIntegrationLogging:
    """Test logging behavior of RNG integration."""

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", False)
    @patch("grimoire_runner.integrations.rng_integration.logger")
    def test_logging_when_package_unavailable(self, mock_logger):
        """Test logging when package is not available."""
        RNGIntegration()

        mock_logger.warning.assert_called_with("Using fallback name generation")

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.logger")
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_logging_on_successful_init(self, mock_wyrdbound_rng, mock_logger):
        """Test logging on successful initialization."""
        RNGIntegration()

        mock_logger.debug.assert_called_with("wyrdbound-rng integration initialized")

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.logger")
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_logging_on_generator_load_success(self, mock_wyrdbound_rng, mock_logger):
        """Test logging on successful generator loading."""
        mock_generator = Mock()
        mock_wyrdbound_rng.Generator.from_file.return_value = mock_generator

        rng = RNGIntegration()
        test_path = "/test/path.json"
        rng.load_name_generator(test_path)

        mock_logger.debug.assert_any_call(f"Loaded name generator: {test_path}")

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.logger")
    @patch("grimoire_runner.integrations.rng_integration.wyrdbound_rng")
    def test_logging_on_generator_load_error(self, mock_wyrdbound_rng, mock_logger):
        """Test logging on generator loading error."""
        error_msg = "File not found"
        mock_wyrdbound_rng.Generator.from_file.side_effect = Exception(error_msg)

        rng = RNGIntegration()
        test_path = "/nonexistent/path.json"
        rng.load_name_generator(test_path)

        mock_logger.error.assert_called_with(
            f"Failed to load name generator from {test_path}: {error_msg}"
        )

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.logger")
    def test_logging_on_generate_error(self, mock_logger):
        """Test logging on name generation error."""
        rng = RNGIntegration()
        mock_generator = Mock()
        error_msg = "Generation failed"
        mock_generator.generate.side_effect = Exception(error_msg)
        rng.generators["error_gen"] = mock_generator

        rng.generate_name("error_gen")

        mock_logger.error.assert_called_with(
            f"Error generating name with error_gen: {error_msg}"
        )

    @patch("grimoire_runner.integrations.rng_integration.RNG_AVAILABLE", True)
    @patch("grimoire_runner.integrations.rng_integration.logger")
    def test_logging_on_generator_not_found(self, mock_logger):
        """Test logging when generator is not loaded."""
        rng = RNGIntegration()

        rng.generate_name("nonexistent_generator")

        mock_logger.warning.assert_called_with(
            "Name generator 'nonexistent_generator' not loaded"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
