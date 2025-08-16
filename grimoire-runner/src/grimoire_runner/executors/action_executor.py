"""Action execution utilities for handling step actions using Strategy Pattern."""

import logging
from typing import TYPE_CHECKING, Any

from .action_strategies import ActionStrategyRegistry

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.system import System
    from .executor_factories import TableExecutorFactory

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Handles execution of step actions using Strategy Pattern for extensibility."""

    def __init__(
        self,
        strategy_registry: ActionStrategyRegistry | None = None,
        table_executor_factory: "TableExecutorFactory" = None,
    ):
        """Initialize with an optional custom strategy registry and table executor factory."""
        if strategy_registry is None:
            strategy_registry = ActionStrategyRegistry(table_executor_factory)
        self.strategy_registry = strategy_registry

    def execute_actions(
        self,
        actions: list[dict[str, Any]],
        context: "ExecutionContext",
        step_data: dict[str, Any],
        system: "System | None" = None,
    ) -> None:
        """Execute a list of actions."""
        for action in actions:
            try:
                logger.debug(f"[ACTION_EXECUTOR] Executing action: {action}")
                self.execute_single_action(action, context, step_data, system)
            except Exception as e:
                logger.error(f"[ACTION_EXECUTOR] Error executing action {action}: {e}")
                raise  # Re-raise to see the full stack trace

    def execute_single_action(
        self,
        action: dict[str, Any],
        context: "ExecutionContext",
        step_data: dict[str, Any],
        system: "System | None" = None,
    ) -> None:
        """Execute a single action using the appropriate strategy."""
        # Handle both old format (key as action type) and new format (type field)
        if "type" in action and "data" in action:
            action_type = action["type"]
            action_data = action["data"]
        else:
            # Fallback to old format
            action_type = list(action.keys())[0]
            action_data = action[action_type]

        # Temporarily add step_data to context for template resolution
        original_values = {}
        if step_data:
            logger.debug(f"[ACTION_EXECUTOR] Setting step_data variables: {step_data}")
            for key, value in step_data.items():
                original_values[key] = context.get_variable(key)
                logger.debug(
                    f"[ACTION_EXECUTOR] Setting {key} = {value} (type: {type(value)})"
                )
                context.set_variable(key, value)

            # Verify variables are set
            logger.debug(
                f"[ACTION_EXECUTOR] Context variables after setting: {list(context.variables.keys())}"
            )
            logger.debug(
                f"[ACTION_EXECUTOR] Checking result variable: {context.get_variable('result')}"
            )

        try:
            # Get the appropriate strategy for this action type
            strategy = self.strategy_registry.get_strategy(action_type)
            if strategy:
                logger.debug(f"[ACTION_EXECUTOR] Executing strategy for {action_type}")
                strategy.execute(action_data, context, system)
            else:
                logger.warning(f"No strategy found for action type: {action_type}")

        finally:
            # Restore original values
            if step_data:
                for key in step_data.keys():
                    if original_values[key] is not None:
                        context.set_variable(key, original_values[key])
                    else:
                        context.variables.pop(key, None)

    def get_supported_action_types(self) -> list[str]:
        """Get all supported action types."""
        return self.strategy_registry.get_supported_action_types()
