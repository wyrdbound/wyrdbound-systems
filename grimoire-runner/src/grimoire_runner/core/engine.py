"""Main GRIMOIRE engine for orchestrating system loading and flow execution."""

import logging
from collections.abc import Iterator
from pathlib import Path

from ..executors.executor_factories import ExecutorRegistry
from ..executors.executor_factory import ExecutorFactory, StepExecutorInterface
from ..models.context_data import ExecutionContext
from ..models.flow import FlowDefinition, FlowResult, StepResult
from ..models.system import System
from .loader import SystemLoader

logger = logging.getLogger(__name__)


class GrimoireEngine:
    """Main orchestrator for GRIMOIRE system execution."""

    def __init__(self, executor_registry: ExecutorRegistry = None):
        self.loader = SystemLoader()
        self.executor_registry = executor_registry or ExecutorRegistry()
        self.executors: dict[str, StepExecutorInterface] = {}
        self.action_executor = self.executor_registry.create_action_executor()
        self.breakpoints: dict[str, list[str]] = {}  # flow_id -> step_ids
        self._debug_mode = False

        # Initialize default executors
        self._initialize_executors()

    def _initialize_executors(self) -> None:
        """Initialize the default step executors using the registry."""
        supported_types = self.executor_registry.get_supported_step_types()
        for step_type in supported_types:
            try:
                executor = self.executor_registry.create_step_executor(step_type, self)
                self.executors[step_type] = executor
                logger.debug(f"Initialized executor for step type: {step_type}")
            except Exception as e:
                logger.warning(f"Failed to create executor for {step_type}: {e}")

    def register_executor(
        self, step_type: str, executor: StepExecutorInterface
    ) -> None:
        """Register a custom step executor."""
        self.executors[step_type] = executor
        logger.debug(f"Registered executor for step type: {step_type}")

    def set_executor_registry(self, registry: ExecutorRegistry) -> None:
        """Set a custom executor registry and reinitialize executors."""
        self.executor_registry = registry
        self.executors.clear()
        self.action_executor = self.executor_registry.create_action_executor()
        self._initialize_executors()

    def set_executor_factory(self, factory: ExecutorFactory) -> None:
        """Set a custom executor factory and reinitialize executors."""
        self.executor_registry.set_step_executor_factory(factory)
        self.executors.clear()
        self._initialize_executors()

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
            context.initialize_flow_namespace_variables(
                namespace_id, flow.variables.copy()
            )

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
            outputs = (
                flow_namespace_data["outputs"].copy() if flow_namespace_data else {}
            )

            # Also get the variables from the namespace
            variables = (
                flow_namespace_data["variables"].copy() if flow_namespace_data else {}
            )

            logger.info(
                f"Flow execution completed: {flow_id} (namespace: {namespace_id})"
            )
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
                self.action_executor.execute_actions(
                    step.actions, context, result.data, system
                )

            return result

        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            return StepResult(step_id=step.id, success=False, error=str(e))

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
