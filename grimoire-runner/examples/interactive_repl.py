#!/usr/bin/env python3
"""
Example of using the interactive REPL to explore GRIMOIRE systems.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import grimoire_runner
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.ui.interactive import InteractiveREPL


def main():
    """Start an interactive REPL session."""
    
    # Path to the Knave 1e system (relative to this file)
    system_path = Path(__file__).parent.parent.parent / "systems" / "knave_1e"
    
    if not system_path.exists():
        print(f"Error: System path not found: {system_path}")
        print("Please ensure you're running this from the grimoire-runner directory")
        return 1
    
    print("Starting GRIMOIRE Interactive REPL")
    print("=" * 40)
    print(f"System path: {system_path}")
    print()
    print("Available commands:")
    print("  load <system_path>    - Load a GRIMOIRE system")
    print("  execute <flow_id>     - Execute a flow")
    print("  context               - Show current context")
    print("  flows                 - List available flows")
    print("  help                  - Show help")
    print("  quit                  - Exit REPL")
    print()
    
    try:
        repl = InteractiveREPL()
        
        # Auto-load the system
        print(f"Auto-loading system: {system_path}")
        repl.do_load(str(system_path))
        print()
        
        # Start the REPL
        repl.cmdloop()
        
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
