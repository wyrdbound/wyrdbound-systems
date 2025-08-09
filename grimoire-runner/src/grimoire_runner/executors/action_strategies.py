"""Strategy pattern implementation for different action types."""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.system import System
    from .executor_factories import TableExecutorFactory

logger = logging.getLogger(__name__)


class ActionStrategy(ABC):
    """Abstract base class for action execution strategies."""

    @abstractmethod
    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute the action with the given data."""

    @abstractmethod
    def get_action_type(self) -> str:
        """Get the action type this strategy handles."""


class SetValueActionStrategy(ActionStrategy):
    """Strategy for handling set_value actions."""

    def get_action_type(self) -> str:
        return "set_value"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a set_value action."""
        path = action_data["path"]
        value = action_data["value"]

        # Handle dictionary values specially to avoid string conversion
        if isinstance(value, dict):
            # Use dictionary directly without template resolution
            resolved_value = value
            logger.info(f"Action set_value: Using dict directly for {path}")
        else:
            # Resolve template in value for non-dict values
            resolved_value = context.resolve_template(str(value))
            logger.info(f"Action set_value: Resolved template for {path}")

        # Use namespaced paths to avoid collision during flow execution
        current_namespace = context.get_current_flow_namespace()

        if current_namespace:
            # Use namespaced path to avoid collision
            if path.startswith("outputs."):
                namespaced_path = f"{current_namespace}.outputs.{path[8:]}"
            elif path.startswith("variables."):
                namespaced_path = f"{current_namespace}.variables.{path[10:]}"
            else:
                # Default to outputs if no prefix specified
                namespaced_path = f"{current_namespace}.outputs.{path}"

            context.set_namespaced_value(namespaced_path, resolved_value)
        else:
            # Fallback to original behavior for backward compatibility
            if path.startswith("outputs."):
                context.set_output(path[8:], resolved_value)
            elif path.startswith("variables."):
                context.set_variable(path[10:], resolved_value)
            else:
                # Default to outputs
                context.set_output(path, resolved_value)


