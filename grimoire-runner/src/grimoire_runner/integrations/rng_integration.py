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

    def load_name_generator(self, file_path: str) -> Any | None:
        """Load and cache a name generator from file."""
        if not self._available:
            return None

        try:
            if file_path not in self.generators:
                # Load the generator using wyrdbound-rng
                generator = wyrdbound_rng.Generator.from_file(file_path)
                self.generators[file_path] = generator
                logger.debug(f"Loaded name generator: {file_path}")

            return self.generators[file_path]
        except Exception as e:
            logger.error(f"Failed to load name generator from {file_path}: {e}")
            return None

    def generate_name(self, generator_id: str, **kwargs) -> str:
        """Generate a name using a loaded generator."""
        if not self._available:
            return self._generate_fallback_name(generator_id, **kwargs)

        try:
            if generator_id in self.generators:
                generator = self.generators[generator_id]
                return generator.generate(**kwargs)
            else:
                logger.warning(f"Name generator '{generator_id}' not loaded")
                return self._generate_fallback_name(generator_id, **kwargs)
        except Exception as e:
            logger.error(f"Error generating name with {generator_id}: {e}")
            return self._generate_fallback_name(generator_id, **kwargs)

    def _generate_fallback_name(self, generator_id: str, **kwargs) -> str:
        """Fallback name generation."""
        import random

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

        first = random.choice(first_names)
        last = random.choice(last_names)

        return f"{first} {last}"

    def list_generators(self) -> list[str]:
        """List all loaded generators."""
        return list(self.generators.keys())
