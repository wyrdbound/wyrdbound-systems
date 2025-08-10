"""Unified template resolution service for GRIMOIRE runner."""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from jinja2 import (
    BaseLoader,
    Environment,
    StrictUndefined,
    TemplateError,
    meta,
)

logger = logging.getLogger(__name__)


class TemplateResolutionStrategy(ABC):
    """Abstract base class for template resolution strategies."""

    @abstractmethod
    def resolve_template(self, template_str: str, context_data: Any) -> Any:
        """Resolve a template string with the given context."""
        pass

    @abstractmethod
    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        pass


class RuntimeTemplateStrategy(TemplateResolutionStrategy):
    """Template resolution strategy for runtime execution context."""

    def __init__(self):
        self._jinja_env = Environment(undefined=StrictUndefined)
        self._setup_template_functions()

    def _setup_template_functions(self):
        """Setup custom functions available in runtime templates."""
        self._jinja_env.globals.update(
            {
                "get_value": self._template_get_value,
                "has_value": self._template_has_value,
            }
        )

        # Add standard Python functions
        self._jinja_env.globals.update(
            {
                "range": range,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
            }
        )

    def resolve_template(self, template_str: str, context_data: Any) -> Any:
        """Resolve a template using runtime execution context."""
        if not isinstance(template_str, str):
            return template_str

        # Skip if no template syntax
        if not self.is_template(template_str):
            return template_str

        try:
            template = self._jinja_env.from_string(template_str)

            # context_data should be a dict with all template variables
            if not isinstance(context_data, dict):
                logger.warning(
                    f"Expected dict for runtime template context, got {type(context_data)}"
                )
                return template_str

            result = template.render(context_data)

            # Try to parse as structured data if it looks like it
            parsed_result = self._try_parse_structured_data(result)
            if parsed_result is not None:
                return parsed_result

            return result

        except Exception as e:
            logger.error(
                f"Runtime template resolution failed for '{template_str}': {e}"
            )
            return template_str

    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        if not isinstance(text, str):
            return False
        return "{{" in text or "{%" in text

    def _try_parse_structured_data(self, result: str) -> Any:
        """Try to parse template result as structured data."""
        import ast
        import json

        import yaml

        result = result.strip()

        # Try to parse as number first
        try:
            if "." in result:
                return float(result)
            else:
                return int(result)
        except ValueError:
            pass

        # Explicitly handle boolean strings
        if result.lower() == "true":
            return True
        elif result.lower() == "false":
            return False

        # Try JSON for clearly JSON-formatted results
        if (result.startswith("{") and result.endswith("}")) or (
            result.startswith("[") and result.endswith("]")
        ):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

        # Try Python literal evaluation for Python representations like "['a', 'b', 'c']"
        try:
            parsed = ast.literal_eval(result)
            # Only return if it's actually structured data (not a simple string or number)
            if isinstance(parsed, list | dict | tuple | set):
                return parsed
        except (ValueError, SyntaxError):
            pass

        # Try YAML - but be more selective to avoid parsing display text
        # Only parse multi-line YAML or clearly structured single-line YAML
        if result.count("\n") > 0 or (
            result.startswith("- ") or result.startswith("  ")
        ):
            try:
                parsed = yaml.safe_load(result)
                if parsed != result and not isinstance(
                    parsed, str
                ):  # If YAML parsing changed something meaningful, use it
                    return parsed
            except yaml.YAMLError:
                pass

        # Special handling for single-line YAML that might be intentional structured data
        # but not simple display text like "Strength: +2"
        if ":" in result and (
            result.count("\n") > 0
            or not any(char in result for char in ["+", "-", "Strength", "Dexterity"])
        ):
            try:
                parsed = yaml.safe_load(result)
                if parsed != result and isinstance(
                    parsed, dict
                ):  # Only use parsed dict if it's actually structured
                    return parsed
            except yaml.YAMLError:
                pass

        return None

    def _template_get_value(self, path: str, default: Any = None) -> Any:
        """Template function to get values by path."""
        # This will be bound to the actual context during template resolution
        # For now, return the default - the actual implementation will be injected
        return default

    def _template_has_value(self, path: str) -> bool:
        """Template function to check if a path has a value."""
        # This will be bound to the actual context during template resolution
        return False


