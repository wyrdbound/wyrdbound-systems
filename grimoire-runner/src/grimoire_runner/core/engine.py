"""Main GRIMOIRE engine for orchestrating system loading and flow execution."""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ..executors.base import BaseStepExecutor
from ..executors.choice_executor import ChoiceExecutor
from ..executors.dice_executor import DiceExecutor
from ..executors.flow_executor import FlowExecutor
from ..executors.llm_executor import LLMExecutor
from ..executors.table_executor import TableExecutor
from ..models.context_data import ExecutionContext
from ..models.flow import FlowDefinition, FlowResult, StepResult
from ..models.system import System
from .loader import SystemLoader

logger = logging.getLogger(__name__)


class GrimoireEngine:
    """Main orchestrator for GRIMOIRE system execution."""

    def __init__(self):
        self.loader = SystemLoader()
        self.executors: dict[str, BaseStepExecutor] = {}
        self.breakpoints: dict[str, list[str]] = {}  # flow_id -> step_ids
        self._debug_mode = False

        # Initialize default executors
        self._initialize_executors()

    def _initialize_executors(self) -> None:
        """Initialize the default step executors."""
        self.executors = {
            "dice_roll": DiceExecutor(),
            "dice_sequence": DiceExecutor(),
            "player_choice": ChoiceExecutor(self),
            "table_roll": TableExecutor(),
            "llm_generation": LLMExecutor(),
            "completion": FlowExecutor(),
            "flow_call": FlowExecutor(),
        }

    def register_executor(self, step_type: str, executor: BaseStepExecutor) -> None:
        """Register a custom step executor."""
        self.executors[step_type] = executor
        logger.debug(f"Registered executor for step type: {step_type}")

    def load_system(self, system_path: str | Path) -> System:
        """Load a GRIMOIRE system from filesystem."""
        return self.loader.load_system(system_path)

    def create_execution_context(self, **kwargs) -> ExecutionContext:
        """Create a new execution context with optional initial data."""
        context = ExecutionContext()

        # Set any provided initial data
        for key, value in kwargs.items():
            if key == "variables":
                context.variables.update(value)
            elif key == "inputs":
                context.inputs.update(value)
            elif key == "outputs":
                context.outputs.update(value)
            else:
                context.set_variable(key, value)

        return context

    def execute_flow(
        self, flow_id: str, context: ExecutionContext, system: System | None = None
    ) -> FlowResult:
        """Execute a complete flow and return the result."""
        if system is None:
            # Try to find the system from loaded systems
            systems = self.loader.list_loaded_systems()
            if not systems:
                raise ValueError("No system loaded and none provided")
            system = self.loader._loaded_systems[systems[0]]  # Use first loaded system

        flow = system.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow '{flow_id}' not found in system")

        logger.info(f"Executing flow: {flow.name} ({flow_id})")

        # Create unique execution namespace for this flow
        import uuid
        execution_id = str(uuid.uuid4())[:8]
        namespace_id = f"flow_{execution_id}"
        
        # Create isolated namespace for this flow execution
        context.create_flow_namespace(namespace_id, flow_id, execution_id)
        context.set_current_flow_namespace(namespace_id)

        try:
            # Set system metadata in context for templating
            context.system_metadata = {
                "id": system.id,
                "name": system.name,
                "description": system.description,
                "version": system.version,
                "currency": getattr(system, "currency", {}),
                "credits": getattr(system, "credits", {}),
            }

            # Initialize flow variables in the namespace
            context.initialize_flow_namespace_variables(namespace_id, flow.variables.copy())

            # Initialize observable derived fields from output models
            for output_def in flow.outputs:
                if output_def.type in system.models:
                    model = system.models[output_def.type]
                    logger.info(
                        f"Initializing model observables for {output_def.type} ({output_def.id})"
                    )
                    context.initialize_model_observables(model, output_def.id)

            # Execute all steps
            step_results = []
            current_step_id = flow.steps[0].id if flow.steps else None

            while current_step_id:
                step = flow.get_step(current_step_id)
                if not step:
                    break

                context.current_step = current_step_id
                context.step_history.append(current_step_id)

                # Check for breakpoints
                if self._debug_mode and self._has_breakpoint(flow_id, current_step_id):
                    logger.info(f"Breakpoint hit at step: {current_step_id}")
                    break

                # Execute the step
                try:
                    step_result = self._execute_step(step, context, system)
                    step_results.append(step_result)

                    if not step_result.success:
                        return FlowResult(
                            flow_id=flow_id,
                            success=False,
                            error=step_result.error,
                            step_results=step_results,
                            completed_at_step=current_step_id,
                        )

                    # Handle user input requirements
                    if step_result.requires_input:
                        # In automatic execution, we can't handle user input
                        # This should be handled by interactive execution
                        logger.warning(
                            f"Step {current_step_id} requires user input but we're in automatic mode"
                        )
                        break

                    # Determine next step
                    if step_result.next_step_id:
                        current_step_id = step_result.next_step_id
                    else:
                        current_step_id = flow.get_next_step_id(current_step_id)

                except ValueError:
                    # Re-raise ValueError exceptions (like missing executors) as they indicate configuration issues
                    raise
                except Exception as e:
                    logger.error(f"Error executing step {current_step_id}: {e}")
                    return FlowResult(
                        flow_id=flow_id,
                        success=False,
                        error=str(e),
                        step_results=step_results,
                        completed_at_step=current_step_id,
                    )

            # Compute all derived fields before extracting outputs
            logger.debug("Computing derived fields after flow execution")
            context.compute_derived_fields()

            # Copy flow outputs from namespace to root level for result
            context.copy_flow_outputs_to_root(namespace_id)

            # Extract outputs from the namespace for the result
            flow_namespace_data = context.get_flow_namespace_data(namespace_id)
            outputs = flow_namespace_data["outputs"].copy() if flow_namespace_data else {}

            # Also get the variables from the namespace
            variables = flow_namespace_data["variables"].copy() if flow_namespace_data else {}

            logger.info(f"Flow execution completed: {flow_id} (namespace: {namespace_id})")
            return FlowResult(
                flow_id=flow_id,
                success=True,
                outputs=outputs,
                variables=variables,
                step_results=step_results,
            )

        finally:
            # Clean up the flow namespace
            context.pop_flow_namespace()
            logger.debug(f"Cleaned up flow namespace: {namespace_id}")

    def step_through_flow(
        self, flow_id: str, context: ExecutionContext, system: System | None = None
    ) -> Iterator[StepResult]:
        """Execute a flow step by step, yielding results for each step."""
        if system is None:
            systems = self.loader.list_loaded_systems()
            if not systems:
                raise ValueError("No system loaded and none provided")
            system = self.loader._loaded_systems[systems[0]]

        flow = system.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow '{flow_id}' not found in system")

        # Set system metadata in context for templating
        context.system_metadata = {
            "id": system.id,
            "name": system.name,
            "description": system.description,
            "version": system.version,
            "currency": getattr(system, "currency", {}),
            "credits": getattr(system, "credits", {}),
        }

        # Initialize flow variables
        for var_name, var_value in flow.variables.items():
            context.set_variable(var_name, var_value)

        current_step_id = flow.steps[0].id if flow.steps else None

        while current_step_id:
            step = flow.get_step(current_step_id)
            if not step:
                break

            context.current_step = current_step_id
            context.step_history.append(current_step_id)

            # Execute the step
            try:
                step_result = self._execute_step(step, context, system)
                yield step_result

                if not step_result.success:
                    break

                # Determine next step
                if step_result.next_step_id:
                    current_step_id = step_result.next_step_id
                else:
                    current_step_id = flow.get_next_step_id(current_step_id)

            except Exception as e:
                logger.error(f"Error executing step {current_step_id}: {e}")
                yield StepResult(step_id=current_step_id, success=False, error=str(e))
                break

    def _execute_step(
        self, step, context: ExecutionContext, system: System
    ) -> StepResult:
        """Execute a single step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)

        # Check step condition
        if step.condition:
            try:
                condition_result = context.resolve_template(step.condition)
                if not condition_result:
                    logger.debug(
                        f"Step {step.id} skipped due to condition: {step.condition}"
                    )
                    return StepResult(
                        step_id=step.id,
                        success=True,
                        data={"skipped": True, "reason": "condition_false"},
                    )
            except Exception as e:
                logger.error(f"Error evaluating condition for step {step.id}: {e}")
                return StepResult(
                    step_id=step.id,
                    success=False,
                    error=f"Condition evaluation failed: {e}",
                )

        # Get the appropriate executor
        executor = self.executors.get(step_type)
        if not executor:
            error_msg = f"No executor found for step type: {step_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Execute the step
        try:
            result = executor.execute(step, context, system)

            # Handle output variable setting
            if result.success and step.output and result.data:
                if "result" in result.data:
                    context.set_variable(step.output, result.data["result"])
                elif result.data:
                    # Use the first available data value if no 'result' key
                    first_value = next(iter(result.data.values()))
                    context.set_variable(step.output, first_value)

            # Execute post-step actions, but skip for choice steps that require user input
            # Those will be handled after user interaction
            if step.actions and not (
                result.requires_input and step_type == "player_choice"
            ):
                self._execute_actions(step.actions, context, result.data, system)

            return result

        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            return StepResult(step_id=step.id, success=False, error=str(e))

    def _execute_actions(
        self,
        actions: list[dict[str, Any]],
        context: ExecutionContext,
        step_data: dict[str, Any],
        system: System | None = None,
    ) -> None:
        """Execute a list of actions."""
        for action in actions:
            try:
                self._execute_single_action(action, context, step_data, system)
            except Exception as e:
                logger.error(f"Error executing action {action}: {e}")

    def _execute_single_action(
        self,
        action: dict[str, Any],
        context: ExecutionContext,
        step_data: dict[str, Any],
        system: System | None = None,
    ) -> None:
        """Execute a single action."""
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
            for key, value in step_data.items():
                original_values[key] = context.get_variable(key)
                context.set_variable(key, value)

        try:
            if action_type == "set_value":
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

            elif action_type == "get_value":
                # This is typically used in templates, not as a standalone action
                pass

            elif action_type == "display_value":
                # For now, just log the value
                path = (
                    action_data
                    if isinstance(action_data, str)
                    else action_data.get("path", "")
                )
                try:
                    value = context.resolve_path_value(path)
                    logger.info(f"Display: {path} = {value}")
                except Exception as e:
                    logger.warning(f"Could not display value at path {path}: {e}")

            elif action_type == "validate_value":
                # TODO: Implement validation
                pass

            elif action_type == "log_event":
                event_type = action_data.get("type", "unknown")
                event_data = action_data.get("data", {})
                logger.info(f"Event: {event_type} - {event_data}")

            elif action_type == "swap_values":
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
                    logger.error(
                        f"Error swapping values between {path1} and {path2}: {e}"
                    )

            elif action_type == "flow_call":
                # Handle sub-flow calls
                flow_id = action_data["flow"]
                raw_inputs = action_data.get("inputs", {})
                logger.info(
                    f"Engine action flow_call: {flow_id} (raw inputs: {raw_inputs})"
                )

                # Resolve input templates using the current context
                resolved_inputs = {}
                for input_key, input_value in raw_inputs.items():
                    if isinstance(input_value, str):
                        # Resolve any templates in the input value
                        try:
                            if input_value.startswith("{{") and input_value.endswith(
                                "}}"
                            ):
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

                logger.info(
                    f"Engine action flow_call resolved inputs: {resolved_inputs}"
                )

                # Import here to avoid circular imports
                from ..executors.table_executor import TableExecutor

                # Use the table executor's sub-flow execution logic
                # since it already handles the template resolution and typing correctly
                table_executor = TableExecutor()
                try:
                    if system:
                        table_executor._execute_sub_flow(
                            flow_id, resolved_inputs, context, system, raw_inputs
                        )
                        logger.info(f"Successfully executed sub-flow: {flow_id}")
                    else:
                        logger.error(
                            f"No system available for sub-flow execution: {flow_id}"
                        )
                except Exception as e:
                    logger.error(f"Error executing sub-flow {flow_id}: {e}")

            else:
                logger.warning(f"Unknown action type: {action_type}")

        finally:
            # Restore original values
            if step_data:
                for key in step_data.keys():
                    if original_values[key] is not None:
                        context.set_variable(key, original_values[key])
                    else:
                        context.variables.pop(key, None)

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

    def set_breakpoint(self, flow_id: str, step_id: str) -> None:
        """Set a breakpoint on a specific step."""
        if flow_id not in self.breakpoints:
            self.breakpoints[flow_id] = []

        if step_id not in self.breakpoints[flow_id]:
            self.breakpoints[flow_id].append(step_id)
            logger.info(f"Breakpoint set: {flow_id}.{step_id}")

    def remove_breakpoint(self, flow_id: str, step_id: str) -> None:
        """Remove a breakpoint from a specific step."""
        if flow_id in self.breakpoints:
            if step_id in self.breakpoints[flow_id]:
                self.breakpoints[flow_id].remove(step_id)
                logger.info(f"Breakpoint removed: {flow_id}.{step_id}")

    def clear_breakpoints(self, flow_id: str | None = None) -> None:
        """Clear breakpoints for a flow or all flows."""
        if flow_id:
            if flow_id in self.breakpoints:
                del self.breakpoints[flow_id]
        else:
            self.breakpoints.clear()
        logger.info(f"Breakpoints cleared for {flow_id or 'all flows'}")

    def _has_breakpoint(self, flow_id: str, step_id: str) -> bool:
        """Check if there's a breakpoint on a specific step."""
        return flow_id in self.breakpoints and step_id in self.breakpoints[flow_id]

    def has_breakpoint(self, flow_id: str, step_id: str) -> bool:
        """Public method to check if there's a breakpoint set for a specific step."""
        return self._has_breakpoint(flow_id, step_id)

    def execute_flow_steps(
        self, flow_id: str, context: ExecutionContext, system: System | None = None
    ) -> Iterator[StepResult]:
        """Execute flow steps one by one, yielding each step result. Alias for step_through_flow."""
        return self.step_through_flow(flow_id, context, system)

    def enable_debug_mode(self) -> None:
        """Enable debug mode with breakpoint support."""
        self._debug_mode = True
        logger.info("Debug mode enabled")

    def disable_debug_mode(self) -> None:
        """Disable debug mode."""
        self._debug_mode = False
        logger.info("Debug mode disabled")

    def set_debug_mode(self, enabled: bool) -> None:
        """Set debug mode on or off."""
        if enabled:
            self.enable_debug_mode()
        else:
            self.disable_debug_mode()

    def set_breakpoints(self, flow_id: str, step_ids: list[str]) -> None:
        """Set multiple breakpoints for a flow."""
        if flow_id not in self.breakpoints:
            self.breakpoints[flow_id] = []
        self.breakpoints[flow_id] = step_ids.copy()
        logger.debug(f"Set breakpoints for flow {flow_id}: {step_ids}")

    def get_available_flows(self, system: System | None = None) -> list[FlowDefinition]:
        """Get all available flows from a system."""
        if system is None:
            systems = self.loader.list_loaded_systems()
            if not systems:
                return []
            system = self.loader._loaded_systems[systems[0]]

        return list(system.flows.values())
