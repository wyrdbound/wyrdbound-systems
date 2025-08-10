"""Template resolution for execution context."""

import logging
from typing import TYPE_CHECKING, Any, Optional

from ..services.template_service import TemplateService

if TYPE_CHECKING:
    from .flow_namespace import FlowNamespaceManager
    from .observable import DerivedFieldManager

logger = logging.getLogger(__name__)


class TemplateResolver:
    """Handles template resolution with context data integration."""

    def __init__(self):
        self._template_service = TemplateService()
        self._current_context_resolver = None

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
        if not self._template_service.is_template(template_str):
            return template_str

        # Build template context
        context = self._build_template_context(
            variables,
            outputs,
            inputs,
            system_metadata,
            namespace_manager,
            derived_field_manager,
        )

        # Store context resolver for template functions
        self._current_context_resolver = self._create_context_resolver(
            variables, outputs, inputs, namespace_manager, derived_field_manager
        )

        # Set up template functions that need access to the context
        runtime_strategy = self._template_service.get_strategy("runtime")
        if hasattr(runtime_strategy, "_template_get_value"):
            runtime_strategy._template_get_value = self._template_get_value
        if hasattr(runtime_strategy, "_template_has_value"):
            runtime_strategy._template_has_value = self._template_has_value

        try:
            return self._template_service.resolve_template(
                template_str, context, "runtime"
            )
        finally:
            # Clean up context resolver
            self._current_context_resolver = None

    def _create_context_resolver(
        self,
        variables: dict[str, Any],
        outputs: dict[str, Any],
        inputs: dict[str, Any],
        namespace_manager: Optional["FlowNamespaceManager"] = None,
        derived_field_manager: Optional["DerivedFieldManager"] = None,
    ):
        """Create a context resolver function for template functions."""

        def resolve_path(path: str, default: Any = None) -> Any:
            """Resolve a path that might reference variables, outputs, or inputs."""
            logger.debug(f"resolve_path_value({path})")
            if path.startswith("variables."):
                return self._get_nested_value(variables, path[10:], default)
            elif path.startswith("outputs."):
                return self._get_nested_value(outputs, path[8:], default)
            elif path.startswith("inputs."):
                return self._get_nested_value(inputs, path[7:], default)
            else:
                # Try all contexts
                for context in [variables, outputs, inputs]:
                    try:
                        return self._get_nested_value(context, path, default)
                    except (KeyError, TypeError):
                        continue

                # Try namespace manager if available
                if namespace_manager:
                    try:
                        return namespace_manager.get_namespaced_value(path, default)
                    except (KeyError, TypeError):
                        pass

                return default

        return resolve_path

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
            **outputs,  # Make outputs available at top level too
        }

        # Add input instances directly to the context for observable system
        # This ensures that model instances in inputs are available for derived field computation
        flow_inputs = inputs
        if namespace_manager:
            namespace_context = namespace_manager.get_namespace_context_for_templates()
            if namespace_context:
                flow_inputs = {**inputs, **namespace_context["inputs"]}

        # Make model instances from inputs available at their expected paths
        # This is crucial for the observable system to compute derived fields correctly
        for input_key, input_value in flow_inputs.items():
            if isinstance(input_value, dict):
                # Add the input model instance directly to context (e.g., inputs.character -> character)
                # But we need to ensure we're providing the fully resolved data structure
                # If the input value contains template strings, we should resolve them first
                resolved_input = self._resolve_template_fields_in_dict(
                    input_value, context
                )
                context[input_key] = resolved_input
                logger.debug(
                    f"Made input model '{input_key}' available for observable system"
                )

        # Add namespace-aware context if we have an active flow
        if namespace_manager:
            namespace_context = namespace_manager.get_namespace_context_for_templates()
            if namespace_context:
                # Overlay flow-specific data with precedence over root data
                context.update(
                    {
                        "variables": {**variables, **namespace_context["variables"]},
                        "outputs": {**outputs, **namespace_context["outputs"]},
                        "inputs": {**inputs, **namespace_context["inputs"]},
                        # Make flow-specific data available at top level too
                        **namespace_context["variables"],
                        **namespace_context["outputs"],
                    }
                )
                logger.debug(
                    f"Template resolution using namespace: {namespace_manager.get_current_flow_namespace()}"
                )

        # Add observable values for current derived field values
        if derived_field_manager:
            self._overlay_observable_values(context, derived_field_manager)

        return context

    def _overlay_observable_values(
        self, context: dict[str, Any], derived_field_manager: "DerivedFieldManager"
    ) -> None:
        """Overlay observable values to ensure template resolution gets current values."""
        for (
            field_name,
            observable_value,
        ) in derived_field_manager.observable_values.items():
            # Convert qualified field names (e.g., "knave.inventory") to template paths
            if "." in field_name:
                # Set the observable value directly in the context at the qualified path
                context[field_name] = observable_value.value

                # Debug log for inventory field
                if field_name == "knave.inventory":
                    logger.debug(
                        f"Template context overlay: {field_name} = {type(observable_value.value).__name__} "
                        f"with {len(observable_value.value) if isinstance(observable_value.value, list) else 'non-list'} items"
                    )

        # Debug: check if knave.inventory is in the context and what type it is
        if "knave.inventory" in context:
            inventory_value = context["knave.inventory"]
            logger.debug(
                f"Template context has knave.inventory: {type(inventory_value).__name__}"
            )
            if isinstance(inventory_value, list):
                logger.debug(f"Inventory has {len(inventory_value)} items")
            else:
                logger.debug(f"Inventory is not a list: {inventory_value}")

    def _resolve_template_fields_in_dict(
        self, data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively resolve any template strings in a dictionary structure."""
        import copy

        result = copy.deepcopy(data)

        def resolve_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    obj[key] = resolve_recursive(value)
                return obj
            elif isinstance(obj, list):
                return [resolve_recursive(item) for item in obj]
            elif isinstance(obj, str) and self._template_service.is_template(obj):
                try:
                    # Resolve the template string using the current context
                    resolved = self._template_service.resolve_template(obj, context)
                    logger.debug(f"Resolved template field: {obj} -> {resolved}")
                    return resolved
                except Exception as e:
                    logger.warning(f"Failed to resolve template field '{obj}': {e}")
                    return obj
            else:
                return obj

        return resolve_recursive(result)

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
                return self._get_nested_value(
                    outputs, path[8:]
                )  # Remove "outputs." prefix
            elif path.startswith("variables."):
                return self._get_nested_value(
                    variables, path[10:]
                )  # Remove "variables." prefix
            elif path.startswith("inputs."):
                return self._get_nested_value(
                    inputs, path[7:]
                )  # Remove "inputs." prefix
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

    def _template_get_value(self, path: str, default: Any = None) -> Any:
        """Template function to get a value by path."""
        if self._current_context_resolver:
            return self._current_context_resolver(path, default)
        return default

    def _template_has_value(self, path: str) -> bool:
        """Template function to check if a value exists."""
        if self._current_context_resolver:
            try:
                result = self._current_context_resolver(path, None)
                return result is not None
            except (KeyError, TypeError):
                return False
        return False

    def _get_nested_value(self, data: dict, path: str, default: Any = None) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        try:
            keys = path.split(".")
            current = data

            for key in keys:
                if not isinstance(current, dict) or key not in current:
                    if default is not None:
                        return default
                    raise KeyError(f"Key '{key}' not found in path '{path}'")
                current = current[key]

            return current
        except (KeyError, TypeError):
            if default is not None:
                return default
            raise
