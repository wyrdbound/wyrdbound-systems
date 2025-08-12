"""Execution context models for managing runtime state."""

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from ..services.flow_execution_context_manager import (
    DefaultNamespaceDataAccess,
    FlowExecutionContextManager,
)
from ..services.path_resolver import PathResolver
from .flow_namespace import FlowNamespaceManager
from .template_resolver import TemplateResolver

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

    # Flow namespace management (delegated to specialized manager)
    namespace_manager: FlowNamespaceManager = field(
        default_factory=FlowNamespaceManager
    )

    # Execution tracking
    current_step: str | None = None
    step_history: list[str] = field(default_factory=list)
    checkpoints: dict[str, Checkpoint] = field(default_factory=dict)
    
    # Action messages for UI display
    action_messages: list[str] = field(default_factory=list)

    # Template resolution (delegated to specialized resolver)
    template_resolver: TemplateResolver = field(default_factory=TemplateResolver)

    # Path resolution (delegated to specialized resolver)
    path_resolver: PathResolver = field(default_factory=PathResolver)

    # Flow execution context management (delegated to specialized manager)
    _flow_execution_manager: FlowExecutionContextManager | None = field(
        default=None, init=False, repr=False
    )

    # Observable system for derived fields
    _derived_field_manager: Optional["DerivedFieldManager"] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize the derived field manager and flow execution manager."""
        # Initialize the derived field manager
        from .observable import DerivedFieldManager

        self._derived_field_manager = DerivedFieldManager(self, self.resolve_template)

        # Initialize the flow execution context manager
        namespace_data_access = DefaultNamespaceDataAccess(self)
        self._flow_execution_manager = FlowExecutionContextManager(
            namespace_data_access
        )

    def set_variable(self, path: str, value: Any) -> None:
        """Set a variable at the specified path."""
        self.path_resolver.set_value(self, f"variables.{path}", value)

    def get_variable(self, path: str, default: Any = None) -> Any:
        """Get a variable at the specified path."""
        return self.path_resolver.get_value(self, f"variables.{path}", default)

    def has_variable(self, path: str) -> bool:
        """Check if a variable exists at the specified path."""
        return self.path_resolver.has_value(self, f"variables.{path}")

    def set_output(self, path: str, value: Any) -> None:
        """Set an output at the specified path, triggering derived field computation if applicable."""
        self.path_resolver.set_value(self, f"outputs.{path}", value)

    def set_output_with_observables(self, path: str, value: Any) -> None:
        """Set an output and trigger observable updates."""
        # This is now redundant since set_output always handles observables
        self.set_output(path, value)

    def get_output(self, path: str, default: Any = None) -> Any:
        """Get an output at the specified path, including computed derived fields."""
        try:
            base_value = self.path_resolver.get_value(self, f"outputs.{path}")
            logger.debug(f"get_output({path}): base_value = {base_value}")

            # If we have a derived field manager and this looks like a model instance,
            # try to merge in the computed derived fields
            if self._derived_field_manager and isinstance(base_value, dict):
                logger.debug(f"get_output({path}): checking for computed values")
                # Check if this path corresponds to a model instance
                # For paths like "knave", check if we have derived fields for that instance
                computed_values = (
                    self._derived_field_manager.get_computed_values_for_instance(path)
                )
                logger.debug(f"get_output({path}): computed_values = {computed_values}")
                if computed_values:
                    # Deep merge the computed values into the base value
                    merged_value = self._deep_merge_dicts(
                        base_value.copy(), computed_values
                    )
                    logger.debug(f"get_output({path}): merged_value = {merged_value}")
                    return merged_value

            return base_value
        except Exception:
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
        self.path_resolver.set_value(self, f"inputs.{path}", value)

    def get_input(self, path: str, default: Any = None) -> Any:
        """Get an input at the specified path."""
        return self.path_resolver.get_value(self, f"inputs.{path}", default)

    def resolve_template(self, template_str: str) -> Any:
        """Resolve a Jinja2 template string with current context."""
        return self.template_resolver.resolve_template(
            template_str,
            self.variables,
            self.outputs,
            self.inputs,
            self.system_metadata,
            self.namespace_manager,
            self._derived_field_manager,
        )

    def resolve_template_with_context(
        self, template_str: str, additional_context: dict[str, Any]
    ) -> Any:
        """Resolve a template string with additional context variables."""
        # Merge additional context with existing context
        merged_variables = {**self.variables, **additional_context}
        merged_outputs = {**self.outputs}
        merged_inputs = {**self.inputs}

        # If additional_context has variables/outputs/inputs, merge those too
        if "variables" in additional_context:
            merged_variables.update(additional_context["variables"])
        if "outputs" in additional_context:
            merged_outputs.update(additional_context["outputs"])
        if "inputs" in additional_context:
            merged_inputs.update(additional_context["inputs"])

        return self.template_resolver.resolve_template(
            template_str,
            merged_variables,
            merged_outputs,
            merged_inputs,
            self.system_metadata,
            self.namespace_manager,
            self._derived_field_manager,
        )

    def resolve_path_value(self, path: str) -> Any:
        """Resolve a path that might reference variables, outputs, inputs, or system metadata."""
        logger.debug(f"resolve_path_value({path})")

        # Use the centralized path resolver
        try:
            return self.path_resolver.get_value(self, path)
        except Exception as e:
            raise KeyError(f"Path '{path}' not found: {e}") from e

    # Flow Namespace Management (delegated to namespace manager)
    def create_flow_namespace(
        self, namespace_id: str, flow_id: str, execution_id: str
    ) -> None:
        """Create an isolated namespace for flow execution."""
        self.namespace_manager.create_flow_namespace(
            namespace_id, flow_id, execution_id
        )

    def set_current_flow_namespace(self, namespace_id: str) -> None:
        """Set the current active flow namespace."""
        self.namespace_manager.set_current_flow_namespace(namespace_id)

    def pop_flow_namespace(self) -> str | None:
        """Pop the current flow namespace from the execution stack."""
        return self.namespace_manager.pop_flow_namespace()

    def get_current_flow_namespace(self) -> str | None:
        """Get the current active flow namespace ID."""
        return self.namespace_manager.get_current_flow_namespace()

    def set_namespaced_value(self, full_path: str, value: Any) -> None:
        """Set a value using full namespaced path (e.g., 'flow_abc123.outputs.character.name')."""
        self.namespace_manager.set_namespaced_value(full_path, value)

    def get_namespaced_value(self, full_path: str, default: Any = None) -> Any:
        """Get a value using full namespaced path."""
        return self.namespace_manager.get_namespaced_value(full_path, default)

    def copy_flow_outputs_to_root(self, namespace_id: str) -> None:
        """Copy flow outputs from namespace to root level after completion."""
        self.namespace_manager.copy_flow_outputs_to_root(namespace_id, self.outputs)

    def initialize_flow_namespace_variables(
        self, namespace_id: str, variables: dict[str, Any]
    ) -> None:
        """Initialize variables in a flow namespace."""
        self.namespace_manager.initialize_flow_namespace_variables(
            namespace_id, variables
        )

    def get_flow_namespace_data(self, namespace_id: str) -> dict[str, Any] | None:
        """Get all data for a specific flow namespace."""
        return self.namespace_manager.get_flow_namespace_data(namespace_id)

    # Flow Execution Management (delegated to specialized manager)
    def start_flow_execution(
        self, flow_id: str, variables: dict[str, Any] | None = None
    ):
        """Start a new flow execution with proper context management."""
        if self._flow_execution_manager:
            return self._flow_execution_manager.start_flow_execution(flow_id, variables)
        else:
            # Fallback to legacy method for backward compatibility
            return self.create_flow_namespace(f"flow_{flow_id}", flow_id, "legacy")

    def end_flow_execution(self):
        """End the current flow execution and clean up resources."""
        if self._flow_execution_manager:
            return self._flow_execution_manager.end_flow_execution()
        else:
            # Fallback to legacy method
            return self.pop_flow_namespace()

    def update_execution_step(self, step_id: str) -> None:
        """Update the current step in the execution context."""
        self.current_step = step_id
        self.step_history.append(step_id)

        if self._flow_execution_manager:
            self._flow_execution_manager.update_execution_step(step_id)

    def get_current_execution(self):
        """Get the current flow execution state."""
        if self._flow_execution_manager:
            return self._flow_execution_manager.get_current_execution()
        return None

    def is_execution_active(self) -> bool:
        """Check if a flow execution is currently active."""
        if self._flow_execution_manager:
            return self._flow_execution_manager.is_execution_active()
        return False

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

    def add_action_message(self, message: str) -> None:
        """Add an action message to be displayed by the UI."""
        self.action_messages.append(message)

    def get_and_clear_action_messages(self) -> list[str]:
        """Get all action messages and clear the list."""
        messages = self.action_messages.copy()
        self.action_messages.clear()
        return messages

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
