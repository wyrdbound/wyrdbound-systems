"""Core engine for executing GRIMOIRE flows."""

import logging
import uuid
from pathlib import Path
from typing import Iterator

from ..executors.executor_factories import ExecutorRegistry
from ..executors.executor_factory import ExecutorFactory, StepExecutorInterface
from ..models.context_data import ExecutionContext
from ..models.flow import FlowDefinition, FlowResult, StepResult
from ..models.system import System
from .loader import SystemLoader
from ..services import event_signals

logger = logging.getLogger(__name__)


class GrimoireEngine:
    """Main orchestrator for GRIMOIRE system execution."""

    def __init__(self, executor_registry: ExecutorRegistry = None):
        self.loader = SystemLoader()
        self.executor_registry = executor_registry or ExecutorRegistry()
        self.executors: dict[str, StepExecutorInterface] = {}
        self.action_executor = self.executor_registry.create_action_executor()

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

    def create_execution_context(self, system: System = None, **kwargs) -> ExecutionContext:
        """Create a new execution context with optional initial data."""
        from ..utils.debug import debug_print
        debug_print(f"[ENGINE] create_execution_context called with system: {system is not None}")
        
        context = ExecutionContext()

        # Populate system metadata if system is provided
        if system:
            debug_print(f"[ENGINE] Populating system_metadata with models: {list(system.models.keys())}")
            context.system_metadata = {
                "id": system.id,
                "name": system.name,
                "description": system.description,
                "version": system.version,
                "models": system.models,  # Add models for ModelAwareDict
            }
        else:
            debug_print(f"[ENGINE] No system provided, system_metadata will be empty")

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
        from ..utils.debug import debug_print
        
        if system is None:
            # Try to find the system from loaded systems
            systems = self.loader.list_loaded_systems()
            if not systems:
                raise ValueError("No system loaded and none provided")
            system = self.loader._loaded_systems[systems[0]]  # Use first loaded system

        flow = system.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow '{flow_id}' not found in system")

        debug_print(f"[ENGINE] Executing flow: {flow.name} ({flow_id})")

        # Create unique execution namespace for this flow
        import uuid

        execution_id = str(uuid.uuid4())[:8]
        namespace_id = f"flow_{execution_id}"
        
        # Add execution ID to context for event tracking
        context.execution_id = execution_id

        # Create isolated namespace for this flow execution
        context.create_flow_namespace(namespace_id, flow_id, execution_id)
        context.set_current_flow_namespace(namespace_id)

        try:
            context.system_metadata = {
                "id": system.id,
                "name": system.name,
                "description": system.description,
                "version": system.version,
                "models": system.models,  # Add models for template resolution
            }

            # Initialize flow variables in the namespace
            variables_dict = (
                {var.id: var.default for var in flow.variables}
                if flow.variables
                else {}
            )
            context.initialize_flow_namespace_variables(namespace_id, variables_dict)

            # Initialize complete model instances for declared outputs
            context.initialize_output_models(flow.outputs, system)

            # Initialize observable derived fields from output models
            for output_def in flow.outputs:
                if output_def.type in system.models:
                    model = system.models[output_def.type]
                    debug_print(
                        f"Initializing model observables for {output_def.type} ({output_def.id})"
                    )
                    # Create a generic model resolver function
                    def model_resolver(model_type):
                        return system.models.get(model_type)
                    context.initialize_model_observables(model, output_def.id, model_resolver)

            # Execute all steps
            step_results = []
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
                    step_results.append(step_result)

                    if not step_result.success:
                        flow_result = FlowResult(
                            flow_id=flow_id,
                            success=False,
                            error=step_result.error,
                            step_results=step_results,
                            completed_at_step=current_step_id,
                        )
                        
                        return flow_result

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
                    
                    flow_result = FlowResult(
                        flow_id=flow_id,
                        success=False,
                        error=str(e),
                        step_results=step_results,
                        completed_at_step=current_step_id,
                    )
                    
                    return flow_result

            # Compute all derived fields before extracting outputs
            debug_print("Computing derived fields after flow execution")
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

            debug_print(
                f"Flow execution completed: {flow_id} (namespace: {namespace_id})"
            )
            
            flow_result = FlowResult(
                flow_id=flow_id,
                success=True,
                outputs=outputs,
                variables=variables,
                step_results=step_results,
            )
            
            return flow_result

        finally:
            # Clean up the flow namespace
            context.pop_flow_namespace()
            debug_print(f"Cleaned up flow namespace: {namespace_id}")

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
            "models": system.models,  # Add models for template resolution
        }

        # Initialize flow variables
        if flow.variables:
            for variable in flow.variables:
                context.set_variable(variable.id, variable.default)

        current_step_id = flow.steps[0].id if flow.steps else None

        while current_step_id:
            step = flow.get_step(current_step_id)
            if not step:
                break

            context.current_step = current_step_id
            context.step_history.append(current_step_id)

            # Execute the step
            try:
                from ..utils.debug import debug_print
                
                step_result = self._execute_step(step, context, system)
                
                # Store the step result in context so UI service can update it
                context.set_variable(f"_last_step_result_{step.id}", step_result)
                
                yield step_result

                if not step_result.success:
                    break

                # Check if the step result was updated by UI service after user input
                updated_result = context.get_variable(f"_updated_step_result_{step.id}")
                if updated_result:
                    debug_print(f"[ENGINE] Using updated step result for {step.id}")
                    step_result = updated_result
                    # Clean up the updated result
                    context.set_variable(f"_updated_step_result_{step.id}", None)

                # Determine next step
                if step_result.next_step_id:
                    debug_print(f"[ENGINE] Step {current_step_id} result has next_step_id: {step_result.next_step_id}")
                    current_step_id = step_result.next_step_id
                else:
                    next_step_from_flow = flow.get_next_step_id(current_step_id)
                    debug_print(f"[ENGINE] Step {current_step_id} using sequential next step: {next_step_from_flow}")
                    current_step_id = next_step_from_flow

            except Exception as e:
                logger.error(f"Error executing step {current_step_id}: {e}")
                yield StepResult(step_id=current_step_id, success=False, error=str(e))
                break

    def _execute_step(
        self, step, context: ExecutionContext, system: System
    ) -> StepResult:
        """Execute a single step."""
        from ..utils.debug import debug_print
        
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        
        debug_print(f"[ENGINE] Executing step {step.id} (type: {step_type})")
        # Check step condition
        if step.condition:
            try:
                condition_result = context.resolve_template(step.condition)
                if not condition_result:
                    debug_print(
                        f"Step {step.id} skipped due to condition: {step.condition}"
                    )
                    
                    result = StepResult(
                        step_id=step.id,
                        success=True,
                        data={"skipped": True, "reason": "condition_false"},
                    )
                    
                    # Publish step executed event for skipped step
                    event_signals.publish_step_executed(
                        step_type=step_type,
                        step_id=step.id,
                        result=result.data,
                        context_id=getattr(context, 'execution_id', None)
                    )
                    
                    return result
            except Exception as e:
                logger.error(f"Error evaluating condition for step {step.id}: {e}")
                
                error_result = StepResult(
                    step_id=step.id,
                    success=False,
                    error=f"Condition evaluation failed: {e}",
                )
                
                # Publish step executed event for failed condition
                event_signals.publish_step_executed(
                    step_type=step_type,
                    step_id=step.id,
                    result={"error": error_result.error},
                    context_id=getattr(context, 'execution_id', None)
                )
                
                return error_result

        # Get the appropriate executor
        executor = self.executors.get(step_type)
        if not executor:
            error_msg = f"No executor found for step type: {step_type}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Execute pre-actions before the step's main logic
        if step.pre_actions:
            debug_print(f"Engine executing {len(step.pre_actions)} pre-actions for step {step.id}")
            self.action_executor.execute_actions(
                step.pre_actions, context, {}, system
            )

        # Execute the step
        try:
            result = executor.execute(step, context, system)
            
            debug_print(f"[ENGINE] Step {step.id} executed with success: {result.success}")

            # Special handling for player_input steps when user input is available
            if (step_type == "player_input" and 
                result.requires_input and 
                hasattr(context, 'get_variable') and 
                context.get_variable('user_input') is not None):
                
                debug_print(f"[ENGINE] User input available for player_input step {step.id}, processing input")
                
                # Call the process_input method to handle the user input
                user_input = context.get_variable('user_input')
                if hasattr(executor, 'process_input'):
                    try:
                        result = executor.process_input(user_input, step, context, system)
                        debug_print(f"[ENGINE] User input processed with success: {result.success}")
                        
                        # Clear the user_input variable after processing
                        context.set_variable('user_input', None)
                    except Exception as e:
                        logger.error(f"Error processing user input for step {step.id}: {e}")
                        result = StepResult(step_id=step.id, success=False, error=f"Input processing failed: {e}")

            # Handle output variable setting
            if result.success and step.output and result.data:
                if "result" in result.data:
                    context.set_variable(step.output, result.data["result"])
                elif result.data:
                    # Use the first available data value if no 'result' key
                    first_value = next(iter(result.data.values()))
                    context.set_variable(step.output, first_value)

            # Execute post-step actions, but skip for steps that require user input
            # Those will be handled after user interaction
            # Also skip if the executor already handled the actions (e.g., flow_call)
            actions_already_handled = getattr(result, "actions_already_executed", False)

            # Combine actions (for backward compatibility) and post_actions
            step_actions = getattr(step, 'actions', []) or []
            step_post_actions = getattr(step, 'post_actions', []) or []
            post_actions = list(step_actions) + list(step_post_actions)

            if (
                post_actions
                and not result.requires_input
                and not actions_already_handled
            ):
                debug_print(
                    f"Engine executing {len(post_actions)} post-step actions for step {step.id}"
                )
                self.action_executor.execute_actions(
                    post_actions, context, result.data, system
                )
            elif actions_already_handled:
                debug_print(
                    f"Skipping post-step actions for step {step.id} - already handled by executor"
                )

            # Resolve result message template AFTER actions are executed
            # This ensures that any outputs set by actions are available in the template context
            if step.result_message and result.success:
                try:
                    # Use ExecutionContext's template resolution with step data
                    step_data = result.data if result.data else {}
                    resolved_message = context.resolve_template_with_step_data(
                        step.result_message, step_data
                    )
                    # Add resolved message to result data
                    if result.data:
                        result.data["resolved_message"] = resolved_message
                    else:
                        result.data = {"resolved_message": resolved_message}
                except Exception as e:
                    logger.error(f"Failed to resolve result message template: {e}")
            elif actions_already_handled:
                debug_print(
                    f"Skipping post-step actions for step {step.id} - already handled by executor"
                )

            # Publish step executed event
            event_signals.publish_step_executed(
                step_type=step_type,
                step_id=step.id,
                result=result.data,
                context_id=getattr(context, 'execution_id', None)
            )

            return result

        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            
            error_result = StepResult(step_id=step.id, success=False, error=str(e))
            
            # Publish step executed event for error
            event_signals.publish_step_executed(
                step_type=step_type,
                step_id=step.id,
                result={"error": str(e)},
                context_id=getattr(context, 'execution_id', None)
            )
            
            return error_result

    def get_available_flows(self, system: System | None = None) -> list[FlowDefinition]:
        """Get all available flows from a system."""
        if system is None:
            systems = self.loader.list_loaded_systems()
            if not systems:
                return []
            system = self.loader._loaded_systems[systems[0]]

        return list(system.flows.values())
