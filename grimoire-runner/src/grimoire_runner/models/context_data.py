"""Execution context models for managing runtime state."""

import copy
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from jinja2 import Environment, StrictUndefined

if TYPE_CHECKING:
    from .observable import DerivedFieldManager

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """A saved state checkpoint for rollback."""

    id: str
    timestamp: datetime
    variables: dict[str, Any]
    outputs: dict[str, Any]
    current_step: str | None = None


@dataclass
class ExecutionContext:
    """Runtime execution context for flows."""

    # Core state
    variables: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)

    # System metadata for templating
    system_metadata: dict[str, Any] = field(default_factory=dict)

    # Flow namespace isolation
    flow_namespaces: dict[str, dict[str, Any]] = field(default_factory=dict)
    current_flow_namespace: str | None = None
    flow_execution_stack: list[str] = field(default_factory=list)

    # Execution tracking
    current_step: str | None = None
    step_history: list[str] = field(default_factory=list)
    checkpoints: dict[str, Checkpoint] = field(default_factory=dict)

    # Template environment
    _jinja_env: Environment = field(
        default_factory=lambda: Environment(undefined=StrictUndefined),
        init=False,
        repr=False,
    )

    # Observable system for derived fields
    _derived_field_manager: Optional["DerivedFieldManager"] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize the template environment with custom functions."""
        self._jinja_env.globals.update(
            {
                "get_value": self.get_variable,
                "has_value": self.has_variable,
            }
        )

        # Initialize the derived field manager
        from .observable import DerivedFieldManager

        self._derived_field_manager = DerivedFieldManager(self, self.resolve_template)

    def set_variable(self, path: str, value: Any) -> None:
        """Set a variable at the specified path."""
        self._set_nested_value(self.variables, path, value)

    def get_variable(self, path: str, default: Any = None) -> Any:
        """Get a variable at the specified path."""
        try:
            return self._get_nested_value(self.variables, path)
        except (KeyError, TypeError):
            return default

    def has_variable(self, path: str) -> bool:
        """Check if a variable exists at the specified path."""
        try:
            self._get_nested_value(self.variables, path)
            return True
        except (KeyError, TypeError):
            return False

    def set_output(self, path: str, value: Any) -> None:
        """Set an output at the specified path, triggering derived field computation if applicable."""
        # Always use the observable system for consistency and to trigger derived fields
        if self._derived_field_manager:
            self._derived_field_manager.set_field_value(path, value)
        else:
            # Fallback if no derived field manager (shouldn't happen in normal operation)
            self._set_nested_value(self.outputs, path, value)

    def set_output_with_observables(self, path: str, value: Any) -> None:
        """Set an output and trigger observable updates."""
        # This is now redundant since set_output always handles observables
        self.set_output(path, value)

    def get_output(self, path: str, default: Any = None) -> Any:
        """Get an output at the specified path, including computed derived fields."""
        try:
            base_value = self._get_nested_value(self.outputs, path)
            logger.info(f"get_output({path}): base_value = {base_value}")

            # If we have a derived field manager and this looks like a model instance,
            # try to merge in the computed derived fields
            if self._derived_field_manager and isinstance(base_value, dict):
                logger.info(f"get_output({path}): checking for computed values")
                # Check if this path corresponds to a model instance
                # For paths like "knave", check if we have derived fields for that instance
                computed_values = (
                    self._derived_field_manager.get_computed_values_for_instance(path)
                )
                logger.info(f"get_output({path}): computed_values = {computed_values}")
                if computed_values:
                    # Deep merge the computed values into the base value
                    merged_value = self._deep_merge_dicts(
                        base_value.copy(), computed_values
                    )
                    logger.info(f"get_output({path}): merged_value = {merged_value}")
                    return merged_value

            return base_value
        except (KeyError, TypeError):
            return default

    def _deep_merge_dicts(self, base: dict, overlay: dict) -> dict:
        """Deep merge two dictionaries, with overlay values taking precedence.

        Special handling: If both values are strings but one looks like serialized
        structured data, attempt to parse and use the structured version.
        """
        result = base.copy()

        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge_dicts(result[key], value)
            elif (
                key in result
                and isinstance(result[key], str)
                and isinstance(value, str)
            ):
                # Both are strings - check if either looks like serialized structured data
                base_parsed = self._try_parse_structured_data(result[key])
                overlay_parsed = self._try_parse_structured_data(value)

                # Use structured data if available, preferring overlay
                if overlay_parsed is not None:
                    result[key] = overlay_parsed
                elif base_parsed is not None:
                    result[key] = base_parsed
                else:
                    result[key] = value  # Use overlay string value
            else:
                result[key] = value

        return result

    def _try_parse_structured_data(self, value: str) -> Any:
        """Try to parse a string as structured data. Returns None if not valid."""
        if not isinstance(value, str):
            return None

        # Only try parsing if it looks like structured data
        if not (
            value.strip().startswith(("[", "{")) and value.strip().endswith(("]", "}"))
        ):
            return None

        # Try JSON first (double quotes)
        try:
            import json

            parsed = json.loads(value)
            # Only return if it's actually structured data (list or dict)
            if isinstance(parsed, list | dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Try Python literal evaluation (single quotes)
        try:
            import ast

            parsed = ast.literal_eval(value)
            # Only return if it's actually structured data (list or dict)
            if isinstance(parsed, list | dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

        return None

    def set_input(self, path: str, value: Any) -> None:
        """Set an input at the specified path."""
        self._set_nested_value(self.inputs, path, value)

    def get_input(self, path: str, default: Any = None) -> Any:
        """Get an input at the specified path."""
        try:
            return self._get_nested_value(self.inputs, path)
        except (KeyError, TypeError):
            return default

    def resolve_template(self, template_str: str) -> Any:
        """Resolve a Jinja2 template string with current context."""
        if not isinstance(template_str, str):
            return template_str

        # Skip if no template syntax
        if "{{" not in template_str and "{%" not in template_str:
            return template_str

        try:
            template = self._jinja_env.from_string(template_str)

            # Start with basic context (backward compatibility)
            context = {
                "variables": self.variables,
                "outputs": self.outputs,
                "inputs": self.inputs,
                "system": self.system_metadata,  # Make system metadata available
                **self.variables,  # Make variables available at top level too
                **self.outputs,  # Make outputs available at top level too
            }

            # Add namespace-aware context if we have an active flow
            if self.current_flow_namespace and self.current_flow_namespace in self.flow_namespaces:
                flow_data = self.flow_namespaces[self.current_flow_namespace]
                # Overlay flow-specific data with precedence over root data
                context.update({
                    "variables": {**self.variables, **flow_data["variables"]},
                    "outputs": {**self.outputs, **flow_data["outputs"]},
                    "inputs": {**self.inputs, **flow_data["inputs"]},
                    # Make flow-specific data available at top level too
                    **flow_data["variables"],
                    **flow_data["outputs"],
                })
                logger.debug(f"Template resolution using namespace: {self.current_flow_namespace}")

            # If we have a derived field manager, overlay observable values to ensure
            # template resolution gets the most current values (including lists, not strings)
            if self._derived_field_manager:
                for (
                    field_name,
                    observable_value,
                ) in self._derived_field_manager.observable_values.items():
                    # Convert qualified field names (e.g., "knave.inventory") to template paths
                    if "." in field_name:
                        # Set the observable value directly in the context at the qualified path
                        context[field_name] = observable_value.value
                        # Debug log for inventory field
                        if field_name == "knave.inventory":
                            logger.info(
                                f"Template context overlay: {field_name} = {type(observable_value.value).__name__} with {len(observable_value.value) if isinstance(observable_value.value, list) else 'non-list'} items"
                            )

            # Debug: check if knave.inventory is in the context and what type it is
            if "knave.inventory" in context:
                inventory_value = context["knave.inventory"]
                logger.info(
                    f"Template context has knave.inventory: {type(inventory_value).__name__}"
                )
                if isinstance(inventory_value, list):
                    logger.info(
                        f"Inventory list has {len(inventory_value)} items: {[item.get('slot_cost', 'no_slot_cost') for item in inventory_value if isinstance(item, dict)]}"
                    )
                else:
                    logger.info(f"Inventory is not a list: {inventory_value}")

            logger.debug(f"Template context for '{template_str}': {context}")
            result = template.render(context)

            # Try to parse as JSON if it looks like structured data
            result = result.strip()
            if (
                result.startswith(("{", "[", '"'))
                or result in ("true", "false", "null")
                or result.isdigit()
            ):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    pass

            # Try to parse as number
            try:
                if "." in result:
                    return float(result)
                else:
                    return int(result)
            except ValueError:
                pass

            return result

        except Exception as e:
            raise ValueError(f"Template resolution failed: {e}") from e

    def resolve_path_value(self, path: str) -> Any:
        """Resolve a path that might reference variables, outputs, or inputs."""
        logger.info(f"resolve_path_value({path})")
        if path.startswith("variables."):
            return self.get_variable(path[10:])  # Remove 'variables.' prefix
        elif path.startswith("outputs."):
            return self.get_output(path[8:])  # Remove 'outputs.' prefix
        elif path.startswith("inputs."):
            return self.get_input(path[7:])  # Remove 'inputs.' prefix
        else:
            # Try all contexts
            for _context_name, context in [
                ("variables", self.variables),
                ("outputs", self.outputs),
                ("inputs", self.inputs),
            ]:
                try:
                    return self._get_nested_value(context, path)
                except (KeyError, TypeError):
                    continue

            raise KeyError(f"Path '{path}' not found in any context")

    # Flow Namespace Management
    def create_flow_namespace(self, namespace_id: str, flow_id: str, execution_id: str) -> None:
        """Create an isolated namespace for flow execution."""
        self.flow_namespaces[namespace_id] = {
            "inputs": {},
            "outputs": {},
            "variables": {},
            "metadata": {
                "flow_id": flow_id,
                "execution_id": execution_id,
                "created_at": datetime.now().isoformat()
            }
        }
        logger.info(f"Created flow namespace: {namespace_id} for flow {flow_id}")

    def set_current_flow_namespace(self, namespace_id: str) -> None:
        """Set the current active flow namespace."""
        if namespace_id not in self.flow_namespaces:
            raise ValueError(f"Flow namespace '{namespace_id}' does not exist")

        self.current_flow_namespace = namespace_id
        if namespace_id not in self.flow_execution_stack:
            self.flow_execution_stack.append(namespace_id)

        logger.info(f"Set current flow namespace to: {namespace_id}")

    def pop_flow_namespace(self) -> str | None:
        """Pop the current flow namespace from the execution stack."""
        if not self.flow_execution_stack:
            return None

        popped_namespace = self.flow_execution_stack.pop()
        self.current_flow_namespace = (
            self.flow_execution_stack[-1] if self.flow_execution_stack else None
        )

        logger.info(f"Popped flow namespace: {popped_namespace}, current: {self.current_flow_namespace}")
        return popped_namespace

    def get_current_flow_namespace(self) -> str | None:
        """Get the current active flow namespace ID."""
        return self.current_flow_namespace

    def set_namespaced_value(self, full_path: str, value: Any) -> None:
        """Set a value using full namespaced path (e.g., 'flow_abc123.outputs.character.name')."""
        parts = full_path.split(".", 2)  # Split into namespace, category, path
        if len(parts) < 3:
            raise ValueError(f"Invalid namespaced path: {full_path}. Expected format: namespace.category.path")

        namespace_id, category, path = parts

        if namespace_id not in self.flow_namespaces:
            raise ValueError(f"Flow namespace '{namespace_id}' does not exist")

        if category not in ["inputs", "outputs", "variables"]:
            raise ValueError(f"Invalid category '{category}'. Must be inputs, outputs, or variables")

        namespace_data = self.flow_namespaces[namespace_id][category]
        self._set_nested_value(namespace_data, path, value)

        logger.info(f"Set namespaced value: {full_path} = {value}")

    def get_namespaced_value(self, full_path: str, default: Any = None) -> Any:
        """Get a value using full namespaced path."""
        try:
            parts = full_path.split(".", 2)
            if len(parts) < 3:
                return default

            namespace_id, category, path = parts

            if namespace_id not in self.flow_namespaces:
                return default

            if category not in ["inputs", "outputs", "variables"]:
                return default

            namespace_data = self.flow_namespaces[namespace_id][category]
            return self._get_nested_value(namespace_data, path)
        except (KeyError, TypeError):
            return default

    def copy_flow_outputs_to_root(self, namespace_id: str) -> None:
        """Copy flow outputs from namespace to root level after completion."""
        if namespace_id not in self.flow_namespaces:
            logger.warning(f"Cannot copy outputs: namespace '{namespace_id}' not found")
            return

        flow_outputs = self.flow_namespaces[namespace_id]["outputs"]

        # Deep copy the outputs to avoid reference issues
        for output_id, output_value in flow_outputs.items():
            self.set_output(output_id, copy.deepcopy(output_value))
            logger.info(f"Copied flow output to root: {output_id} = {type(output_value).__name__}")

    def initialize_flow_namespace_variables(self, namespace_id: str, variables: dict[str, Any]) -> None:
        """Initialize variables in a flow namespace."""
        if namespace_id not in self.flow_namespaces:
            raise ValueError(f"Flow namespace '{namespace_id}' does not exist")

        self.flow_namespaces[namespace_id]["variables"].update(variables)
        logger.info(f"Initialized {len(variables)} variables in namespace {namespace_id}")

    def get_flow_namespace_data(self, namespace_id: str) -> dict[str, Any] | None:
        """Get all data for a specific flow namespace."""
        return self.flow_namespaces.get(namespace_id)

    # Checkpoint and state management
    def create_checkpoint(self, checkpoint_id: str | None = None) -> str:
        """Create a checkpoint for rollback."""
        if checkpoint_id is None:
            checkpoint_id = f"checkpoint_{len(self.checkpoints)}"

        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=datetime.now(),
            variables=copy.deepcopy(self.variables),
            outputs=copy.deepcopy(self.outputs),
            current_step=self.current_step,
        )

        self.checkpoints[checkpoint_id] = checkpoint
        return checkpoint_id

    def restore_checkpoint(self, checkpoint_id: str) -> None:
        """Restore state from a checkpoint."""
        if checkpoint_id not in self.checkpoints:
            raise KeyError(f"Checkpoint '{checkpoint_id}' not found")

        checkpoint = self.checkpoints[checkpoint_id]
        self.variables = copy.deepcopy(checkpoint.variables)
        self.outputs = copy.deepcopy(checkpoint.outputs)
        self.current_step = checkpoint.current_step

    def list_checkpoints(self) -> list[str]:
        """Get a list of available checkpoint IDs."""
        return list(self.checkpoints.keys())

    def get_state_snapshot(self) -> dict[str, Any]:
        """Get a complete snapshot of the current state."""
        return {
            "variables": copy.deepcopy(self.variables),
            "outputs": copy.deepcopy(self.outputs),
            "inputs": copy.deepcopy(self.inputs),
            "current_step": self.current_step,
            "step_history": self.step_history.copy(),
            "timestamp": datetime.now().isoformat(),
        }

    def initialize_model_observables(
        self, model_definition, instance_id: str = None
    ) -> None:
        """Initialize observable derived fields from a model definition."""
        if self._derived_field_manager:
            self._derived_field_manager.initialize_from_model(
                model_definition, instance_id
            )

    def compute_derived_fields(self) -> None:
        """Compute all derived fields in the model."""
        if self._derived_field_manager:
            self._derived_field_manager.compute_all_derived_fields()

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """Get a nested value by dot-separated path."""
        if not path:
            return obj

        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path '{path}' not found")

        return current

    def _set_nested_value(self, obj: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value by dot-separated path, creating intermediate dicts as needed."""
        if not path:
            raise ValueError("Path cannot be empty")

        parts = path.split(".")
        current = obj

        # Navigate to parent of target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise ValueError(f"Cannot set nested value: '{part}' is not a dict")
            current = current[part]

        # Set the final value
        current[parts[-1]] = value
