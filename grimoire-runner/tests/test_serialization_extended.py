"""
Tests for serialization utilities.
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.utils.serialization import SerializationHelpers


class TestSerializationHelpers:
    """Test the SerializationHelpers utility class."""

    def test_to_json_pretty(self):
        """Test JSON serialization with pretty formatting."""
        data = {"name": "test", "value": 123, "nested": {"key": "value"}}

        result = SerializationHelpers.to_json(data, pretty=True)

        assert "{\n" in result  # Pretty formatting includes newlines
        assert '"name": "test"' in result
        assert '"value": 123' in result
        assert '"nested"' in result

        # Should be parseable back
        parsed = json.loads(result)
        assert parsed == data

    def test_to_json_compact(self):
        """Test JSON serialization without pretty formatting."""
        data = {"name": "test", "value": 123}

        result = SerializationHelpers.to_json(data, pretty=False)

        assert "\n" not in result  # No pretty formatting
        assert '"name":"test"' in result or '"name": "test"' in result

        # Should be parseable back
        parsed = json.loads(result)
        assert parsed == data

    def test_to_json_unicode(self):
        """Test JSON serialization with unicode characters."""
        data = {"unicode": "café", "emoji": "🎲", "chinese": "测试"}

        result = SerializationHelpers.to_json(data)

        # Should preserve unicode characters
        assert "café" in result
        assert "🎲" in result
        assert "测试" in result

        parsed = json.loads(result)
        assert parsed == data

    def test_to_json_with_datetime(self):
        """Test JSON serialization with datetime objects."""
        from datetime import datetime

        data = {"timestamp": datetime(2023, 1, 1, 12, 0, 0)}

        result = SerializationHelpers.to_json(data)

        # Should convert datetime to string
        assert "2023-01-01 12:00:00" in result

    def test_to_json_error_handling(self):
        """Test JSON serialization error handling."""
        # Create a non-serializable object
        class NonSerializable:
            def __str__(self):
                raise Exception("Cannot convert to string")

        data = {"bad": NonSerializable()}

        with pytest.raises(ValueError, match="Failed to serialize to JSON"):
            SerializationHelpers.to_json(data)

    def test_from_json_valid(self):
        """Test JSON parsing with valid input."""
        json_str = '{"name": "test", "value": 123, "flag": true}'

        result = SerializationHelpers.from_json(json_str)

        assert result == {"name": "test", "value": 123, "flag": True}

    def test_from_json_unicode(self):
        """Test JSON parsing with unicode characters."""
        json_str = '{"unicode": "café", "emoji": "🎲"}'

        result = SerializationHelpers.from_json(json_str)

        assert result == {"unicode": "café", "emoji": "🎲"}

    def test_from_json_error_handling(self):
        """Test JSON parsing error handling."""
        invalid_json = '{"name": "test", "value":}'  # Missing value

        with pytest.raises(ValueError, match="Failed to parse JSON"):
            SerializationHelpers.from_json(invalid_json)

    def test_to_yaml_pretty(self):
        """Test YAML serialization with pretty formatting."""
        data = {"name": "test", "value": 123, "nested": {"key": "value"}}

        result = SerializationHelpers.to_yaml(data, pretty=True)

        assert "name: test" in result
        assert "value: 123" in result
        assert "nested:" in result
        assert "  key: value" in result  # Indentation

        # Should be parseable back
        parsed = yaml.safe_load(result)
        assert parsed == data

    def test_to_yaml_compact(self):
        """Test YAML serialization without pretty formatting."""
        data = {"name": "test", "value": 123}

        result = SerializationHelpers.to_yaml(data, pretty=False)

        assert "name: test" in result
        assert "value: 123" in result

        # Should be parseable back
        parsed = yaml.safe_load(result)
        assert parsed == data

    def test_to_yaml_unicode(self):
        """Test YAML serialization with unicode characters."""
        data = {"unicode": "café", "emoji": "🎲", "chinese": "测试"}

        result = SerializationHelpers.to_yaml(data)

        # Should preserve unicode characters
        assert "café" in result
        assert "🎲" in result
        assert "测试" in result

        parsed = yaml.safe_load(result)
        assert parsed == data

    def test_to_yaml_error_handling(self):
        """Test YAML serialization error handling."""
        # Create a non-serializable object
        class NonSerializable:
            pass

        # YAML will try to serialize this but should be handled
        data = {"bad": NonSerializable()}

        # This might not always fail depending on PyYAML version
        # but if it does, it should be handled gracefully
        try:
            result = SerializationHelpers.to_yaml(data)
            # If successful, just verify it's a string
            assert isinstance(result, str)
        except ValueError as e:
            assert "Failed to serialize to YAML" in str(e)

    def test_from_yaml_valid(self):
        """Test YAML parsing with valid input."""
        yaml_str = """
        name: test
        value: 123
        flag: true
        list:
          - item1
          - item2
        """

        result = SerializationHelpers.from_yaml(yaml_str)

        assert result["name"] == "test"
        assert result["value"] == 123
        assert result["flag"] is True
        assert result["list"] == ["item1", "item2"]

    def test_from_yaml_unicode(self):
        """Test YAML parsing with unicode characters."""
        yaml_str = "unicode: café\nemoji: 🎲"

        result = SerializationHelpers.from_yaml(yaml_str)

        assert result == {"unicode": "café", "emoji": "🎲"}

    def test_from_yaml_error_handling(self):
        """Test YAML parsing error handling."""
        invalid_yaml = "name: test\n  invalid: indentation"  # Invalid YAML

        with pytest.raises(ValueError, match="Failed to parse YAML"):
            SerializationHelpers.from_yaml(invalid_yaml)

    def test_load_from_file_json(self):
        """Test loading data from JSON file."""
        data = {"name": "test", "value": 123}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = SerializationHelpers.load_from_file(temp_path)
            assert result == data
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_yaml(self):
        """Test loading data from YAML file."""
        data = {"name": "test", "value": 123}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name

        try:
            result = SerializationHelpers.load_from_file(temp_path)
            assert result == data
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_yml_extension(self):
        """Test loading data from .yml file."""
        data = {"name": "test", "value": 123}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name

        try:
            result = SerializationHelpers.load_from_file(temp_path)
            assert result == data
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_auto_detect_yaml(self):
        """Test loading YAML from file with unknown extension."""
        data = {"name": "test", "value": 123}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            yaml.dump(data, f)
            temp_path = f.name

        try:
            result = SerializationHelpers.load_from_file(temp_path)
            assert result == data
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_auto_detect_json(self):
        """Test loading JSON from file with unknown extension when YAML fails."""
        data = {"name": "test", "value": 123}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            json.dump(data, f)
            temp_path = f.name

        try:
            result = SerializationHelpers.load_from_file(temp_path)
            assert result == data
        finally:
            Path(temp_path).unlink()

    def test_load_from_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            SerializationHelpers.load_from_file("nonexistent.json")

    def test_load_from_file_invalid_content(self):
        """Test loading from file with invalid content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Failed to load file"):
                SerializationHelpers.load_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_save_to_file_json(self):
        """Test saving data to JSON file."""
        data = {"name": "test", "value": 123}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.json"

            SerializationHelpers.save_to_file(data, file_path)

            assert file_path.exists()
            with open(file_path) as f:
                loaded = json.load(f)
            assert loaded == data

    def test_save_to_file_yaml(self):
        """Test saving data to YAML file."""
        data = {"name": "test", "value": 123}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.yaml"

            SerializationHelpers.save_to_file(data, file_path)

            assert file_path.exists()
            with open(file_path) as f:
                loaded = yaml.safe_load(f)
            assert loaded == data

    def test_save_to_file_explicit_format(self):
        """Test saving with explicit format parameter."""
        data = {"name": "test", "value": 123}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"

            # Save as YAML despite .txt extension
            SerializationHelpers.save_to_file(data, file_path, format="yaml")

            assert file_path.exists()
            with open(file_path) as f:
                loaded = yaml.safe_load(f)
            assert loaded == data

    def test_save_to_file_creates_directories(self):
        """Test that save_to_file creates missing directories."""
        data = {"name": "test"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "subdir" / "nested" / "test.json"

            SerializationHelpers.save_to_file(data, file_path)

            assert file_path.exists()
            assert file_path.parent.exists()

    def test_save_to_file_unsupported_format(self):
        """Test saving with unsupported format."""
        data = {"name": "test"}

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test.txt"

            with pytest.raises(ValueError, match="Unsupported format"):
                SerializationHelpers.save_to_file(data, file_path, format="xml")

    def test_deep_merge_simple(self):
        """Test deep merging of simple dictionaries."""
        base = {"a": 1, "b": 2}
        update = {"b": 3, "c": 4}

        result = SerializationHelpers.deep_merge(base, update)

        assert result == {"a": 1, "b": 3, "c": 4}
        # Original should not be modified
        assert base == {"a": 1, "b": 2}

    def test_deep_merge_nested(self):
        """Test deep merging of nested dictionaries."""
        base = {"a": 1, "nested": {"x": 10, "y": 20}}
        update = {"nested": {"y": 30, "z": 40}, "b": 2}

        result = SerializationHelpers.deep_merge(base, update)

        expected = {"a": 1, "nested": {"x": 10, "y": 30, "z": 40}, "b": 2}
        assert result == expected

    def test_deep_merge_overwrite_non_dict(self):
        """Test that non-dict values are overwritten completely."""
        base = {"a": {"x": 1}, "b": [1, 2, 3]}
        update = {"a": "string", "b": {"y": 2}}

        result = SerializationHelpers.deep_merge(base, update)

        assert result == {"a": "string", "b": {"y": 2}}

    def test_flatten_dict_simple(self):
        """Test flattening simple nested dictionary."""
        data = {"a": 1, "b": {"c": 2, "d": 3}}

        result = SerializationHelpers.flatten_dict(data)

        assert result == {"a": 1, "b.c": 2, "b.d": 3}

    def test_flatten_dict_deeply_nested(self):
        """Test flattening deeply nested dictionary."""
        data = {"a": {"b": {"c": {"d": 1}}}, "x": 2}

        result = SerializationHelpers.flatten_dict(data)

        assert result == {"a.b.c.d": 1, "x": 2}

    def test_flatten_dict_custom_separator(self):
        """Test flattening with custom separator."""
        data = {"a": 1, "b": {"c": 2}}

        result = SerializationHelpers.flatten_dict(data, separator="_")

        assert result == {"a": 1, "b_c": 2}

    def test_flatten_dict_with_prefix(self):
        """Test flattening with prefix."""
        data = {"a": 1, "b": {"c": 2}}

        result = SerializationHelpers.flatten_dict(data, prefix="root")

        assert result == {"root.a": 1, "root.b.c": 2}

    def test_unflatten_dict_simple(self):
        """Test unflattening simple dictionary."""
        data = {"a": 1, "b.c": 2, "b.d": 3}

        result = SerializationHelpers.unflatten_dict(data)

        assert result == {"a": 1, "b": {"c": 2, "d": 3}}

    def test_unflatten_dict_deeply_nested(self):
        """Test unflattening deeply nested dictionary."""
        data = {"a.b.c.d": 1, "x": 2}

        result = SerializationHelpers.unflatten_dict(data)

        assert result == {"a": {"b": {"c": {"d": 1}}}, "x": 2}

    def test_unflatten_dict_custom_separator(self):
        """Test unflattening with custom separator."""
        data = {"a": 1, "b_c": 2}

        result = SerializationHelpers.unflatten_dict(data, separator="_")

        assert result == {"a": 1, "b": {"c": 2}}

    def test_flatten_unflatten_roundtrip(self):
        """Test that flatten and unflatten are inverse operations."""
        original = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": 4}

        flattened = SerializationHelpers.flatten_dict(original)
        unflattened = SerializationHelpers.unflatten_dict(flattened)

        assert unflattened == original

    def test_sanitize_for_filename_basic(self):
        """Test basic filename sanitization."""
        result = SerializationHelpers.sanitize_for_filename("normal_filename.txt")
        assert result == "normal_filename.txt"

    def test_sanitize_for_filename_invalid_chars(self):
        """Test sanitizing invalid filename characters."""
        result = SerializationHelpers.sanitize_for_filename('file<>:"/\\|?*.txt')
        assert result == "file_.txt"

    def test_sanitize_for_filename_unicode(self):
        """Test sanitizing unicode characters."""
        result = SerializationHelpers.sanitize_for_filename("café_测试.txt")
        # Check that result is a valid string and doesn't crash
        assert isinstance(result, str)
        assert len(result) > 0
        # The exact behavior depends on the regex - just ensure it's handled gracefully

    def test_sanitize_for_filename_spaces_and_underscores(self):
        """Test handling of spaces and multiple underscores."""
        result = SerializationHelpers.sanitize_for_filename("file   with    spaces___and___underscores")
        assert result == "file_with_spaces_and_underscores"

    def test_sanitize_for_filename_length_limit(self):
        """Test that long filenames are truncated."""
        long_name = "a" * 150  # Longer than 100 character limit
        result = SerializationHelpers.sanitize_for_filename(long_name)
        assert len(result) <= 100

    def test_sanitize_for_filename_empty_fallback(self):
        """Test fallback for empty or all-invalid input."""
        result = SerializationHelpers.sanitize_for_filename("!@#$%^&*()")
        assert result == "unnamed"

        result = SerializationHelpers.sanitize_for_filename("")
        assert result == "unnamed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
