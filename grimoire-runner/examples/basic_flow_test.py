#!/usr/bin/env python3
"""
Basic example of using the GRIMOIRE runner to execute a character creation flow.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import grimoire_runner
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner import GrimoireEngine


def main():
    """Run a basic character creation example."""
    
    # Path to the Knave 1e system (relative to this file)
    system_path = Path(__file__).parent.parent.parent / "systems" / "knave_1e"
    
    if not system_path.exists():
        print(f"Error: System path not found: {system_path}")
        print("Please ensure you're running this from the grimoire-runner directory")
        return 1
    
    try:
        # Create the engine
        engine = GrimoireEngine()
        
        # Load the system
        print(f"Loading GRIMOIRE system: {system_path}")
        system = engine.load_system(system_path)
        
        print(f"Successfully loaded: {system.name} ({system.id})")
        print(f"Available flows: {', '.join(system.list_flows())}")
        
        # Create execution context
        context = engine.create_execution_context()
        
        # Execute character creation flow
        flow_id = "character_creation"
        if flow_id in system.flows:
            print(f"\nExecuting flow: {flow_id}")
            result = engine.execute_flow(flow_id, context, system)
            
            if result.success:
                print("✓ Flow execution completed successfully!")
                
                if result.outputs:
                    print("\nGenerated character:")
                    for output_id, output_value in result.outputs.items():
                        print(f"  {output_id}: {output_value}")
                        
                print(f"\nSteps executed: {len(result.step_results)}")
            else:
                print(f"✗ Flow execution failed: {result.error}")
                if result.completed_at_step:
                    print(f"  Failed at step: {result.completed_at_step}")
                return 1
        else:
            print(f"Flow '{flow_id}' not found in system")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
