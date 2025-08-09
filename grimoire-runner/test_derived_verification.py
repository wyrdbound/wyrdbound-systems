#!/usr/bin/env python3
"""Quick test to verify that derived attributes actually work in the execution engine."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.models.context_data import ExecutionContext

def test_derived_attributes_work():
    """Test that derived attributes actually work in flow execution."""
    
    # Load the test system
    test_systems_dir = Path(__file__).parent / "tests_new" / "systems"
    
    # Execute the flow
    engine = GrimoireEngine()
    engine.load_system(test_systems_dir / "model_validations")  # Load the system from path
    
    # Create execution context
    context = ExecutionContext()
    
    # Execute the flow
    results = engine.execute_flow("test_derived_flow", context)
    
    print("=== Flow Execution Results ===")
    print(f"Success: {results.success}")
    print(f"Outputs: {results.outputs}")
    print(f"Context outputs: {results.context.outputs if hasattr(results, 'context') else 'N/A'}")
    
    if "character" in results.outputs:
        character = results.outputs["character"]
        print(f"\n=== Character Data ===")
        print(f"Name: {character.get('name')}")
        print(f"Base AC: {character.get('armor_class_base')}")
        print(f"Dex Mod: {character.get('dexterity_modifier')}")
        print(f"Derived AC: {character.get('armor_class')} (should be 15 = 12 + 3)")
        print(f"Current HP: {character.get('current_hit_points')}")
        print(f"Is Unconscious: {character.get('is_unconscious')} (should be False)")
        
        # Check if derived attributes were calculated
        if character.get('armor_class') == 15:
            print("\n✅ DERIVED ATTRIBUTES WORK! AC calculated correctly")
        else:
            print(f"\n❌ Derived AC calculation failed. Expected 15, got {character.get('armor_class')}")
            
        if character.get('is_unconscious') == False:
            print("✅ DERIVED ATTRIBUTES WORK! is_unconscious calculated correctly")
        else:
            print(f"❌ Derived is_unconscious calculation failed. Expected False, got {character.get('is_unconscious')}")
    else:
        print("❌ No character output found")
    
    return results

if __name__ == "__main__":
    test_derived_attributes_work()
