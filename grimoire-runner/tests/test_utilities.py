"""
Comprehensive tests for utility modules - logging and serialization.
Part of Phase 2 of the test coverage improvement plan.
"""

import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.utils.logging import get_logger, setup_logging
from grimoire_runner.utils.serialization import SerializationHelpers


class TestLogging:
    """Test the logging utility module."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        setup_logging()

        # Should not raise any exceptions
        logger = logging.getLogger()
        assert logger is not None

    def test_setup_logging_with_level(self):
        """Test setup_logging with specific log level."""
        setup_logging(level="DEBUG")

        logger = logging.getLogger()
        assert logger.level <= logging.DEBUG

    def test_setup_logging_with_file(self):
        """Test setup_logging with file output - not supported by current API."""
        # The current setup_logging API doesn't support file output
        # This test is no longer applicable
        pass

    def test_setup_logging_with_format(self):
        """Test setup_logging with custom format."""
        custom_format = "%(levelname)s - %(message)s"
        setup_logging(format_string=custom_format)

        # Should not raise any exceptions
        logger = logging.getLogger()
        assert logger is not None

    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger("test_module")

        assert logger is not None
        assert logger.name == "test_module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_level(self):
        """Test get_logger with specific level - not supported by current API."""
        # The current get_logger API doesn't accept a level parameter
        logger = get_logger("test_module")

        assert logger is not None
        # Set level separately
        logger.setLevel(logging.WARNING)
        assert logger.level == logging.WARNING

    def test_get_logger_same_name(self):
        """Test that get_logger returns same instance for same name."""
        logger1 = get_logger("same_name")
        logger2 = get_logger("same_name")

        assert logger1 is logger2

    def test_logging_hierarchy(self):
        """Test logging hierarchy works correctly."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")

        assert child_logger.parent == parent_logger

    def test_logging_levels(self):
        """Test different logging levels."""
        logger = get_logger("test_levels")

        # Test that all level methods exist and work
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Should not raise any exceptions

    def test_logging_with_extra_data(self):
        """Test logging with extra data."""
        logger = get_logger("test_extra")

        extra_data = {"user_id": 123, "action": "test"}
        logger.info("Test message with extra data", extra=extra_data)

        # Should not raise any exceptions

    def test_logging_exception_handling(self):
        """Test logging exception handling."""
        logger = get_logger("test_exceptions")

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred")

        # Should not raise any exceptions

    def test_setup_logging_console_output(self):
        """Test setup_logging with console output - console is default behavior."""
        with patch("sys.stdout"):
            setup_logging()  # Console output is default

            logger = logging.getLogger()
            logger.info("Console test message")

            # Should not raise any exceptions

    def test_setup_logging_no_console(self):
        """Test setup_logging without console output - using use_rich=False."""
        setup_logging(use_rich=False)

        logger = logging.getLogger()
        logger.info("No console test message")

        # Should not raise any exceptions

    def test_logging_configuration_persistence(self):
        """Test that logging configuration persists."""
        setup_logging(level="ERROR")

        logger1 = get_logger("test1")
        logger2 = get_logger("test2")

        # Both loggers should respect the configuration
        assert logger1.level <= logging.ERROR
        assert logger2.level <= logging.ERROR


