"""Player choice step executor."""

import logging
from typing import TYPE_CHECKING

from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.flow import StepDefinition, StepResult
    from ..models.context_data import ExecutionContext
    from ..models.system import System

logger = logging.getLogger(__name__)


class ChoiceExecutor(BaseStepExecutor):
    """Executor for player choice steps."""
    
    def execute(self, step: "StepDefinition", context: "ExecutionContext", system: "System") -> "StepResult":
        """Execute a player choice step."""
        from ..models.flow import StepResult
        
        try:
            # Execute pre-actions if present
            if step.pre_actions:
                self._execute_pre_actions(step.pre_actions, context)
            
            # For now, we'll return a result that requires user input
            # In an interactive environment, this would present choices to the user
            
            # Resolve choice source if specified
            choices = step.choices
            selection_count = 1  # Default to single selection
            if step.choice_source:
                choices = self._generate_choices_from_source(step.choice_source, context, system)
                # Extract selection count from choice source
                if isinstance(step.choice_source, dict):
                    selection_count = step.choice_source.get('selection_count', 1)
            
            # Resolve template strings in choices
            resolved_choices = []
            for choice in choices:
                resolved_choice = choice
                if choice.label:
                    resolved_choice.label = context.resolve_template(choice.label)
                resolved_choices.append(resolved_choice)
            
            logger.info(f"Player choice step: {step.name}")
            for i, choice in enumerate(resolved_choices):
                logger.info(f"  {i + 1}. {choice.label}")
            
            return StepResult(
                step_id=step.id,
                success=True,
                requires_input=True,
                prompt=step.prompt,
                choices=resolved_choices,
                data={
                    'choice_count': len(resolved_choices),
                    'selection_count': selection_count,
                    'has_choice_source': bool(step.choice_source)
                }
            )
            
        except Exception as e:
            logger.error(f"Error executing choice step {step.id}: {e}")
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"Choice step failed: {e}"
            )
    
    def _execute_pre_actions(self, pre_actions, context: "ExecutionContext") -> None:
        """Execute pre-actions before presenting choices."""
        for action in pre_actions:
            try:
                action_type = list(action.keys())[0]
                action_data = action[action_type]
                
                if action_type == 'display_value':
                    # Display a value from context
                    path = action_data if isinstance(action_data, str) else action_data.get('path', '')
                    try:
                        value = context.resolve_path_value(path)
                        logger.info(f"Display: {value}")
                    except Exception as e:
                        logger.warning(f"Could not display value at path {path}: {e}")
                
                # TODO: Add other pre-action types as needed
                
            except Exception as e:
                logger.error(f"Error executing pre-action {action}: {e}")
    
    def _generate_choices_from_source(self, choice_source, context: "ExecutionContext", system: "System"):
        """Generate choices from a choice source specification."""
        try:
            if isinstance(choice_source, dict):
                if 'table_from_values' in choice_source:
                    # Generate choices from a values table like abilities
                    path = choice_source['table_from_values']
                    selection_count = choice_source.get('selection_count', 1)
                    display_format = choice_source.get('display_format', '{{ key }}: {{ value }}')
                    
                    # Get the data from context
                    data = context.resolve_path_value(path)
                    if isinstance(data, dict):
                        from ..models.flow import ChoiceDefinition
                        choices = []
                        
                        for key, value in data.items():
                            # Create template context for formatting
                            template_context = {
                                'variables': context.variables,
                                'outputs': context.outputs,
                                'inputs': context.inputs,
                                'key': key, 
                                'value': value,
                                **context.variables,
                                **context.outputs
                            }
                            
                            # Use Jinja2 directly for more control
                            from jinja2 import Template
                            template = Template(display_format)
                            label = template.render(template_context)
                            
                            choice = ChoiceDefinition(
                                id=key,
                                label=label,
                                actions=[{
                                    'set_value': {
                                        'path': f'variables.selected_{path.split(".")[-1]}',
                                        'value': key
                                    }
                                }]
                            )
                            choices.append(choice)
                        
                        logger.info(f"Generated {len(choices)} choices from {path}")
                        return choices
                    else:
                        logger.warning(f"Data at path {path} is not a dict: {type(data)}")
                        return []
                
                elif 'compendium' in choice_source:
                    # Generate choices from compendium entries
                    comp_name = choice_source['compendium']
                    comp = system.get_compendium(comp_name)
                    if comp:
                        from ..models.flow import ChoiceDefinition
                        choices = []
                        
                        for entry_id, entry_data in comp.entries.items():
                            choice = ChoiceDefinition(
                                id=entry_id,
                                label=entry_data.get('name', entry_id),
                                actions=[{
                                    'set_value': {
                                        'path': 'variables.selected_item',
                                        'value': entry_id
                                    }
                                }]
                            )
                            choices.append(choice)
                        
                        logger.info(f"Generated {len(choices)} choices from compendium {comp_name}")
                        return choices
                    else:
                        logger.warning(f"Compendium {comp_name} not found")
                        return []
                
                else:
                    logger.warning(f"Unknown choice source format: {choice_source}")
                    return []
            else:
                logger.warning(f"Choice source must be a dict, got: {type(choice_source)}")
                return []
                
        except Exception as e:
            logger.error(f"Error generating choices from source {choice_source}: {e}")
            return []
    
    def process_choice(self, choice_id: str, step: "StepDefinition", context: "ExecutionContext") -> "StepResult":
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
                step_id=step.id,
                success=False,
                error=f"Invalid choice ID: {choice_id}"
            )
        
        try:
            # Execute choice actions
            if selected_choice.actions:
                for action in selected_choice.actions:
                    self._execute_choice_action(action, context)
            
            # Store the choice result
            context.set_variable('user_choice', choice_id)
            context.set_variable('choice_label', selected_choice.label)
            
            logger.info(f"User chose: {selected_choice.label} ({choice_id})")
            
            return StepResult(
                step_id=step.id,
                success=True,
                data={
                    'choice_id': choice_id,
                    'choice_label': selected_choice.label
                },
                next_step_id=selected_choice.next_step
            )
            
        except Exception as e:
            logger.error(f"Error processing choice {choice_id}: {e}")
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"Choice processing failed: {e}"
            )
    
    def _execute_choice_action(self, action, context: "ExecutionContext") -> None:
        """Execute an action associated with a choice."""
        action_type = list(action.keys())[0]
        action_data = action[action_type]
        
        if action_type == 'set_value':
            path = action_data['path']
            value = action_data['value']
            
            # Resolve templates
            resolved_value = context.resolve_template(str(value))
            
            # Set the value
            if path.startswith('outputs.'):
                context.set_output(path[8:], resolved_value)
            elif path.startswith('variables.'):
                context.set_variable(path[10:], resolved_value)
            else:
                context.set_output(path, resolved_value)
        
        # TODO: Add other action types as needed
    
    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, 'value') else str(step.type)
        return step_type == 'player_choice'
    
    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate choice step configuration."""
        errors = []
        
        if not step.choices and not step.choice_source:
            errors.append("Player choice step must have either 'choices' or 'choice_source'")
        
        # Validate choice IDs are unique
        if step.choices:
            choice_ids = [choice.id for choice in step.choices]
            if len(choice_ids) != len(set(choice_ids)):
                errors.append("Choice IDs must be unique within step")
        
        return errors
