"""Integration with wyrdbound-rng package for name generation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    import wyrdbound_rng

    RNG_AVAILABLE = True
except ImportError:
    RNG_AVAILABLE = False
    logger.warning(
        "wyrdbound-rng package not available, using fallback name generation"
    )


class RNGIntegration:
    """Integration with wyrdbound-rng package for name generation."""

    def __init__(self):
        self.generators: dict[str, Any] = {}

        if RNG_AVAILABLE:
            try:
                self._available = True
                logger.debug("wyrdbound-rng integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize wyrdbound-rng: {e}")
                self._available = False
        else:
            self._available = False
            logger.warning("Using fallback name generation")

    def is_available(self) -> bool:
        """Check if wyrdbound-rng is available."""
        return self._available

    def load_name_generator(self, corpus: str) -> Any | None:
        """Load and cache a name generator for a corpus."""
        if not self._available:
            return None

        try:
            if corpus not in self.generators:
                # Load the generator using wyrdbound-rng with the corpus name
                # The Generator constructor takes the name source directly
                generator = wyrdbound_rng.Generator(corpus)
                self.generators[corpus] = generator
                logger.debug(f"Loaded name generator for corpus: {corpus}")

            return self.generators[corpus]
        except Exception as e:
            logger.error(f"Failed to load name generator for corpus {corpus}: {e}")
            return None

    def generate_name(self, generator_id: str, **kwargs) -> str:
        """Generate a name using the specified generator/corpus."""
        if not self._available:
            raise RuntimeError("wyrdbound-rng package not available")

        if generator_id == "wyrdbound-rng":
            # For wyrdbound-rng, use the corpus from kwargs to determine which data to load
            corpus = kwargs.get("corpus", "generic-fantasy")
            max_length = kwargs.get("max_length", 15)
            segmenter = kwargs.get("segmenter", "fantasy")
            algorithm = kwargs.get("algorithm", "bayesian")
            min_probability = kwargs.get("min_probability")
            best_of = kwargs.get("best_of")
            
            logger.debug(f"Attempting to generate name with corpus: {corpus}, max_length: {max_length}, algorithm: {algorithm}, segmenter: {segmenter}")
            if min_probability is not None:
                logger.debug(f"Using min_probability: {min_probability}")
            if best_of is not None:
                logger.debug(f"Using best_of: {best_of}")
            
            # Load generator for the corpus if not already loaded
            if corpus not in self.generators:
                logger.debug(f"Generator for corpus '{corpus}' not loaded, loading now...")
                generator = self.load_name_generator(corpus)
                if not generator:
                    raise RuntimeError(f"Failed to load generator for corpus: {corpus}")
            
            generator = self.generators[corpus]
            logger.debug(f"Using generator for corpus: {corpus}")
            
            # Handle best_of for bayesian algorithm
            if algorithm == "bayesian" and best_of is not None and best_of > 1:
                logger.debug(f"Generating {best_of} names and selecting the best one")
                best_name = None
                best_probability = 0.0
                
                for i in range(best_of):
                    # Generate name using wyrdbound-rng API
                    generation_params = {"max_len": max_length, "algorithm": algorithm}
                    
                    # Add min_probability if specified
                    if min_probability is not None:
                        # Convert string to float if needed
                        if isinstance(min_probability, str):
                            min_prob_float = float(min_probability)
                        else:
                            min_prob_float = min_probability
                        generation_params["min_probability_threshold"] = min_prob_float
                    
                    logger.debug(f"Generating name {i+1}/{best_of} with params: {generation_params}")
                    generated_name = generator.generate_name(**generation_params)
                    
                    # Check if this name has a higher probability
                    name_probability = getattr(generated_name, 'probability', 0.0)
                    logger.debug(f"Generated '{generated_name}' with probability: {name_probability}")
                    
                    if best_name is None or name_probability > best_probability:
                        best_name = generated_name
                        best_probability = name_probability
                        logger.debug(f"New best name: '{best_name}' with probability: {best_probability}")
                
                logger.debug(f"Selected best name '{best_name}' from {best_of} candidates with probability: {best_probability}")
                return best_name
            else:
                # Generate single name using wyrdbound-rng API
                generation_params = {"max_len": max_length, "algorithm": algorithm}
                
                # Add min_probability if specified
                if min_probability is not None:
                    # Convert string to float if needed
                    if isinstance(min_probability, str):
                        min_prob_float = float(min_probability)
                    else:
                        min_prob_float = min_probability
                    generation_params["min_probability_threshold"] = min_prob_float
                
                logger.debug(f"Calling generator.generate_name with params: {generation_params}")
                generated_name = generator.generate_name(**generation_params)
                logger.debug(f"Generated name '{generated_name}' using corpus '{corpus}' with params: {generation_params}")
                
                return generated_name
        else:
            # Handle other generators in the future
            raise RuntimeError(f"Unknown generator '{generator_id}' - only 'wyrdbound-rng' is supported")

    def _generate_fallback_name(self, generator_id: str, **kwargs) -> str:
        """Fallback name generation."""
        import random

        # Extract max_length from kwargs
        max_length = kwargs.get("max_length", 15)

        # Very basic fallback names
        first_names = [
            "Aiden",
            "Bran",
            "Cora",
            "Dara",
            "Ewan",
            "Fynn",
            "Gwen",
            "Hale",
            "Ivy",
            "Jace",
            "Kira",
            "Liam",
            "Maya",
            "Nora",
            "Owen",
            "Piper",
            "Quinn",
            "Raven",
            "Sage",
            "Tara",
            "Ursa",
            "Vale",
            "Wren",
            "Xara",
            "Yara",
            "Zara",
        ]

        last_names = [
            "Ashworth",
            "Blackwood",
            "Crowe",
            "Darkmore",
            "Ember",
            "Frost",
            "Grimm",
            "Hawke",
            "Ironside",
            "Kane",
            "Lightbringer",
            "Morrow",
            "Nightfall",
            "Oakheart",
            "Pierce",
            "Quicksilver",
            "Raven",
            "Stone",
            "Thornfield",
            "Underwood",
            "Vale",
            "Whitmore",
            "Youngblood",
            "Zephyr",
        ]

        # Generate name and trim to max_length if needed
        first = random.choice(first_names)
        
        # If we have space for a last name within max_length, add it
        if len(first) + 1 < max_length:  # +1 for space
            last = random.choice(last_names)
            full_name = f"{first} {last}"
            
            # Trim if too long
            if len(full_name) > max_length:
                return first  # Just use first name if full name is too long
            else:
                return full_name
        else:
            # Just return first name, trimmed if necessary
            return first[:max_length]

    def list_generators(self) -> list[str]:
        """List all loaded generators."""
        return list(self.generators.keys())
