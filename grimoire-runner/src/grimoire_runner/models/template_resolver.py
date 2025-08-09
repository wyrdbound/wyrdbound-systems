"""Template resolution engine for GRIMOIRE execution contexts."""

import ast
import json
import logging
from typing import Any, Optional, TYPE_CHECKING

from jinja2 import Environment, StrictUndefined

if TYPE_CHECKING:
    from .flow_namespace import FlowNamespaceManager
    from .observable import DerivedFieldManager

logger = logging.getLogger(__name__)


class TemplateResolver:
    """Handles template resolution with context data integration."""

    def __init__(self):
        self._jinja_env = Environment(undefined=StrictUndefined)
        self._setup_template_functions()

    def _setup_template_functions(self):
        """Setup custom functions available in templates."""
        self._jinja_env.globals.update({
            "get_value": self._template_get_value,
            "has_value": self._template_has_value,
        })

    def resolve_template(
        self,
        template_str: str,
        variables: dict[str, Any],
        outputs: dict[str, Any],
        inputs: dict[str, Any],
        system_metadata: dict[str, Any],
        namespace_manager: Optional["FlowNamespaceManager"] = None,
        derived_field_manager: Optional["DerivedFieldManager"] = None,
    ) -> Any:
        """Resolve a Jinja2 template string with provided context."""
        if not isinstance(template_str, str):
            return template_str

        # Skip if no template syntax
        if "{{" not in template_str and "{%" not in template_str:
            return template_str

        try:
            template = self._jinja_env.from_string(template_str)
            context = self._build_template_context(
                variables, outputs, inputs, system_metadata,
                namespace_manager, derived_field_manager
            )

            # Render the template
            result = template.render(context)

            # Try to parse as structured data if it looks like it
            parsed_result = self._try_parse_structured_data(result)
            if parsed_result is not None:
                return parsed_result

            return result

        except Exception as e:
            logger.error(f"Template resolution failed for '{template_str}': {e}")
            return template_str

    def _build_template_context(
        self,
        variables: dict[str, Any],
        outputs: dict[str, Any],
        inputs: dict[str, Any],
        system_metadata: dict[str, Any],
        namespace_manager: Optional["FlowNamespaceManager"] = None,
        derived_field_manager: Optional["DerivedFieldManager"] = None,
    ) -> dict[str, Any]:
        """Build the complete template context from all available data sources."""
        # Start with basic context (backward compatibility)
        context = {
            "variables": variables,
            "outputs": outputs,
            "inputs": inputs,
            "system": system_metadata,
            **variables,  # Make variables available at top level too
            **outputs,    # Make outputs available at top level too
        }

        # Add namespace-aware context if we have an active flow
        if namespace_manager:
            namespace_context = namespace_manager.get_namespace_context_for_templates()
            if namespace_context:
                # Overlay flow-specific data with precedence over root data
                context.update({
                    "variables": {**variables, **namespace_context["variables"]},
                    "outputs": {**outputs, **namespace_context["outputs"]},
                    "inputs": {**inputs, **namespace_context["inputs"]},
                    # Make flow-specific data available at top level too
                    **namespace_context["variables"],
                    **namespace_context["outputs"],
                })
                logger.debug(
                    f"Template resolution using namespace: {namespace_manager.get_current_flow_namespace()}"
                )

        # Add observable values for current derived field values
        if derived_field_manager:
            self._overlay_observable_values(context, derived_field_manager)

        return context

    def _overlay_observable_values(
        self, 
        context: dict[str, Any], 
        derived_field_manager: "DerivedFieldManager"
    ) -> None:
        """Overlay observable values to ensure template resolution gets current values."""
        for field_name, observable_value in derived_field_manager.observable_values.items():
            # Convert qualified field names (e.g., "knave.inventory") to template paths
            if "." in field_name:
                # Set the observable value directly in the context at the qualified path
                context[field_name] = observable_value.value
                # Debug log for inventory field
                if field_name == "knave.inventory":
                    logger.info(
                        f"Template context overlay: {field_name} = {type(observable_value.value).__name__} "
                        f"with {len(observable_value.value) if isinstance(observable_value.value, list) else 'non-list'} items"
                    )

        # Debug: check if knave.inventory is in the context and what type it is
        if "knave.inventory" in context:
            inventory_value = context["knave.inventory"]
            logger.info(f"Template context has knave.inventory: {type(inventory_value).__name__}")
            if isinstance(inventory_value, list):
                logger.info(
                    f"Inventory list has {len(inventory_value)} items: "
                    f"{[item.get('slot_cost', 'no_slot_cost') for item in inventory_value if isinstance(item, dict)]}"
                )
            else:
                logger.info(f"Inventory is not a list: {inventory_value}")

    def resolve_path_value(
        self,
        path: str,
        variables: dict[str, Any],
        outputs: dict[str, Any],
        inputs: dict[str, Any],
        default: Any = None,
    ) -> Any:
        """Resolve a path like 'outputs.character.name' to its value."""
        try:
            if path.startswith("outputs."):
                return self._get_nested_value(outputs, path[8:])  # Remove "outputs." prefix
            elif path.startswith("variables."):
                return self._get_nested_value(variables, path[10:])  # Remove "variables." prefix
            elif path.startswith("inputs."):
                return self._get_nested_value(inputs, path[7:])  # Remove "inputs." prefix
            else:
                # Try outputs first, then variables, then inputs
                try:
                    return self._get_nested_value(outputs, path)
                except (KeyError, TypeError):
                    try:
                        return self._get_nested_value(variables, path)
                    except (KeyError, TypeError):
                        return self._get_nested_value(inputs, path)
        except (KeyError, TypeError):
            return default

    def _try_parse_structured_data(self, value: str) -> Any | None:
        """Try to parse a string as structured data or numbers."""
        if not isinstance(value, str):
            return None

        value = value.strip()

        # Try to parse as JSON first if it looks like structured data
        if (
            value.startswith(("{", "[", '"'))
            or value in ("true", "false", "null")
            or value.isdigit()
        ):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        # Try to parse as number
        try:
            if "." in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Try Python literal evaluation for lists and dicts
        if (
            (value.startswith("[") and value.endswith("]"))
            or (value.startswith("{") and value.endswith("}"))
        ):
            try:
                parsed = ast.literal_eval(value)
                # Only return if it's actually structured data (list or dict)
                if isinstance(parsed, list | dict):
                    return parsed
            except (ValueError, SyntaxError):
                pass

        return None

    def _template_get_value(self, path: str, default: Any = None) -> Any:
        """Template function to get a value by path (placeholder - requires context binding)."""
        # This will be bound to the actual context when used
        return default

    def _template_has_value(self, path: str) -> bool:
        """Template function to check if a value exists (placeholder - requires context binding)."""
        # This will be bound to the actual context when used
        return False

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(".")
        current = data

        for key in keys:
            if not isinstance(current, dict) or key not in current:
                raise KeyError(f"Key '{key}' not found in path '{path}'")
            current = current[key]

        return current
