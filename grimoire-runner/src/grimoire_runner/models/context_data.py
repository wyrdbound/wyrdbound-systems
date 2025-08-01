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
        """Set an output at the specified path."""
        self._set_nested_value(self.outputs, path, value)

    def set_output_with_observables(self, path: str, value: Any) -> None:
        """Set an output and trigger observable updates."""
        self.set_output(path, value)

        # If we have a derived field manager, also update the observable system
        if self._derived_field_manager:
            self._derived_field_manager.set_field_value(path, value)

    def get_output(self, path: str, default: Any = None) -> Any:
        """Get an output at the specified path."""
        try:
            return self._get_nested_value(self.outputs, path)
        except (KeyError, TypeError):
            return default

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
            context = {
                "variables": self.variables,
                "outputs": self.outputs,
                "inputs": self.inputs,
                "system": self.system_metadata,  # Make system metadata available
                **self.variables,  # Make variables available at top level too
                **self.outputs,  # Make outputs available at top level too
            }
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

    def set_observable_output(self, path: str, value: Any) -> None:
        """Set an output value that will trigger derived field recalculation."""
        if self._derived_field_manager:
            self._derived_field_manager.set_field_value(path, value)
        else:
            self.set_output(path, value)

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
