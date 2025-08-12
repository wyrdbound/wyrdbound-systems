"""LLM generation step executor using LangChain."""

import json
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

import jsonschema

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
        super().__init__()
        self.llm_integration = LLMIntegration()

    def _extract_json_from_response(self, response: str) -> tuple[dict, bool]:
        """
        Extract JSON from LLM response, handling various formats.
        Returns (json_dict, success_flag)
        """
        import json
        import re
        
        # Try different extraction patterns
        patterns = [
            # JSON in markdown code blocks
            r'```json\s*\n(.*?)\n\s*```',
            r'```\s*\n(\{.*?\})\s*\n```',
            # JSON objects in text
            r'\{[^{}]*\}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.MULTILINE)
            for match in matches:
                try:
                    parsed = json.loads(match.strip())
                    return parsed, True
                except json.JSONDecodeError:
                    continue
        
        # Try parsing the entire response as JSON
        try:
            parsed = json.loads(response.strip())
            return parsed, True
        except json.JSONDecodeError:
            pass
            
        return {}, False

    def _validate_json_schema(self, data: dict, schema: dict) -> tuple[bool, list[str]]:
        """
        Validate JSON data against schema.
        Returns (is_valid, error_messages)
        """
        try:
            jsonschema.validate(data, schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [str(e)]
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]

    def _create_cleanup_template(self, raw_response: str, schema: dict, validation_errors: list[str]) -> str:
        """Create a cleanup template for failed validation."""
        errors_text = "\n".join(f"- {error}" for error in validation_errors)
        
        template = f"""The following LLM response did not match the expected JSON schema:

RESPONSE:
{raw_response}

EXPECTED SCHEMA:
{schema}

VALIDATION ERRORS:
{errors_text}

Please provide ONLY the corrected JSON object with no additional text or formatting."""
        return template

    def _attempt_llm_call_with_validation(
        self, 
        prompt_template: str,
        prompt_data: dict,
        validation_config,
        settings: dict
    ) -> tuple[dict, bool, int, str, list[str]]:
        """
        Make LLM call with validation and automatic cleanup.
        Returns (result_json, success, attempts, raw_response, errors)
        """
        max_attempts = getattr(validation_config, 'max_attempts', 3)
        cleanup_enabled = getattr(validation_config, 'cleanup_enabled', True)
        
        logger.debug(f"Starting validation-aware LLM generation: max_attempts={max_attempts}, cleanup_enabled={cleanup_enabled}")
        
        for attempt in range(max_attempts):
            logger.debug(f"Attempt {attempt + 1}/{max_attempts}")
            
            # Make the LLM call
            if attempt == 0:
                current_template = prompt_template
            else:
                # Add guidance for retry attempts
                current_template = f"{prompt_template}\n\nIMPORTANT: Please respond with valid JSON only, no additional text or formatting."
                logger.debug(f"Retry attempt with modified template")
            
            # Log resolved prompt for this attempt (debug only)
            from jinja2 import Template
            try:
                template = Template(current_template)
                resolved_prompt = template.render(**prompt_data)
                logger.debug(f"Resolved Prompt (attempt {attempt + 1}):\n{resolved_prompt}")
            except Exception as e:
                logger.debug(f"Could not resolve prompt for logging: {e}")
            
            raw_response = self.llm_integration.generate_content(
                prompt_template=current_template,
                context=prompt_data,
                **settings
            )
            
            logger.debug(f"Raw LLM Response (attempt {attempt + 1}):\n{raw_response}")
            
            # Extract JSON
            json_data, json_extracted = self._extract_json_from_response(raw_response)
            logger.debug(f"JSON extraction successful: {json_extracted}")
            
            if not json_extracted:
                logger.debug("JSON extraction failed")
                if attempt < max_attempts - 1 and cleanup_enabled:
                    # Try cleanup call
                    cleanup_template = f"""The following response could not be parsed as JSON:

{{{{ raw_response }}}}

Please provide the same information as a valid JSON object with no additional text or formatting."""
                    
                    logger.debug("Attempting cleanup call for JSON extraction")
                    cleanup_response = self.llm_integration.generate_content(
                        prompt_template=cleanup_template,
                        context={"raw_response": raw_response},
                        **settings
                    )
                    logger.debug(f"Cleanup response:\n{cleanup_response}")
                    
                    cleanup_json, cleanup_extracted = self._extract_json_from_response(cleanup_response)
                    
                    if cleanup_extracted:
                        json_data = cleanup_json
                        raw_response = cleanup_response
                        logger.debug("Cleanup successful, JSON extracted")
                    else:
                        logger.debug("Cleanup failed, retrying")
                        continue  # Try again with next attempt
                else:
                    return {}, False, attempt + 1, raw_response, ["Could not extract JSON from response"]
            
            # Validate against schema if provided
            if validation_config.type == "json_schema" and hasattr(validation_config, 'schema'):
                logger.debug("Validating against JSON schema")
                is_valid, errors = self._validate_json_schema(json_data, validation_config.schema)
                logger.debug(f"Schema validation result: valid={is_valid}")
                
                if not is_valid:
                    logger.debug(f"Schema validation errors: {errors}")
                    if attempt < max_attempts - 1 and cleanup_enabled:
                        # Try cleanup call with schema
                        cleanup_template = self._create_cleanup_template(raw_response, validation_config.schema, errors)
                        logger.debug("Attempting cleanup call for schema validation")
                        cleanup_response = self.llm_integration.generate_content(
                            prompt_template=cleanup_template,
                            context={},
                            **settings
                        )
                        logger.debug(f"Schema cleanup response:\n{cleanup_response}")
                        
                        cleanup_json, cleanup_extracted = self._extract_json_from_response(cleanup_response)
                        
                        if cleanup_extracted:
                            cleanup_valid, cleanup_errors = self._validate_json_schema(cleanup_json, validation_config.schema)
                            if cleanup_valid:
                                logger.debug("Schema cleanup successful")
                                return cleanup_json, True, attempt + 1, cleanup_response, []
                        logger.debug("Schema cleanup failed, retrying")
                        continue  # Try again with next attempt
                    else:
                        return json_data, False, attempt + 1, raw_response, errors
            
            # Success!
            logger.debug(f"LLM generation successful on attempt {attempt + 1}")
            return json_data, True, attempt + 1, raw_response, []
        
        # All attempts failed
        logger.debug(f"All {max_attempts} attempts failed")
        return {}, False, max_attempts, raw_response, ["Maximum validation attempts exceeded"]

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute an LLM generation step."""
        from ..models.flow import StepResult

        try:
            logger.debug(f"=== Executing LLM Generation Step: {step.id} ===")
            
            # Check if LLM is enabled/available
            if not self.llm_integration.is_available():
                logger.warning(f"LLM not available for step {step.id}, skipping")
                # Provide a safe fallback so templates like {{ result }} or {{ llm_result }} don't explode
                context.set_variable("llm_result", "")
                return StepResult(
                    step_id=step.id,
                    success=True,
                    data={
                        "skipped": True,
                        "reason": "llm_not_available",
                        "result": "",
                    },
                )

            # Log provider and model information
            logger.debug(f"LLM Provider: {self.llm_integration.provider}")
            if hasattr(self.llm_integration._llm, 'model'):
                logger.debug(f"LLM Model: {self.llm_integration._llm.model}")
            elif hasattr(self.llm_integration._llm, 'model_name'):
                logger.debug(f"LLM Model: {self.llm_integration._llm.model_name}")

            # Get the prompt template
            prompt_template = self._get_prompt_template(step, system)
            if not prompt_template:
                return StepResult(
                    step_id=step.id,
                    success=False,
                    error="No prompt template found for LLM generation",
                )

            # Log the template before resolution
            logger.debug(f"Prompt Template (before resolution):\n{prompt_template}")

            # Prepare prompt data
            prompt_data = {}
            if step.prompt_data:
                logger.debug("Resolving template inputs:")
                for key, value in step.prompt_data.items():
                    resolved_value = context.resolve_template(str(value))
                    prompt_data[key] = resolved_value
                    logger.debug(f"  {key}: '{value}' -> '{resolved_value}'")
            else:
                logger.debug("No prompt_data defined for this step")

            # Get LLM settings
            settings = step.llm_settings or {}
            if settings:
                logger.debug(f"LLM Settings: {settings}")
            else:
                logger.debug("No LLM settings defined for this step")
            
            # Check if validation is configured
            if step.validation:
                logger.debug(f"Validation configured: type={step.validation.type}, max_attempts={step.validation.max_attempts}")
                
                # Use validation-aware generation
                result_json, success, attempts, raw_response, errors = self._attempt_llm_call_with_validation(
                    prompt_template,
                    prompt_data,
                    step.validation,
                    settings.__dict__ if hasattr(settings, "__dict__") else {}
                )
                
                logger.debug(f"Validation results: success={success}, attempts={attempts}")
                if not success:
                    logger.debug(f"Validation errors: {errors}")
                
                # Set context variables based on validation results
                context.set_variable("llm_validation_successful", success)
                context.set_variable("llm_validation_attempts", attempts)
                context.set_variable("raw_llm_response", raw_response)
                
                if success:
                    context.set_variable("llm_result", result_json)
                    generated_content = result_json
                    logger.debug(f"Validation successful, result: {result_json}")
                else:
                    context.set_variable("llm_validation_errors", errors)
                    
                    # Handle failure based on configuration
                    on_failure = getattr(step.validation, 'on_failure', 'continue')
                    logger.debug(f"Handling validation failure with strategy: {on_failure}")
                    
                    if on_failure == 'fallback' and hasattr(step.validation, 'fallback_value'):
                        context.set_variable("llm_fallback_used", True)
                        context.set_variable("llm_result", step.validation.fallback_value)
                        generated_content = step.validation.fallback_value
                        logger.debug(f"Using fallback value: {step.validation.fallback_value}")
                    elif on_failure == 'fail':
                        logger.debug("Failing step due to validation failure")
                        return StepResult(
                            step_id=step.id,
                            success=False,
                            error=f"LLM validation failed: {'; '.join(errors)}"
                        )
                    else:  # continue
                        context.set_variable("llm_fallback_used", False)
                        context.set_variable("llm_result", result_json)
                        generated_content = result_json
                        logger.debug(f"Continuing with invalid result: {result_json}")
            else:
                logger.debug("No validation configured, using direct LLM generation")
                
                # Log resolved prompt (debug only)
                from jinja2 import Template
                try:
                    template = Template(prompt_template)
                    resolved_prompt = template.render(**prompt_data)
                    logger.debug(f"Resolved Prompt:\n{resolved_prompt}")
                except Exception as e:
                    logger.debug(f"Could not resolve prompt for logging: {e}")
                
                # Use original non-validated generation
                generated_content = self.llm_integration.generate_content(
                    prompt_template=prompt_template,
                    context=prompt_data,
                    **(settings.__dict__ if hasattr(settings, "__dict__") else {}),
                )
                
                # Log raw response
                logger.debug(f"Raw LLM Response:\n{generated_content}")
                
                # Store result in context for actions and provide a common 'result' key
                context.set_variable("llm_result", generated_content)

            return StepResult(
                step_id=step.id,
                success=True,
                data={
                    "result": generated_content,
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
            # Load from system prompts
            prompt = system.get_prompt(step.prompt_id)
            if prompt:
                logger.debug(f"Loaded prompt '{prompt.name}' (ID: {step.prompt_id})")
                return prompt.prompt_template
            else:
                logger.warning(f"Prompt not found in system: {step.prompt_id}")
                return f"Generate content based on the provided context. Prompt ID: {step.prompt_id}"

        # Use the step prompt as template
        if step.prompt:
            logger.debug("Using step-level prompt template")
            return step.prompt

        # Default template
        logger.debug("Using default prompt template")
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
