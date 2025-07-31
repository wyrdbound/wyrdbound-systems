"""Serialization utilities for GRIMOIRE runner."""

import json
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class SerializationHelpers:
    """Helper functions for serializing and deserializing GRIMOIRE data."""

    @staticmethod
    def to_json(data: Any, pretty: bool = True) -> str:
        """Convert data to JSON string."""
        try:
            if pretty:
                return json.dumps(data, indent=2, default=str, ensure_ascii=False)
            else:
                return json.dumps(data, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"JSON serialization error: {e}")
            raise ValueError(f"Failed to serialize to JSON: {e}")

    @staticmethod
    def from_json(json_str: str) -> Any:
        """Parse JSON string to data."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise ValueError(f"Failed to parse JSON: {e}")

    @staticmethod
    def to_yaml(data: Any, pretty: bool = True) -> str:
        """Convert data to YAML string."""
        try:
            if pretty:
                return yaml.dump(
                    data,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                    sort_keys=False,
                )
            else:
                return yaml.dump(data, allow_unicode=True)
        except Exception as e:
            logger.error(f"YAML serialization error: {e}")
            raise ValueError(f"Failed to serialize to YAML: {e}")

    @staticmethod
    def from_yaml(yaml_str: str) -> Any:
        """Parse YAML string to data."""
        try:
            return yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise ValueError(f"Failed to parse YAML: {e}")

    @staticmethod
    def load_from_file(file_path: str | Path) -> Any:
        """Load data from a JSON or YAML file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Determine format by extension
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                return SerializationHelpers.from_yaml(content)
            elif file_path.suffix.lower() == ".json":
                return SerializationHelpers.from_json(content)
            else:
                # Try YAML first, then JSON
                try:
                    return SerializationHelpers.from_yaml(content)
                except ValueError:
                    return SerializationHelpers.from_json(content)

        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise ValueError(f"Failed to load file {file_path}: {e}")

    @staticmethod
    def save_to_file(
        data: Any, file_path: str | Path, format: str | None = None
    ) -> None:
        """Save data to a JSON or YAML file."""
        file_path = Path(file_path)

        # Determine format
        if format is None:
            format = "yaml" if file_path.suffix.lower() in [".yaml", ".yml"] else "json"

        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize data
            if format.lower() == "yaml":
                content = SerializationHelpers.to_yaml(data)
            elif format.lower() == "json":
                content = SerializationHelpers.to_json(data)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.debug(f"Data saved to {file_path}")

        except Exception as e:
            logger.error(f"Error saving file {file_path}: {e}")
            raise ValueError(f"Failed to save file {file_path}: {e}")

    @staticmethod
    def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in update.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = SerializationHelpers.deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def flatten_dict(
        data: dict[str, Any], separator: str = ".", prefix: str = ""
    ) -> dict[str, Any]:
        """Flatten a nested dictionary using dot notation."""
        result = {}

        for key, value in data.items():
            new_key = f"{prefix}{separator}{key}" if prefix else key

            if isinstance(value, dict):
                result.update(
                    SerializationHelpers.flatten_dict(value, separator, new_key)
                )
            else:
                result[new_key] = value

        return result

    @staticmethod
    def unflatten_dict(data: dict[str, Any], separator: str = ".") -> dict[str, Any]:
        """Unflatten a dictionary from dot notation."""
        result = {}

        for key, value in data.items():
            parts = key.split(separator)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result

    @staticmethod
    def sanitize_for_filename(text: str) -> str:
        """Sanitize text to be safe for use in filenames."""
        import re

        # Replace invalid characters with underscores
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", text)

        # Remove any remaining problematic characters
        sanitized = re.sub(r"[^\w\-_\. ]", "", sanitized)

        # Collapse multiple underscores/spaces
        sanitized = re.sub(r"[_\s]+", "_", sanitized)

        # Trim and limit length
        sanitized = sanitized.strip("_").strip()[:100]

        return sanitized or "unnamed"
