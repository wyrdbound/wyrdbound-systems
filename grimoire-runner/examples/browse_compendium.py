#!/usr/bin/env python3
"""
Example of using the compendium browser to explore system content.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import grimoire_runner
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.ui.browser import CompendiumBrowser
from grimoire_runner import GrimoireEngine


def main():
    """Browse compendium content interactively."""
    
    # Path to the Knave 1e system (relative to this file)
    system_path = Path(__file__).parent.parent.parent / "systems" / "knave_1e"
    
    if not system_path.exists():
        print(f"Error: System path not found: {system_path}")
        print("Please ensure you're running this from the grimoire-runner directory")
        return 1
    
    try:
        # Load the system
        engine = GrimoireEngine()
        system = engine.load_system(system_path)
        
        print(f"Loaded system: {system.name}")
        print(f"Compendium entries: {len(system.compendium.entries)}")
        print()
        
        # Start the browser
        browser = CompendiumBrowser(system.compendium)
        browser.browse()
        
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
