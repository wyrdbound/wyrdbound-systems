"""Template handling utilities for GRIMOIRE runner."""

import logging
import re
from typing import Any

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateError, meta

logger = logging.getLogger(__name__)


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


class TemplateHelpers:
    """Helper functions for template processing in GRIMOIRE."""

    def __init__(self):
        self.loader = StringTemplateLoader()
        self.env = Environment(
            loader=self.loader,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters and functions
        self._setup_custom_functions()

    def _setup_custom_functions(self) -> None:
        """Setup custom Jinja2 functions and filters."""

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

    def render_template(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a template string with the given context."""
        try:
            template = self.env.from_string(template_str)
            return template.render(context)
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise ValueError(f"Template error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected template error: {e}")
            raise ValueError(f"Template processing failed: {e}") from e

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

    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        return "{{" in text or "{%" in text or "{#" in text

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
