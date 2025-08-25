#!/usr/bin/env python3
"""
Minimal CLI tool for GRIMOIRE engine development and testing.

This is a development tool to test engine changes without the complexity
of the full Rich TUI interface. It provides simple command-line interaction
with basic logging and user input prompting.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

from .core.engine import GrimoireEngine
from .utils.debug import debug_print, set_debug_enabled


def log_event(event_type: str, data: Any = None) -> None:
    """Simple event logging for development."""
    if data:
        print(f"[EVENT] {event_type}: {data}")
    else:
        print(f"[EVENT] {event_type}")


def prompt_for_input(prompt: str, input_type: str = "text") -> str:
    """Simple input prompting."""
    if input_type == "text":
        return input(f"{prompt}: ")
    else:
        # For now, treat all other types as text
        return input(f"{prompt} ({input_type}): ")


def execute_flow_interactively(
    engine: GrimoireEngine, flow_id: str, context, system
) -> bool:
    """Execute a flow step by step, handling user input interactively."""
    log_event("FlowStarted", {"flow_id": flow_id})
    
    try:
        step_results = []
        
        # Use the step_through_flow method for interactive execution
        for step_result in engine.step_through_flow(flow_id, context, system):
            log_event("StepStarted", {"step_id": step_result.step_id})
            
            if not step_result.success:
                log_event("StepFailed", {
                    "step_id": step_result.step_id,
                    "error": step_result.error
                })
                print(f"❌ Step {step_result.step_id} failed: {step_result.error}")
                return False
            
            if step_result.requires_input:
                # Find the step to determine the type
                flow = system.get_flow(flow_id)
                step = flow.get_step(step_result.step_id)
                step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
                
                if step_type == "player_choice" and hasattr(step_result, 'choices') and step_result.choices:
                    # Handle choice steps - display options and get selection
                    log_event("ChoiceRequired", {
                        "step_id": step_result.step_id,
                        "prompt": step_result.prompt,
                        "choice_count": len(step_result.choices)
                    })
                    
                    print(f"\n📋 {step_result.prompt or 'Choose an option:'}")
                    print("Available options:")
                    for i, choice in enumerate(step_result.choices, 1):
                        description = f" - {choice.description}" if choice.description else ""
                        print(f"  {i}. {choice.label}{description}")
                    
                    # Get user choice
                    while True:
                        try:
                            choice_input = input(f"\nEnter choice (1-{len(step_result.choices)}): ").strip()
                            choice_index = int(choice_input) - 1
                            
                            if 0 <= choice_index < len(step_result.choices):
                                selected_choice = step_result.choices[choice_index]
                                break
                            else:
                                print(f"❌ Invalid choice. Please enter a number between 1 and {len(step_result.choices)}")
                        except ValueError:
                            print("❌ Please enter a valid number")
                        except KeyboardInterrupt:
                            print("\n⏹️  Cancelled by user")
                            return False
                    
                    # Process the choice
                    from .executors.choice_executor import ChoiceExecutor
                    choice_executor = ChoiceExecutor(engine)
                    choice_result = choice_executor.process_choice(selected_choice.id, step, context, system)
                    
                    if not choice_result.success:
                        log_event("ChoiceProcessingFailed", {
                            "step_id": step_result.step_id,
                            "error": choice_result.error
                        })
                        print(f"❌ Choice processing failed: {choice_result.error}")
                        return False
                    
                    log_event("ChoiceProcessed", {
                        "step_id": step_result.step_id,
                        "choice_id": selected_choice.id,
                        "choice_label": selected_choice.label
                    })
                    print(f"✅ Selected: {selected_choice.label}")
                    
                elif step_type == "player_input":
                    # Handle text input steps
                    log_event("InputRequired", {
                        "step_id": step_result.step_id,
                        "prompt": step_result.prompt
                    })
                    
                    # Get user input
                    user_input = prompt_for_input(step_result.prompt or "Enter input")
                    
                    # Use PlayerInputExecutor to process the input
                    from .executors.player_input_executor import PlayerInputExecutor
                    input_executor = PlayerInputExecutor()
                    input_result = input_executor.process_input(user_input, step, context, system)
                    
                    if not input_result.success:
                        log_event("InputProcessingFailed", {
                            "step_id": step_result.step_id,
                            "error": input_result.error
                        })
                        print(f"❌ Input processing failed: {input_result.error}")
                        return False
                    
                    log_event("InputProcessed", {
                        "step_id": step_result.step_id,
                        "input": user_input
                    })
                    print(f"✅ Input processed: {user_input}")
                else:
                    print(f"⚠️  Unknown input step type: {step_type}")
                    return False
            else:
                log_event("StepCompleted", {
                    "step_id": step_result.step_id,
                    "data": step_result.data
                })
                print(f"✅ Step {step_result.step_id} completed")
                
                # Show any result data
                if step_result.data:
                    for key, value in step_result.data.items():
                        if key != "resolved_message":  # Skip internal message
                            print(f"   {key}: {value}")
            
            step_results.append(step_result)
        
        log_event("FlowCompleted", {"step_count": len(step_results)})
        print(f"\n🎉 Flow '{flow_id}' completed successfully!")
        
        # Show final outputs if any
        if hasattr(context, 'outputs') and context.outputs:
            print("\n📤 Final outputs:")
            for output_id, output_value in context.outputs.items():
                print(f"   {output_id}: {output_value}")
        
        return True
        
    except Exception as e:
        log_event("FlowError", {"error": str(e)})
        print(f"❌ Flow execution error: {e}")
        return False


def main():
    """Main entry point for the simple CLI."""
    parser = argparse.ArgumentParser(
        description="Minimal GRIMOIRE CLI for engine development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  grimoire system.yaml character_creation
  grimoire --debug system.yaml test_flow
  grimoire systems/knave_1e combat_flow
        """
    )
    
    parser.add_argument(
        "system_path",
        type=Path,
        help="Path to GRIMOIRE system directory or YAML file"
    )
    
    parser.add_argument(
        "flow_id",
        help="ID of the flow to execute"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output showing internal engine processing"
    )
    
    parser.add_argument(
        "--inputs",
        type=Path,
        help="YAML file containing initial input values"
    )
    
    args = parser.parse_args()
    
    # Set debug mode
    if args.debug:
        set_debug_enabled(True)
        print("🐛 Debug mode enabled")
    
    try:
        # Load inputs if provided
        initial_inputs = {}
        if args.inputs:
            import yaml
            try:
                with open(args.inputs) as f:
                    initial_inputs = yaml.safe_load(f) or {}
                print(f"📥 Loaded inputs from {args.inputs}")
            except Exception as e:
                print(f"❌ Error loading inputs file: {e}")
                return 1
        
        # Create engine
        log_event("EngineCreated")
        engine = GrimoireEngine()
        
        # Load system
        log_event("SystemLoading", {"path": str(args.system_path)})
        print(f"📂 Loading system: {args.system_path}")
        system = engine.load_system(args.system_path)
        
        log_event("SystemLoaded", {
            "id": system.id,
            "name": system.name,
            "flows": len(system.flows)
        })
        print(f"✅ Loaded: {system.name} ({system.id})")
        print(f"   Flows: {len(system.flows)}")
        print(f"   Models: {len(system.models)}")
        
        # Check if flow exists
        if args.flow_id not in system.flows:
            available_flows = list(system.flows.keys())
            print(f"❌ Flow '{args.flow_id}' not found")
            print(f"   Available flows: {', '.join(available_flows)}")
            return 1
        
        # Create execution context
        log_event("ContextCreated")
        context = engine.create_execution_context(system, **initial_inputs)
        
        # Execute flow interactively
        print(f"\n🚀 Starting flow: {args.flow_id}")
        success = execute_flow_interactively(engine, args.flow_id, context, system)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Execution cancelled by user")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
