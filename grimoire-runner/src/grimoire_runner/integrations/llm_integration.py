"""Integration with LangChain for LLM capabilities."""

import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

# Core dependency check
try:
    # We only need the base LangChain classes, not PromptTemplate
    from langchain_core.language_models import BaseLanguageModel
    LANGCHAIN_CORE_AVAILABLE = True
except ImportError:
    LANGCHAIN_CORE_AVAILABLE = False
    logger.error("langchain_core not available. Install with: pip install langchain-core")

# Provider-specific dependencies
ANTHROPIC_AVAILABLE = False
OLLAMA_AVAILABLE = False
OPENAI_AVAILABLE = False

# Only check provider modules if core is available
if LANGCHAIN_CORE_AVAILABLE:
    # Check Ollama support (our default) - prefer newer package
    try:
        from langchain_ollama import OllamaLLM
        OLLAMA_AVAILABLE = True
        logger.debug("Using langchain-ollama (recommended)")
    except ImportError:
        try:
            from langchain_community.llms import Ollama as OllamaLLM
            OLLAMA_AVAILABLE = True
            logger.debug("Using langchain-community Ollama (deprecated)")
        except ImportError:
            logger.warning("Ollama integration not available. Install with: pip install langchain-ollama")
    
    # Check Anthropic support
    try:
        from langchain_anthropic import ChatAnthropic
        ANTHROPIC_AVAILABLE = True
    except ImportError:
        logger.debug("Anthropic integration not available. Install with: pip install langchain-anthropic")
    
    # Check OpenAI support
    try:
        from langchain_openai import ChatOpenAI
        OPENAI_AVAILABLE = True
    except ImportError:
        logger.debug("OpenAI integration not available. Install with: pip install langchain-openai")


class LLMIntegration:
    """Integration with LangChain for LLM content generation."""

    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self._llm = None
        
        # Check core dependency first
        if not LANGCHAIN_CORE_AVAILABLE:
            raise ImportError(
                "LangChain Core is required but not installed. "
                "Please install with: pip install langchain-core"
            )
        
        # Check if requested provider is available
        self._check_provider_availability(provider)
        
        try:
            self._setup_langchain(provider)
            logger.debug(f"LLM integration initialized with provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM integration: {e}")
            raise RuntimeError(f"Failed to initialize LLM integration: {e}") from e

    def _check_provider_availability(self, provider: str) -> None:
        """Check if the requested provider is available and provide installation instructions if not."""
        if provider == "ollama" and not OLLAMA_AVAILABLE:
            raise ImportError(
                "Ollama integration requested but langchain-community is not installed. "
                "Please install with: pip install langchain-community"
            )
        elif provider == "anthropic" and not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "Anthropic integration requested but langchain-anthropic is not installed. "
                "Please install with: pip install langchain-anthropic"
            )
        elif provider == "openai" and not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI integration requested but langchain-openai is not installed. "
                "Please install with: pip install langchain-openai"
            )

    def _setup_langchain(self, provider: str) -> None:
        """Setup LangChain with the specified provider."""
        if provider == "anthropic":
            self._llm = ChatAnthropic(
                model="claude-3-haiku-20240307", temperature=0.7, max_tokens=200
            )
        elif provider == "ollama":
            if not OLLAMA_AVAILABLE:
                raise ValueError("Ollama integration not available. Install with: pip install langchain-ollama")
            # Default to a common model, can be overridden
            model_name = os.environ.get("OLLAMA_MODEL", "gemma2")
            self._llm = OllamaLLM(model=model_name, temperature=0.7)
        elif provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError("OpenAI integration not available. Install with: pip install langchain-openai")
            self._llm = ChatOpenAI(
                model="gpt-3.5-turbo", temperature=0.7, max_tokens=200
            )
        else:
            supported_providers = self.get_available_providers()
            raise ValueError(
                f"Unsupported LLM provider: '{provider}'. "
                f"Available providers: {', '.join(supported_providers) or 'none'}"
            )

    def get_available_providers(self) -> list[str]:
        """Get list of available LLM providers."""
        providers = []
        
        if ANTHROPIC_AVAILABLE:
            providers.append("anthropic")
            
        if OLLAMA_AVAILABLE:
            providers.append("ollama")
            
        if OPENAI_AVAILABLE:
            providers.append("openai")
            
        return providers

    def is_provider_available(self, provider: str) -> bool:
        """Check if a specific provider is available."""
        return provider in self.get_available_providers()

    def is_available(self) -> bool:
        """Check if LLM integration is available."""
        return LANGCHAIN_CORE_AVAILABLE and self._llm is not None

    def generate_content(
        self, prompt_template: str, context: dict[str, Any], **kwargs
    ) -> str:
        """Generate content using the LLM."""
        if not self.is_available():
            raise RuntimeError(
                f"LLM integration is not available. Provider '{self.provider}' failed to initialize."
            )

        try:
            # Use Jinja2 templating for consistency with GRIMOIRE spec
            from jinja2 import Template
            
            template = Template(prompt_template)
            formatted_prompt = template.render(**context)

            # Update LLM settings if provided
            llm = self._llm
            
            # For Ollama, we need to create a new instance with updated parameters
            # because bind() doesn't work reliably with all parameter types
            if self.provider == "ollama" and kwargs:
                from langchain_ollama import OllamaLLM
                llm_kwargs = {}
                if hasattr(self._llm, 'model'):
                    llm_kwargs['model'] = self._llm.model
                if hasattr(self._llm, 'base_url'):
                    llm_kwargs['base_url'] = self._llm.base_url
                
                # Override with provided kwargs
                if "temperature" in kwargs:
                    llm_kwargs['temperature'] = kwargs["temperature"]
                elif hasattr(self._llm, 'temperature'):
                    llm_kwargs['temperature'] = self._llm.temperature
                    
                if "num_predict" in kwargs:
                    llm_kwargs['num_predict'] = kwargs["num_predict"]
                elif "max_tokens" in kwargs:
                    llm_kwargs['num_predict'] = kwargs["max_tokens"]
                
                llm = OllamaLLM(**llm_kwargs)
            else:
                # For other providers, use bind() method
                if kwargs:
                    if "temperature" in kwargs:
                        llm = llm.bind(temperature=kwargs["temperature"])
                    if "max_tokens" in kwargs:
                        llm = llm.bind(max_tokens=kwargs["max_tokens"])

            # Generate response
            response = llm.invoke(formatted_prompt)

            # Extract content from response
            if hasattr(response, "content"):
                return response.content
            else:
                return str(response)

        except Exception as e:
            logger.error(f"Error generating LLM content: {e}")
            raise RuntimeError(f"LLM content generation failed: {e}") from e

    def create_character_description(self, traits: dict[str, Any]) -> str:
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
        try:
            self._setup_langchain(provider)
            self.provider = provider
            logger.info(f"LLM provider changed to: {provider}")
        except Exception as e:
            logger.error(f"Failed to change provider to {provider}: {e}")
            raise RuntimeError(f"Failed to change provider to {provider}: {e}") from e