class DisplayValueActionStrategy(ActionStrategy):
    """Strategy for handling display_value actions."""

    def get_action_type(self) -> str:
        return "display_value"

    def execute(
        self,
        action_data: dict[str, Any] | str,
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a display_value action."""
        # For now, just log the value
        path = (
            action_data if isinstance(action_data, str) else action_data.get("path", "")
        )
        try:
            value = context.resolve_path_value(path)
            logger.info(f"Display: {path} = {value}")
        except Exception as e:
            logger.warning(f"Could not display value at path {path}: {e}")


class LogEventActionStrategy(ActionStrategy):
    """Strategy for handling log_event actions."""

    def get_action_type(self) -> str:
        return "log_event"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a log_event action."""
        event_type = action_data.get("type", "unknown")
        event_data = action_data.get("data", {})
        logger.info(f"Event: {event_type} - {event_data}")


class SwapValuesActionStrategy(ActionStrategy):
    """Strategy for handling swap_values actions."""

    def get_action_type(self) -> str:
        return "swap_values"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a swap_values action."""
        # Swap values between two paths
        path1 = action_data.get("path1", "")
        path2 = action_data.get("path2", "")

        # Resolve templates in the paths
        path1 = context.resolve_template(path1)
        path2 = context.resolve_template(path2)

        try:
            # Get values from both paths
            value1 = context.resolve_path_value(path1)
            value2 = context.resolve_path_value(path2)

            # Swap them
            self._set_value_at_path(context, path1, value2)
            self._set_value_at_path(context, path2, value1)

            logger.info(f"Swapped values: {path1} <-> {path2}")

        except Exception as e:
            logger.error(f"Error swapping values between {path1} and {path2}: {e}")

    def _set_value_at_path(
        self, context: "ExecutionContext", path: str, value: Any
    ) -> None:
        """Set a value at a specific path in the context."""
        if path.startswith("outputs."):
            context.set_output(path[8:], value)
        elif path.startswith("variables."):
            context.set_variable(path[10:], value)
        else:
            # Default to outputs
            context.set_output(path, value)


class FlowCallActionStrategy(ActionStrategy):
    """Strategy for handling flow_call actions."""

    def __init__(self, table_executor_factory: "TableExecutorFactory" = None):
        """Initialize with optional table executor factory for dependency injection."""
        self.table_executor_factory = table_executor_factory

    def get_action_type(self) -> str:
        return "flow_call"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a flow_call action."""
        # Handle sub-flow calls
        flow_id = action_data["flow"]
        raw_inputs = action_data.get("inputs", {})
        logger.info(f"Engine action flow_call: {flow_id} (raw inputs: {raw_inputs})")

        # Resolve input templates using the current context
        resolved_inputs = {}
        for input_key, input_value in raw_inputs.items():
            if isinstance(input_value, str):
                # Resolve any templates in the input value
                try:
                    if input_value.startswith("{{") and input_value.endswith("}}"):
                        # This is a template, resolve it while preserving object types
                        resolved_value = context.resolve_template(input_value)
                        logger.info(
                            f"Resolved template {input_key}: {input_value} -> {type(resolved_value).__name__}"
                        )
                    elif "outputs." in input_value:
                        # This is a path reference, resolve it
                        resolved_value = context.resolve_path_value(input_value)
                        logger.info(
                            f"Resolved path {input_key}: {input_value} -> {type(resolved_value).__name__}"
                        )
                    else:
                        # Plain string, use as-is
                        resolved_value = input_value
                    resolved_inputs[input_key] = resolved_value
                except Exception as e:
                    logger.error(
                        f"Failed to resolve input {input_key}: {input_value} - {e}"
                    )
                    resolved_inputs[input_key] = input_value
            else:
                # Non-string values, use as-is
                resolved_inputs[input_key] = input_value

        logger.info(f"Engine action flow_call resolved inputs: {resolved_inputs}")

        # Create table executor using factory or fallback to direct creation
        if self.table_executor_factory:
            table_executor = self.table_executor_factory.create_table_executor()
        else:
            # Fallback to direct import and creation for backward compatibility
            from ..executors.table_executor import TableExecutor

            table_executor = TableExecutor()

        # Use the table executor's sub-flow execution logic
        # since it already handles the template resolution and typing correctly
        try:
            if system:
                table_executor._execute_sub_flow(
                    flow_id, resolved_inputs, context, system, raw_inputs
                )
                logger.info(f"Successfully executed sub-flow: {flow_id}")
            else:
                logger.error(f"No system available for sub-flow execution: {flow_id}")
        except Exception as e:
            logger.error(f"Error executing sub-flow {flow_id}: {e}")


class GetValueActionStrategy(ActionStrategy):
    """Strategy for handling get_value actions (typically used in templates)."""

    def get_action_type(self) -> str:
        return "get_value"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a get_value action (no-op as it's used in templates)."""
        # This is typically used in templates, not as a standalone action
        pass


class ValidateValueActionStrategy(ActionStrategy):
    """Strategy for handling validate_value actions."""

    def get_action_type(self) -> str:
        return "validate_value"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a validate_value action."""
        # TODO: Implement validation
        logger.info(
            f"Validate value action called - not yet implemented: {action_data}"
        )


class ActionStrategyRegistry:
    """Registry for managing action strategies."""

    def __init__(self, table_executor_factory: "TableExecutorFactory" = None):
        self._strategies: dict[str, ActionStrategy] = {}
        self.table_executor_factory = table_executor_factory
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register the default action strategies."""
        default_strategies = [
            SetValueActionStrategy(),
            DisplayValueActionStrategy(),
            LogEventActionStrategy(),
            SwapValuesActionStrategy(),
            FlowCallActionStrategy(self.table_executor_factory),
            GetValueActionStrategy(),
            ValidateValueActionStrategy(),
        ]

        for strategy in default_strategies:
            self.register_strategy(strategy)

    def register_strategy(self, strategy: ActionStrategy) -> None:
        """Register an action strategy."""
        action_type = strategy.get_action_type()
        self._strategies[action_type] = strategy
        logger.debug(f"Registered action strategy for: {action_type}")

    def get_strategy(self, action_type: str) -> ActionStrategy | None:
        """Get a strategy for the given action type."""
        return self._strategies.get(action_type)

    def get_supported_action_types(self) -> list[str]:
        """Get all supported action types."""
        return list(self._strategies.keys())
