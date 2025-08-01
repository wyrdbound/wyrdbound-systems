"""LLM generation step executor using LangChain."""

import logging
from typing import TYPE_CHECKING

from ..integrations.llm_integration import LLMIntegration
from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class LLMExecutor(BaseStepExecutor):
    """Executor for LLM generation steps."""

    def __init__(self):
        self.llm_integration = LLMIntegration()

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute an LLM generation step."""
        from ..models.flow import StepResult

        try:
            # Check if LLM is enabled/available
            if not self.llm_integration.is_available():
                logger.warning(f"LLM not available for step {step.id}, skipping")
                return StepResult(
                    step_id=step.id,
                    success=True,
                    data={"skipped": True, "reason": "llm_not_available"},
                )

            # Get the prompt template
            prompt_template = self._get_prompt_template(step, system)
            if not prompt_template:
                return StepResult(
                    step_id=step.id,
                    success=False,
                    error="No prompt template found for LLM generation",
                )

            # Prepare prompt data
            prompt_data = {}
            if step.prompt_data:
                for key, value in step.prompt_data.items():
                    prompt_data[key] = context.resolve_template(str(value))

            # Get LLM settings
            settings = step.llm_settings or {}

            # Generate content
            generated_content = self.llm_integration.generate_content(
                prompt_template=prompt_template,
                context=prompt_data,
                **settings.__dict__ if hasattr(settings, "__dict__") else {},
            )

            logger.info(f"LLM generation completed for step {step.id}")
            logger.debug(f"Generated content: {generated_content[:100]}...")

            # Store result in context for actions
            context.set_variable("llm_result", generated_content)

            return StepResult(
                step_id=step.id,
                success=True,
                data={
                    "generated_content": generated_content,
                    "prompt_data": prompt_data,
                    "settings": settings.__dict__
                    if hasattr(settings, "__dict__")
                    else {},
                },
                prompt=step.prompt,
            )

        except Exception as e:
            logger.error(f"Error executing LLM generation step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"LLM generation failed: {e}"
            )

    def _get_prompt_template(self, step: "StepDefinition", system: "System") -> str:
        """Get the prompt template for the step."""
        if step.prompt_id:
            # Load from system prompts (TODO: implement prompt loading)
            logger.warning(
                f"Prompt loading from system not yet implemented: {step.prompt_id}"
            )
            return f"Generate content based on the provided context. Prompt ID: {step.prompt_id}"

        # Use the step prompt as template
        if step.prompt:
            return step.prompt

        # Default template
        return "Generate appropriate content based on the provided context."

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type == "llm_generation"

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate LLM generation step configuration."""
        errors = []

        if not step.prompt and not step.prompt_id:
            errors.append(
                "LLM generation step must have either 'prompt' or 'prompt_id'"
            )

        return errors
