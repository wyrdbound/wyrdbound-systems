"""Player choice step executor."""

import logging
from typing import TYPE_CHECKING, Any

from .base import BaseStepExecutor
from .flow_helper import create_flow_helper

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System
    from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class ChoiceExecutor(BaseStepExecutor):
    """Executor for player choice steps."""

    def __init__(self, engine=None, action_executor: "ActionExecutor" = None):
        """Initialize the choice executor with optional engine reference and action executor."""
        self.engine = engine
        self.flow_helper = create_flow_helper(engine)
        
        if action_executor is None:
            # Fallback to direct creation for backward compatibility
            from .action_executor import ActionExecutor
            action_executor = ActionExecutor()
        self.action_executor = action_executor

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a player choice step."""
        from ..models.flow import StepResult

        try:
            # Execute pre-actions if present
            if step.pre_actions:
                self._execute_pre_actions(step.pre_actions, context)

            # Resolve choice source if specified
            choices = step.choices
            selection_count = 1  # Default to single selection
            if step.choice_source:
                choices = self._generate_choices_from_source(
                    step.choice_source, context, system
                )

                # Fail the step if no choices were generated from the source
                if not choices:
                    error_msg = "Failed to generate choices from choice source"
                    logger.error(f"Step {step.id}: {error_msg}")
                    return StepResult(step_id=step.id, success=False, error=error_msg)

                # Extract selection count from choice source
                if isinstance(step.choice_source, dict):
                    selection_count = step.choice_source.get("selection_count", 1)

            # Resolve template strings in choices
            resolved_choices = []
            for choice in choices:
                resolved_choice = choice
                if choice.label:
                    resolved_choice.label = context.resolve_template(choice.label)
                resolved_choices.append(resolved_choice)

            logger.debug(f"Player choice step: {step.name}")
            for i, choice in enumerate(resolved_choices):
                logger.debug(f"  {i + 1}. {choice.label}")

            # Check if user input is already available in the context
            user_choice_id = context.get_variable("pending_user_choice_id")
            user_choice_ids = context.get_variable("pending_user_choice_ids")
            
            if selection_count > 1 and user_choice_ids is not None:
                # Process multiple choice selection
                logger.debug(f"MULTIPLE CHOICE PATH - Processing multiple user choices: {user_choice_ids}")
                logger.debug(f"MULTIPLE CHOICE PATH - selection_count: {selection_count}")
                
                # Clear the pending input
                context.set_variable("pending_user_choice_ids", None)
                
                # Set the results variable for multiple choices
                context.set_variable("results", user_choice_ids)
                
                # Debug: Check if step has actions
                logger.debug(f"Step {step.id} step object: {step}")
                logger.debug(f"Step {step.id} step dir: {dir(step)}")
                logger.debug(f"Step {step.id} has actions: {step.actions is not None}")
                if hasattr(step, 'actions') and step.actions:
                    logger.debug(f"Step {step.id} actions count: {len(step.actions)}")
                    logger.debug(f"Step {step.id} actions: {step.actions}")
                else:
                    logger.debug(f"Step {step.id} has no actions or actions is None")
                
                # Execute step-level actions if present
                actions_already_executed = False
                if hasattr(step, 'actions') and step.actions:
                    logger.debug(f"Executing {len(step.actions)} step actions after multiple choice")
                    step_result_data = {"results": user_choice_ids}
                    self.action_executor.execute_actions(step.actions, context, step_result_data, system)
                    logger.debug(f"Finished executing step actions for {step.id}")
                    actions_already_executed = True
                else:
                    logger.debug(f"No step actions to execute for {step.id}")
                
                # Return successful result with next_step_id if specified
                result = StepResult(
                    step_id=step.id,
                    success=True,
                    data={"results": user_choice_ids},
                    next_step_id=step.next_step
                )
                result.actions_already_executed = actions_already_executed
                return result
                
            elif selection_count == 1 and user_choice_id is not None:
                # Process single choice selection
                logger.debug(f"Processing user choice: {user_choice_id}")
                
                # Clear the pending input
                context.set_variable("pending_user_choice_id", None)
                
                # Process the choice using existing logic
                choice_result = self.process_choice(user_choice_id, step, context, system)
                return choice_result
                
            else:
                # No user input available - return step that requires input
                return StepResult(
                    step_id=step.id,
                    success=True,
                    requires_input=True,
                    prompt=step.prompt,
                    choices=resolved_choices,
                    data={
                        "choice_count": len(resolved_choices),
                        "selection_count": selection_count,
                        "has_choice_source": bool(step.choice_source),
                    },
                )

        except Exception as e:
            logger.error(f"Error executing choice step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Choice step failed: {e}"
            )

    def _execute_pre_actions(self, pre_actions, context: "ExecutionContext") -> None:
        """Execute pre-actions before presenting choices."""
        # Delegate all pre-actions to the centralized ActionExecutor
        try:
            self.action_executor.execute_actions(
                pre_actions, context, {}, None
            )
        except Exception as e:
            logger.error(f"Error executing pre-actions: {e}")

    def _generate_choices_from_source(
        self, choice_source, context: "ExecutionContext", system: "System"
    ):
        """Generate choices from a choice source specification."""
        try:
            if isinstance(choice_source, dict):
                if "table_from_values" in choice_source:
                    # Generate choices from a values table like attributes
                    path = choice_source["table_from_values"]
                    choice_source.get("selection_count", 1)
                    display_format = choice_source.get(
                        "display_format", "{{ key }}: {{ value }}"
                    )

                    # Get the data from context
                    data = context.resolve_path_value(path)
                    if isinstance(data, dict):
                        from ..models.flow import ChoiceDefinition

                        choices = []

                        for key, value in data.items():
                            # Create template context for formatting
                            template_context = {
                                "key": key,
                                "value": value,
                            }

                            # Use step data template resolution to make key and value available at top level
                            label = context.resolve_template_with_step_data(
                                display_format, template_context
                            )
                            if not isinstance(label, str):
                                label = str(label)

                            choice = ChoiceDefinition(
                                id=key,
                                label=label,
                                actions=[
                                    {
                                        "set_value": {
                                            "path": f"variables.selected_{path.split('.')[-1]}",
                                            "value": key,
                                        }
                                    }
                                ],
                            )
                            choices.append(choice)

                        logger.debug(f"Generated {len(choices)} choices from {path}")
                        return choices
                    else:
                        logger.warning(
                            f"Data at path {path} is not a dict: {type(data)}"
                        )
                        return []

                elif "compendium" in choice_source:
                    # Generate choices from compendium entries
                    comp_name = choice_source["compendium"]
                    comp = system.get_compendium(comp_name)
                    if comp:
                        from ..models.flow import ChoiceDefinition

                        choices = []

                        for entry_id, entry_data in comp.entries.items():
                            choice = ChoiceDefinition(
                                id=entry_id,
                                label=entry_data.get("name", entry_id),
                                actions=[
                                    {
                                        "set_value": {
                                            "path": "variables.result",
                                            "value": entry_id,
                                        }
                                    }
                                ],
                            )
                            choices.append(choice)

                        logger.debug(
                            f"Generated {len(choices)} choices from compendium {comp_name}"
                        )
                        return choices
                    else:
                        logger.warning(f"Compendium {comp_name} not found")
                        return []

                elif "table" in choice_source:
                    # Generate choices from table entries
                    table_name = choice_source["table"]
                    table = system.get_table(table_name)
                    if table:
                        from ..models.flow import ChoiceDefinition

                        choices = []

                        for _entry_key, entry_value in table.entries.items():
                            # Use the entry value as the choice ID (not the table key)
                            choice_id = str(entry_value)
                            choice_label = str(entry_value)
                            choice_description = ""
                            selected_item_value = entry_value  # Default to just the ID

                            # If table has an entry_type, try to look up the item in compendiums
                            if hasattr(table, "entry_type") and table.entry_type:
                                # Try to find the item in compendiums
                                for comp_id in system.list_compendiums():
                                    comp = system.get_compendium(comp_id)
                                    if comp and entry_value in comp.entries:
                                        entry_data = comp.entries[entry_value]

                                        # Apply model inheritance to ensure defaults are included
                                        if table.entry_type in system.models:
                                            model_def = system.models[table.entry_type]
                                            # Create a copy and apply model defaults
                                            enhanced_entry_data = dict(entry_data) if isinstance(entry_data, dict) else entry_data
                                            if isinstance(enhanced_entry_data, dict):
                                                enhanced_entry_data = self._apply_model_defaults(enhanced_entry_data, model_def, system)
                                                selected_item_value = enhanced_entry_data
                                            else:
                                                selected_item_value = entry_data
                                        else:
                                            # Use the full object as the selected_item value
                                            selected_item_value = entry_data
                                        # Use the proper name if available
                                        if (
                                            isinstance(entry_data, dict)
                                            and "name" in entry_data
                                        ):
                                            choice_label = entry_data["name"]
                                        # Use the description if available
                                        if (
                                            isinstance(entry_data, dict)
                                            and "description" in entry_data
                                        ):
                                            choice_description = entry_data[
                                                "description"
                                            ]
                                        break

                            # Create choice definition
                            choice = ChoiceDefinition(
                                id=choice_id,
                                label=choice_label,
                                description=choice_description,
                                actions=[
                                    {
                                        "set_value": {
                                            "path": "variables.result",
                                            "value": selected_item_value,
                                        }
                                    }
                                ],
                            )
                            choices.append(choice)

                        logger.debug(
                            f"Generated {len(choices)} choices from table {table_name}"
                        )
                        return choices
                    else:
                        # Provide helpful error message with available tables
                        available_tables = system.list_tables()
                        table_list = (
                            ", ".join(sorted(available_tables))
                            if available_tables
                            else "none"
                        )
                        logger.warning(
                            f"Table '{table_name}' not found in system. Available tables: {table_list}"
                        )
                        return []

                else:
                    # Improved error message for unknown formats
                    available_formats = ["table_from_values", "compendium", "table"]
                    logger.warning(
                        f"Unknown choice source format: {choice_source}. Supported formats: {', '.join(available_formats)}"
                    )
                    return []
            else:
                logger.warning(
                    f"Choice source must be a dict, got: {type(choice_source)}"
                )
                return []

        except Exception as e:
            logger.error(f"Error generating choices from source {choice_source}: {e}")
            return []

    def process_choice(
        self,
        choice_id: str,
        step: "StepDefinition",
        context: "ExecutionContext",
        system: "System" = None,
    ) -> "StepResult":
        """Process a user's choice selection."""
        from ..models.flow import StepResult

        # Find the selected choice
        selected_choice = None
        for choice in step.choices:
            if choice.id == choice_id:
                selected_choice = choice
                break

        if not selected_choice:
            return StepResult(
                step_id=step.id, success=False, error=f"Invalid choice ID: {choice_id}"
            )

        try:
            # Execute choice actions
            if selected_choice.actions:
                for action in selected_choice.actions:
                    self._execute_choice_action(action, context)

            # Store the choice result
            context.set_variable("user_choice", choice_id)
            context.set_variable("choice_label", selected_choice.label)

            logger.debug(f"User chose: {selected_choice.label} ({choice_id})")

            # Prepare step result data
            step_result_data = {"choice_id": choice_id, "choice_label": selected_choice.label}

            # Add result for single selections (from compendium/table choices)
            result = context.get_variable("result")
            if result is not None:
                step_result_data["result"] = result

            # Add results if available (for multi-selection choices)
            results = context.get_variable("results")
            if results is not None:
                step_result_data["results"] = results

            return StepResult(
                step_id=step.id,
                success=True,
                data=step_result_data,
                next_step_id=selected_choice.next_step,
            )

        except Exception as e:
            logger.error(f"Error processing choice {choice_id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Choice processing failed: {e}"
            )

    def _execute_choice_action(self, action, context: "ExecutionContext") -> None:
        """Execute an action associated with a choice."""
        action_type = list(action.keys())[0]
        action_data = action[action_type]

        if action_type == "set_value":
            path = action_data["path"]
            value = action_data["value"]

            # Handle dictionary values specially to avoid string conversion
            if isinstance(value, dict):
                # Use dictionary directly without template resolution
                resolved_value = value
                logger.debug(f"Choice action set_value: Using dict directly for {path}")
            else:
                # Resolve templates for non-dict values
                resolved_value = context.resolve_template(str(value))
                logger.debug(f"Choice action set_value: Resolved template for {path}")

            # Set the value
            if path.startswith("outputs."):
                context.set_output(path[8:], resolved_value)
            elif path.startswith("variables."):
                context.set_variable(path[10:], resolved_value)
            else:
                context.set_output(path, resolved_value)

        elif action_type == "flow_call":
            # Handle sub-flow calls - similar to table executor
            flow_id = action_data["flow"]
            inputs = action_data.get("inputs", {})
            logger.debug(f"Choice action flow_call: {flow_id} (inputs: {inputs})")

            # This should be handled by the engine after choice processing
            # For now, we'll log it but not execute it here
            logger.warning(
                "flow_call action in choice step should be handled at step level, not choice level"
            )

        else:
            logger.warning(f"Unknown choice action type: {action_type}")

        # TODO: Add other action types as needed

    def _execute_step_action(
        self,
        action: dict[str, Any],
        context: "ExecutionContext",
        system: "System",
        step_result_data: dict[str, Any] = None,
    ) -> None:
        """Execute a step-level action (including flow calls)."""
        action_type = list(action.keys())[0]

    def _execute_step_action(
        self, action, context: "ExecutionContext", system: "System", step_result_data: dict
    ) -> None:
        """Execute a step action using centralized ActionExecutor."""
        # Delegate all step actions to the centralized ActionExecutor
        try:
            self.action_executor.execute_single_action(
                action, context, step_result_data, system
            )
        except Exception as e:
            logger.error(f"Error executing step action: {e}")

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type == "player_choice"

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate choice step configuration."""
        errors = []

        if not step.choices and not step.choice_source:
            errors.append(
                "Player choice step must have either 'choices' or 'choice_source'"
            )

        # Validate choice IDs are unique
        if step.choices:
            choice_ids = [choice.id for choice in step.choices]
            if len(choice_ids) != len(set(choice_ids)):
                errors.append("Choice IDs must be unique within step")

        return errors

    def _apply_model_defaults(self, entry_data: dict, model_def, system) -> dict:
        """Apply model defaults to entry data."""
        # Create a copy to avoid modifying the original
        result = dict(entry_data)

        # Get all attributes from the model hierarchy (including inherited ones)
        all_attributes = self._get_all_model_attributes(model_def, system)

        # Apply defaults for missing attributes
        for attr_name, attr_def in all_attributes.items():
            if attr_name not in result:
                if hasattr(attr_def, 'default') and attr_def.default is not None:
                    result[attr_name] = attr_def.default

        return result

    def _get_all_model_attributes(self, model_def, system) -> dict:
        """Get all attributes from model definition including inherited ones."""
        all_attributes = {}

        # Process inheritance chain (extends)
        if hasattr(model_def, 'extends') and model_def.extends:
            for parent_model_id in model_def.extends:
                if parent_model_id in system.models:
                    parent_model = system.models[parent_model_id]
                    parent_attributes = self._get_all_model_attributes(parent_model, system)
                    all_attributes.update(parent_attributes)

        # Add this model's own attributes (these override inherited ones)
        if hasattr(model_def, 'attributes'):
            all_attributes.update(model_def.attributes)

        return all_attributes
