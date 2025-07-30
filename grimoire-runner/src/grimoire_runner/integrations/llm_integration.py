"""Integration with LangChain for LLM capabilities."""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

try:
    from langchain_core.prompts import PromptTemplate
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain packages not available, LLM features will be disabled")


class LLMIntegration:
    """Integration with LangChain for LLM content generation."""
    
    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        self._llm = None
        
        if LANGCHAIN_AVAILABLE:
            try:
                self._setup_langchain(provider)
                self._available = True
                logger.debug(f"LLM integration initialized with provider: {provider}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM integration: {e}")
                self._available = False
        else:
            self._available = False
            logger.warning("LLM integration not available")
    
    def _setup_langchain(self, provider: str) -> None:
        """Setup LangChain with the specified provider."""
        if provider == "anthropic":
            self._llm = ChatAnthropic(
                model="claude-3-haiku-20240307",
                temperature=0.7,
                max_tokens=200
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def is_available(self) -> bool:
        """Check if LLM integration is available."""
        return self._available
    
    def generate_content(self, prompt_template: str, context: Dict[str, Any], **kwargs) -> str:
        """Generate content using the LLM."""
        if not self._available:
            return self._generate_fallback_content(prompt_template, context)
        
        try:
            # Create prompt template
            template = PromptTemplate.from_template(prompt_template)
            
            # Format the prompt with context
            formatted_prompt = template.format(**context)
            
            # Update LLM settings if provided
            llm = self._llm
            if kwargs:
                if 'model' in kwargs:
                    # TODO: Update model if different
                    pass
                if 'temperature' in kwargs:
                    llm = llm.bind(temperature=kwargs['temperature'])
                if 'max_tokens' in kwargs:
                    llm = llm.bind(max_tokens=kwargs['max_tokens'])
            
            # Generate response
            response = llm.invoke(formatted_prompt)
            
            # Extract content from response
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating LLM content: {e}")
            return self._generate_fallback_content(prompt_template, context)
    
    def _generate_fallback_content(self, prompt_template: str, context: Dict[str, Any]) -> str:
        """Fallback content generation when LLM is not available."""
        # Very basic template replacement
        try:
            content = prompt_template
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in content:
                    content = content.replace(placeholder, str(value))
            
            # If it still looks like a template, return a generic response
            if '{' in content or 'generate' in prompt_template.lower():
                return "[LLM content would be generated here]"
            
            return content
            
        except Exception as e:
            logger.error(f"Error in fallback content generation: {e}")
            return "[Content generation failed]"
    
    def create_character_description(self, traits: Dict[str, Any]) -> str:
        """Specialized character description generation."""
        template = """
        Create a brief character description based on these traits:
        
        Physical traits:
        - Physique: {physique}
        - Face: {face}
        - Skin: {skin}
        - Hair: {hair}
        - Clothing: {clothing}
        
        Personality traits:
        - Background: {background}
        - Virtue: {virtue}
        - Vice: {vice}
        - Speech: {speech}
        
        Write 2-3 sentences describing this character in a way that brings them to life.
        """
        
        return self.generate_content(template, traits)
    
    def set_provider(self, provider: str) -> None:
        """Change the LLM provider."""
        if self._available:
            try:
                self._setup_langchain(provider)
                self.provider = provider
                logger.info(f"LLM provider changed to: {provider}")
            except Exception as e:
                logger.error(f"Failed to change provider to {provider}: {e}")
