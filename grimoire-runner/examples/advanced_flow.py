#!/usr/bin/env python3
"""
Example of advanced flow execution with custom context variables.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import grimoire_runner
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner import GrimoireEngine


def main():
    """Run an advanced example with custom context."""
    
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
        
        # Create execution context with custom variables
        context = engine.create_execution_context()
        
        # Add some custom context variables
        context.variables.update({
            "character_name": "Grimjaw the Bold",
            "campaign_setting": "The Forgotten Realms",
            "experience_level": "veteran",
            "preferred_background": "soldier"
        })
        
        print(f"Custom context variables: {list(context.variables.keys())}")
        
        # Execute character creation flow
        flow_id = "character_creation"
        if flow_id in system.flows:
            print(f"\nExecuting flow: {flow_id}")
            result = engine.execute_flow(flow_id, context, system)
            
            if result.success:
                print("✓ Flow execution completed successfully!")
                
                # Display detailed results
                print(f"\nExecution Summary:")
                print(f"  Total steps: {len(result.step_results)}")
                print(f"  Duration: {result.execution_time:.3f}s")
                
                if result.outputs:
                    print("\nGenerated outputs:")
                    for output_id, output_value in result.outputs.items():
                        print(f"  {output_id}: {output_value}")
                
                # Show step-by-step results
                print("\nStep-by-step execution:")
                for i, step_result in enumerate(result.step_results):
                    status = "✓" if step_result.success else "✗"
                    print(f"  {i+1}. {status} {step_result.step_id}")
                    if step_result.output:
                        print(f"      Output: {step_result.output}")
                    if step_result.error:
                        print(f"      Error: {step_result.error}")
                        
                # Show final context state
                print("\nFinal context variables:")
                for key, value in context.variables.items():
                    if not key.startswith('_'):  # Skip internal variables
                        print(f"  {key}: {value}")
                        
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
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
