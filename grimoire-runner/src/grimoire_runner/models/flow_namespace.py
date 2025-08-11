"""Flow namespace management for execution context isolation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FlowNamespaceManager:
    """Manages flow execution namespaces for context isolation."""

    def __init__(self):
        self.flow_namespaces: dict[str, dict[str, Any]] = {}
        self.current_flow_namespace: str | None = None
        self.flow_execution_stack: list[str] = []

    def create_flow_namespace(
        self, namespace_id: str, flow_id: str, execution_id: str
    ) -> None:
        """Create a new flow namespace for isolated execution."""
        self.flow_namespaces[namespace_id] = {
            "flow_id": flow_id,
            "execution_id": execution_id,
            "variables": {},
            "outputs": {},
            "inputs": {},
            "created": True,
        }
        logger.debug(f"Created flow namespace: {namespace_id} for flow: {flow_id}")

    def set_current_flow_namespace(self, namespace_id: str) -> None:
        """Set the current active flow namespace."""
        if namespace_id not in self.flow_namespaces:
            raise ValueError(f"Flow namespace '{namespace_id}' does not exist")

        self.current_flow_namespace = namespace_id
        self.flow_execution_stack.append(namespace_id)
        logger.debug(f"Set current flow namespace to: {namespace_id}")

    def pop_flow_namespace(self) -> str | None:
        """Pop the current flow namespace and return to the previous one."""
        if not self.flow_execution_stack:
            self.current_flow_namespace = None
            return None

        popped_namespace = self.flow_execution_stack.pop()
        self.current_flow_namespace = (
            self.flow_execution_stack[-1] if self.flow_execution_stack else None
        )

        logger.debug(
            f"Popped flow namespace: {popped_namespace}, current: {self.current_flow_namespace}"
        )
        return popped_namespace

    def get_current_flow_namespace(self) -> str | None:
        """Get the current active flow namespace ID."""
        return self.current_flow_namespace

    def has_namespace(self, namespace_id: str) -> bool:
        """Check if a namespace exists."""
        return namespace_id in self.flow_namespaces

    def get_namespace_data(self, namespace_id: str) -> dict[str, Any] | None:
        """Get all data for a specific namespace."""
        return self.flow_namespaces.get(namespace_id)

    def get_current_namespace_data(self) -> dict[str, Any] | None:
        """Get data for the current active namespace."""
        if not self.current_flow_namespace:
            return None
        return self.flow_namespaces.get(self.current_flow_namespace)

    def set_namespaced_value(self, full_path: str, value: Any) -> None:
        """Set a value in a specific namespace using a full path like 'namespace.category.key'."""
        parts = full_path.split(".", 2)
        if len(parts) != 3:
            raise ValueError(f"Invalid namespaced path format: {full_path}")

        namespace_id, category, key_path = parts

        if namespace_id not in self.flow_namespaces:
            raise ValueError(f"Flow namespace '{namespace_id}' does not exist")

        if category not in ["variables", "outputs", "inputs"]:
            raise ValueError(
                f"Invalid category '{category}'. Must be variables, outputs, or inputs"
            )

        namespace_data = self.flow_namespaces[namespace_id][category]
        self._set_nested_value(namespace_data, key_path, value)
        logger.debug(f"Set namespaced value: {full_path} = {value}")

    def get_namespaced_value(self, full_path: str, default: Any = None) -> Any:
        """Get a value from a specific namespace using a full path."""
        parts = full_path.split(".", 2)
        if len(parts) != 3:
            return default

        namespace_id, category, key_path = parts

        if namespace_id not in self.flow_namespaces:
            return default

        if category not in ["variables", "outputs", "inputs"]:
            return default

        namespace_data = self.flow_namespaces[namespace_id].get(category, {})
        try:
            return self._get_nested_value(namespace_data, key_path)
        except (KeyError, TypeError):
            return default

    def initialize_flow_namespace_variables(
        self, namespace_id: str, variables: dict[str, Any]
    ) -> None:
        """Initialize variables for a flow namespace."""
        if namespace_id not in self.flow_namespaces:
            raise ValueError(f"Flow namespace '{namespace_id}' does not exist")

        # Handle both new list format (VariableDefinition objects) and old dict format
        if isinstance(variables, list):
            # New format: list of VariableDefinition objects
            # Convert to dictionary for internal storage
            variables_dict = {}
            for var_def in variables:
                if hasattr(var_def, "id") and hasattr(var_def, "default"):
                    # VariableDefinition object
                    variables_dict[var_def.id] = var_def.default
                elif isinstance(var_def, dict):
                    # Convert dict representation to proper format
                    var_id = var_def.get("id")
                    if var_id:
                        # Use default value if provided, otherwise use appropriate default based on type
                        default_value = var_def.get("default", "")
                        if var_def.get("type") == "bool":
                            default_value = var_def.get("default", False)
                        elif var_def.get("type") in ["int", "number"]:
                            default_value = var_def.get("default", 0)
                        elif var_def.get("type") == "list":
                            default_value = var_def.get("default", [])
                        elif var_def.get("type") == "dict":
                            default_value = var_def.get("default", {})
                        variables_dict[var_id] = default_value
                    else:
                        raise ValueError(
                            f"Variable definition missing 'id' field: {var_def}"
                        )
                else:
                    raise TypeError(
                        f"Expected variable definition to be a VariableDefinition object or dict, got {type(var_def).__name__}: {var_def}"
                    )

            variables = variables_dict
        elif isinstance(variables, dict):
            # Old format: dictionary mapping variable names to values - still supported for now
            pass
        else:
            # Invalid format
            actual_type = type(variables).__name__
            raise TypeError(
                f"Expected variables to be a list of VariableDefinition objects or a dictionary, but got {actual_type}. "
                f"Variables should use the new list format like inputs/outputs:\n"
                f'variables:\n  - id: variable_name\n    type: string\n    default: "value"\n'
                f"Actual value: {variables}"
            )

        self.flow_namespaces[namespace_id]["variables"] = variables.copy()
        logger.debug(
            f"Initialized variables for namespace {namespace_id}: {list(variables.keys())}"
        )

    def copy_flow_outputs_to_root(
        self, namespace_id: str, root_outputs: dict[str, Any]
    ) -> None:
        """Copy flow outputs from namespace to root level."""
        if namespace_id not in self.flow_namespaces:
            logger.warning(f"Cannot copy outputs: namespace '{namespace_id}' not found")
            return

        namespace_outputs = self.flow_namespaces[namespace_id].get("outputs", {})

        # Deep copy the outputs to avoid reference issues
        import copy

        for output_id, output_value in namespace_outputs.items():
            root_outputs[output_id] = copy.deepcopy(output_value)
            logger.debug(
                f"Copied output to root: {output_id} = {type(output_value).__name__}"
            )

    def get_flow_namespace_data(self, namespace_id: str) -> dict[str, Any] | None:
        """Get the complete data for a flow namespace."""
        return self.flow_namespaces.get(namespace_id)

    def cleanup_namespace(self, namespace_id: str) -> None:
        """Clean up a specific namespace (remove it from memory)."""
        if namespace_id in self.flow_namespaces:
            del self.flow_namespaces[namespace_id]
            logger.debug(f"Cleaned up namespace: {namespace_id}")

    def get_namespace_context_for_templates(self) -> dict[str, Any]:
        """Get the current namespace context for template resolution."""
        if (
            not self.current_flow_namespace
            or self.current_flow_namespace not in self.flow_namespaces
        ):
            return {}

        flow_data = self.flow_namespaces[self.current_flow_namespace]
        return {
            "variables": flow_data.get("variables", {}),
            "outputs": flow_data.get("outputs", {}),
            "inputs": flow_data.get("inputs", {}),
        }

    def _set_nested_value(self, data: dict, path: str, value: Any) -> None:
        """Set a nested value in a dictionary using dot notation."""
        keys = path.split(".")
        current = data

        # Navigate to the parent of the target key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # Set the final value
        current[keys[-1]] = value

    def _get_nested_value(self, data: dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(".")
        current = data

        for key in keys:
            if not isinstance(current, dict) or key not in current:
                raise KeyError(f"Key '{key}' not found in path '{path}'")
            current = current[key]

        return current
