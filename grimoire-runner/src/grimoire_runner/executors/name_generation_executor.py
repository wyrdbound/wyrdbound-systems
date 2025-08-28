"""Name generation step executor."""

import logging
from typing import TYPE_CHECKING

from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System
    from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class NameGenerationExecutor(BaseStepExecutor):
    """Executor for name generation steps."""
    
    def __init__(self, action_executor: "ActionExecutor" = None):
        if action_executor is None:
            # Fallback to direct creation for backward compatibility
            from .action_executor import ActionExecutor
            action_executor = ActionExecutor()
        self.action_executor = action_executor

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a name generation step."""
        from ..models.flow import StepResult
        from ..integrations.rng_integration import RNGIntegration

        try:
            step_name = getattr(step, "name", None) or step.id if step else "unknown"
            logger.debug(f"Name generation step: {step_name}")

            # Initialize RNG integration
            rng_integration = RNGIntegration()
            
            # Get the new field configuration
            generator = getattr(step, "generator", "wyrdbound-rng")  # Default to wyrdbound-rng
            output_variable = getattr(step, "output_variable", "generated_name")
            settings = getattr(step, "settings", {})
            
            # Debug output to see what we're getting from the step
            logger.debug(f"[NAME_GEN] Step attributes: generator={generator}, output_variable={output_variable}, settings={settings}")
            logger.debug(f"[NAME_GEN] Step dir: {dir(step)}")
            
            # Use the specified generator with the settings
            logger.debug(f"Using name generator: {generator} with settings: {settings}")
            generated_name = rng_integration.generate_name(generator, **settings)

            # Store the generated name in the context using the specified output variable
            context.set_variable("result", generated_name)
            context.set_variable(output_variable, generated_name)

            # Execute step actions if present using the centralized ActionExecutor
            if step.actions:
                step_data = {
                    "result": generated_name, 
                    output_variable: generated_name,
                    "generated_name": generated_name  # For backward compatibility
                }
                self.action_executor.execute_actions(step.actions, context, step_data, system)

            logger.debug(f"Generated name: '{generated_name}' using generator: {generator} with settings: {settings}")

            return StepResult(
                step_id=step.id if step else "unknown",
                success=True,
                data={
                    "result": generated_name,
                    output_variable: generated_name,
                    "generated_name": generated_name,  # For backward compatibility
                    "generator": generator,
                    "settings": settings,
                    "using_wyrdbound_rng": rng_integration.is_available(),
                },
            )

        except Exception as e:
            step_id = step.id if step and hasattr(step, "id") else "unknown"
            logger.error(f"Error executing name generation step {step_id}: {e}")
            return StepResult(
                step_id=step_id, success=False, error=f"Name generation step failed: {e}"
            )

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type == "name_generation"

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate name generation step configuration."""
        errors = []

        # generator is optional - defaults to "wyrdbound-rng"
        generator = getattr(step, "generator", "wyrdbound-rng")
        output_variable = getattr(step, "output_variable", None)
        settings = getattr(step, "settings", {})
        
        # Validate output_variable if provided
        if output_variable and not isinstance(output_variable, str):
            errors.append(f"output_variable must be a string, got {type(output_variable)}")
        
        # Validate settings is a dictionary
        if not isinstance(settings, dict):
            errors.append(f"settings must be a dictionary, got {type(settings)}")
        
        # Generator-specific validation can be added here in the future
        # For now, we let each generator (wyrdbound-rng, etc.) handle its own validation

        return errors