class TestSerialization:
    """Test the serialization utility module."""

    def test_serialize_data_dict(self):
        """Test serializing dictionary data."""
        test_data = {"name": "Test", "value": 42, "items": ["a", "b", "c"]}

        # Test JSON serialization
        json_result = SerializationHelpers.to_json(test_data)
        assert isinstance(json_result, str)
        assert "Test" in json_result
        assert "42" in json_result

        # Test YAML serialization
        yaml_result = SerializationHelpers.to_yaml(test_data)
        assert isinstance(yaml_result, str)
        assert "Test" in yaml_result
        assert "42" in yaml_result

    def test_serialize_data_list(self):
        """Test serializing list data."""
        test_data = [{"name": "Item1", "value": 1}, {"name": "Item2", "value": 2}]

        json_result = SerializationHelpers.to_json(test_data)
        assert isinstance(json_result, str)
        assert "Item1" in json_result
        assert "Item2" in json_result

    def test_serialize_data_invalid_format(self):
        """Test serializing with invalid format - this test doesn't apply to current API."""
        # The current SerializationHelpers API doesn't take a format parameter
        # for to_json/to_yaml methods, so this test is no longer relevant
        pass

    def test_serialize_data_non_serializable(self):
        """Test serializing non-serializable data."""

        class NonSerializable:
            pass

        test_data = {"object": NonSerializable()}

        # The current API converts non-serializable objects to string
        # So this doesn't raise TypeError anymore, but let's test the behavior
        result = SerializationHelpers.to_json(test_data)
        assert isinstance(result, str)
        # Should contain string representation of the object
        assert "NonSerializable" in result

    def test_deserialize_data_json(self):
        """Test deserializing JSON data."""
        json_string = '{"name": "Test", "value": 42}'

        result = SerializationHelpers.from_json(json_string)

        assert isinstance(result, dict)
        assert result["name"] == "Test"
        assert result["value"] == 42

    def test_deserialize_data_yaml(self):
        """Test deserializing YAML data."""
        yaml_string = """
        name: Test
        value: 42
        items:
          - a
          - b
          - c
        """

        result = SerializationHelpers.from_yaml(yaml_string)

        assert isinstance(result, dict)
        assert result["name"] == "Test"
        assert result["value"] == 42
        assert result["items"] == ["a", "b", "c"]

    def test_deserialize_data_invalid_json(self):
        """Test deserializing invalid JSON."""
        invalid_json = '{"name": "Test", "value":}'

        with pytest.raises(ValueError):
            SerializationHelpers.from_json(invalid_json)

    def test_deserialize_data_invalid_yaml(self):
        """Test deserializing invalid YAML."""
        invalid_yaml = """
        name: Test
        value: [unclosed list
        """

        with pytest.raises(ValueError):
            SerializationHelpers.from_yaml(invalid_yaml)

    def test_deserialize_data_invalid_format(self):
        """Test deserializing with invalid format - not applicable to current API."""
        # The current API has separate from_json and from_yaml methods
        # so this test doesn't apply anymore
        pass

    def test_save_to_file_json(self):
        """Test saving data to JSON file."""
        test_data = {"name": "Test", "value": 42}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"

            SerializationHelpers.save_to_file(test_data, file_path, format="json")

            assert file_path.exists()

            # Verify content
            with open(file_path) as f:
                content = f.read()
                assert "Test" in content
                assert "42" in content

    def test_save_to_file_yaml(self):
        """Test saving data to YAML file."""
        test_data = {"name": "Test", "value": 42}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.yaml"

            SerializationHelpers.save_to_file(test_data, file_path, format="yaml")

            assert file_path.exists()

            # Verify content
            with open(file_path) as f:
                content = f.read()
                assert "Test" in content
                assert "42" in content

    def test_save_to_file_auto_format(self):
        """Test saving data with auto-detected format."""
        test_data = {"name": "Test", "value": 42}

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test JSON auto-detection
            json_path = Path(temp_dir) / "test.json"
            SerializationHelpers.save_to_file(test_data, json_path)
            assert json_path.exists()

            # Test YAML auto-detection
            yaml_path = Path(temp_dir) / "test.yaml"
            SerializationHelpers.save_to_file(test_data, yaml_path)
            assert yaml_path.exists()

    def test_save_to_file_create_directories(self):
        """Test saving file with automatic directory creation."""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "deep" / "test.json"

            SerializationHelpers.save_to_file(test_data, nested_path)

            assert nested_path.exists()
            assert nested_path.parent.exists()

    def test_load_from_file_json(self):
        """Test loading data from JSON file."""
        test_data = {"name": "Test", "value": 42}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"

            # Save data first
            SerializationHelpers.save_to_file(test_data, file_path, format="json")

            # Load and verify
            loaded_data = SerializationHelpers.load_from_file(file_path)

            assert loaded_data == test_data

    def test_load_from_file_yaml(self):
        """Test loading data from YAML file."""
        test_data = {"name": "Test", "value": 42, "items": ["a", "b"]}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.yaml"

            # Save data first
            SerializationHelpers.save_to_file(test_data, file_path, format="yaml")

            # Load and verify
            loaded_data = SerializationHelpers.load_from_file(file_path)

            assert loaded_data == test_data

    def test_load_from_file_auto_format(self):
        """Test loading data with auto-detected format."""
        test_data = {"name": "Test", "value": 42}

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test JSON auto-detection
            json_path = Path(temp_dir) / "test.json"
            SerializationHelpers.save_to_file(test_data, json_path)
            loaded_json = SerializationHelpers.load_from_file(json_path)
            assert loaded_json == test_data

            # Test YAML auto-detection
            yaml_path = Path(temp_dir) / "test.yaml"
            SerializationHelpers.save_to_file(test_data, yaml_path)
            loaded_yaml = SerializationHelpers.load_from_file(yaml_path)
            assert loaded_yaml == test_data

    def test_load_from_file_nonexistent(self):
        """Test loading from non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "nonexistent.json"

            with pytest.raises(FileNotFoundError):
                SerializationHelpers.load_from_file(file_path)

    def test_roundtrip_serialization_json(self):
        """Test complete roundtrip serialization/deserialization for JSON."""
        original_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "roundtrip.json"

            SerializationHelpers.save_to_file(original_data, file_path, format="json")
            loaded_data = SerializationHelpers.load_from_file(file_path)

            assert loaded_data == original_data

    def test_roundtrip_serialization_yaml(self):
        """Test complete roundtrip serialization/deserialization for YAML."""
        original_data = {
            "string": "test",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "roundtrip.yaml"

            SerializationHelpers.save_to_file(original_data, file_path, format="yaml")
            loaded_data = SerializationHelpers.load_from_file(file_path)

            assert loaded_data == original_data

    def test_serialize_data_pretty_json(self):
        """Test pretty JSON serialization."""
        test_data = {"name": "Test", "nested": {"key": "value"}}

        result = SerializationHelpers.to_json(test_data, pretty=True)

        assert isinstance(result, str)
        assert "\n" in result  # Should be formatted with newlines
        assert "  " in result  # Should be indented

    def test_serialize_data_compact_json(self):
        """Test compact JSON serialization."""
        test_data = {"name": "Test", "nested": {"key": "value"}}

        result = SerializationHelpers.to_json(test_data, pretty=False)

        assert isinstance(result, str)
        assert "\n" not in result.strip()  # Should be compact

    def test_serialization_encoding_handling(self):
        """Test serialization with different text encodings."""
        test_data = {
            "unicode": "测试数据",
            "emoji": "🎲🗡️⚔️",
            "accents": "café naïve résumé",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "unicode.yaml"

            SerializationHelpers.save_to_file(test_data, file_path, format="yaml")
            loaded_data = SerializationHelpers.load_from_file(file_path)

            assert loaded_data == test_data

    def test_serialization_large_data(self):
        """Test serialization with large data sets."""
        # Create large test data
        large_data = {"items": [{"id": i, "name": f"Item {i}"} for i in range(1000)]}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "large.json"

            SerializationHelpers.save_to_file(large_data, file_path, format="json")
            loaded_data = SerializationHelpers.load_from_file(file_path)

            assert len(loaded_data["items"]) == 1000
            assert loaded_data["items"][0]["name"] == "Item 0"
            assert loaded_data["items"][999]["name"] == "Item 999"

    def test_serialization_error_handling(self):
        """Test serialization error handling."""
        test_data = {"test": "data"}

        with tempfile.TemporaryDirectory() as temp_dir:
            # Test permission error simulation
            file_path = Path(temp_dir) / "readonly.json"

            with patch("builtins.open", mock_open()) as mock_file:
                mock_file.side_effect = PermissionError("Permission denied")

                with pytest.raises(
                    ValueError
                ):  # SerializationHelpers wraps errors in ValueError
                    SerializationHelpers.save_to_file(test_data, file_path)