class LoadTimeTemplateStrategy(TemplateResolutionStrategy):
    """Template resolution strategy for system loading time."""

    def __init__(self):
        self.loader = StringTemplateLoader()
        self.env = Environment(
            loader=self.loader,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._setup_custom_functions()

    def _setup_custom_functions(self) -> None:
        """Setup custom Jinja2 functions and filters for load time."""
        # Custom filters
        self.env.filters["title_case"] = lambda x: str(x).title()
        self.env.filters["snake_case"] = lambda x: re.sub(
            r"[^a-zA-Z0-9]", "_", str(x)
        ).lower()
        self.env.filters["kebab_case"] = lambda x: re.sub(
            r"[^a-zA-Z0-9]", "-", str(x)
        ).lower()
        self.env.filters["upper_first"] = (
            lambda x: str(x)[:1].upper() + str(x)[1:] if x else ""
        )

        # Dice-related filters
        self.env.filters["dice_modifier"] = self._format_dice_modifier
        self.env.filters["signed_number"] = self._format_signed_number

        # Custom globals
        self.env.globals["range"] = range
        self.env.globals["len"] = len
        self.env.globals["str"] = str
        self.env.globals["int"] = int
        self.env.globals["float"] = float

    def _format_dice_modifier(self, value: Any) -> str:
        """Format a number as a dice modifier (+3, -1, etc.)."""
        try:
            num = int(value)
            if num >= 0:
                return f"+{num}"
            else:
                return str(num)  # Already has minus sign
        except (ValueError, TypeError):
            return str(value)

    def _format_signed_number(self, value: Any) -> str:
        """Format a number with explicit sign."""
        try:
            num = float(value)
            if num >= 0:
                return f"+{num:g}"
            else:
                return f"{num:g}"
        except (ValueError, TypeError):
            return str(value)

    def resolve_template(self, template_str: str, context_data: Any) -> Any:
        """Resolve a template using load time context."""
        if not isinstance(template_str, str):
            return template_str

        try:
            template = self.env.from_string(template_str)

            # Ensure context_data is a dict
            if not isinstance(context_data, dict):
                context_data = {"value": context_data}

            return template.render(context_data)
        except TemplateError as e:
            logger.error(f"Load time template rendering error: {e}")
            raise ValueError(f"Template error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected load time template error: {e}")
            raise ValueError(f"Template processing failed: {e}") from e

    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        if not isinstance(text, str):
            return False
        return "{{" in text or "{%" in text or "{#" in text

    def add_template(self, name: str, template_str: str) -> None:
        """Add a named template that can be referenced later."""
        self.loader.add_template(name, template_str)

    def render_named_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a previously added named template."""
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except TemplateError as e:
            logger.error(f"Named template rendering error: {e}")
            raise ValueError(f"Template '{template_name}' error: {e}") from e

    def validate_template(self, template_str: str) -> str | None:
        """Validate a template string and return error message if invalid."""
        try:
            self.env.from_string(template_str)
            return None
        except TemplateError as e:
            return str(e)

    def extract_variables(self, template_str: str) -> set[str]:
        """Extract variable names used in a template."""
        try:
            ast = self.env.parse(template_str)
            return set(meta.find_undeclared_variables(ast))
        except Exception as e:
            logger.warning(f"Could not extract variables from template: {e}")
            return set()

    def escape_for_template(self, text: str) -> str:
        """Escape text so it can be safely included in a template."""
        # Escape template delimiters
        text = text.replace("{{", r"\{\{")
        text = text.replace("}}", r"\}\}")
        text = text.replace("{%", r"\{\%")
        text = text.replace("%}", r"\%\}")
        text = text.replace("{#", r"\{\#")
        text = text.replace("#}", r"\#\}")
        return text


class StringTemplateLoader(BaseLoader):
    """Custom Jinja2 loader for string templates."""

    def __init__(self):
        self.templates: dict[str, str] = {}

    def get_source(self, environment: Environment, template: str) -> tuple:
        # environment parameter required by Jinja2 interface but not used in this implementation
        _ = environment
        if template in self.templates:
            source = self.templates[template]
            return source, None, lambda: True
        raise TemplateError(f"Template '{template}' not found")

    def add_template(self, name: str, source: str) -> None:
        """Add a template to the loader."""
        self.templates[name] = source


class TemplateService:
    """Unified template resolution service with strategy pattern."""

    def __init__(self):
        self._strategies = {
            "runtime": RuntimeTemplateStrategy(),
            "loadtime": LoadTimeTemplateStrategy(),
        }

    def resolve_template(
        self, template_str: str, context_data: Any, mode: str = "runtime"
    ) -> Any:
        """Resolve a template using the specified strategy."""
        if mode not in self._strategies:
            raise ValueError(f"Unknown template resolution mode: {mode}")

        return self._strategies[mode].resolve_template(template_str, context_data)

    def resolve_template_with_execution_context(
        self, template_str: str, execution_context, system=None, mode: str = "runtime"
    ) -> Any:
        """Resolve a template using ExecutionContext, automatically converting to dict format."""
        # Debug logging for template resolution
        import logging

        logger = logging.getLogger(__name__)

        # Let's check the actual ExecutionContext outputs before conversion
        logger.debug(
            f"BEFORE dict conversion - execution_context.outputs type: {type(execution_context.outputs)}"
        )
        logger.debug(
            f"BEFORE dict conversion - execution_context.outputs content: {execution_context.outputs}"
        )
        if hasattr(execution_context.outputs, "items"):
            for key, value in execution_context.outputs.items():
                logger.debug(
                    f"BEFORE dict conversion - outputs[{key}] = {value} (type: {type(value)})"
                )

        # Convert ExecutionContext to dict for template resolution
        context_dict = {
            "inputs": dict(execution_context.inputs),
            "variables": dict(execution_context.variables),
            "outputs": dict(execution_context.outputs),
        }

        logger.debug(f"Template resolution input: '{template_str}'")
        logger.debug(f"Context dict outputs: {context_dict['outputs']}")
        if "outputs" in context_dict:
            for key, value in context_dict["outputs"].items():
                logger.debug(
                    f"AFTER dict conversion - outputs[{key}] = {value} (type: {type(value)})"
                )

        # Add system metadata if available
        if system:
            context_dict["system"] = {
                "id": system.id,
                "name": system.name,
                "description": system.description,
            }

        result = self.resolve_template(template_str, context_dict, mode)
        logger.debug(f"Template resolution result: '{result}'")
        return result

    def is_template(self, text: str, mode: str = "runtime") -> bool:
        """Check if a string contains template syntax."""
        if mode not in self._strategies:
            raise ValueError(f"Unknown template resolution mode: {mode}")

        return self._strategies[mode].is_template(text)

    def get_strategy(self, mode: str) -> TemplateResolutionStrategy:
        """Get a specific template resolution strategy."""
        if mode not in self._strategies:
            raise ValueError(f"Unknown template resolution mode: {mode}")

        return self._strategies[mode]

    # Convenience methods for backward compatibility
    def add_template(self, name: str, template_str: str) -> None:
        """Add a named template (loadtime strategy)."""
        loadtime_strategy = self._strategies["loadtime"]
        if hasattr(loadtime_strategy, "add_template"):
            loadtime_strategy.add_template(name, template_str)

    def render_named_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a named template (loadtime strategy)."""
        loadtime_strategy = self._strategies["loadtime"]
        if hasattr(loadtime_strategy, "render_named_template"):
            return loadtime_strategy.render_named_template(template_name, context)
        raise ValueError("Named template rendering not supported in runtime mode")

    def validate_template(
        self, template_str: str, mode: str = "loadtime"
    ) -> str | None:
        """Validate a template string."""
        strategy = self._strategies[mode]
        if hasattr(strategy, "validate_template"):
            return strategy.validate_template(template_str)
        return None

    def extract_variables(self, template_str: str, mode: str = "loadtime") -> set[str]:
        """Extract variable names used in a template."""
        strategy = self._strategies[mode]
        if hasattr(strategy, "extract_variables"):
            return strategy.extract_variables(template_str)
        return set()

    def escape_for_template(self, text: str, mode: str = "loadtime") -> str:
        """Escape text for template inclusion."""
        strategy = self._strategies[mode]
        if hasattr(strategy, "escape_for_template"):
            return strategy.escape_for_template(text)
        return text
