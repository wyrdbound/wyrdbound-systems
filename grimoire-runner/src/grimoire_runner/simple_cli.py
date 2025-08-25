#!/usr/bin/env python3
"""
Minimal CLI tool for GRIMOIRE engine development and testing.

This is a development tool to test engine changes without the complexity
of the full Rich TUI interface. It provides simple command-line interaction
with event logging and user input prompting using the new UI service interface.

Phase 1, Step 4: Enhanced to use the new service interface and event system.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict

from .services.ui_service import (
    GrimoireUIService,
    ExecutionStatus,
    InputType,
    # Events
    SystemLoadedEvent,
    SessionCreatedEvent,
    FlowStartedEvent,
    StepStartedEvent,
    StepCompletedEvent,
    InputRequiredEvent,
    ChoiceRequiredEvent,
    FlowCompletedEvent,
    ErrorOccurredEvent,
    FlowCancelledEvent,
)
from .utils.debug import debug_print, set_debug_enabled


class SimpleEventCLI:
    """Minimal CLI that uses the UI service interface and logs events."""
    
    def __init__(self, debug: bool = False):
        self.ui_service = GrimoireUIService()
        self.debug = debug
        self.session_id = None
        self.waiting_for_input = False
        self.waiting_for_choice = False
        self.execution_complete = False
        self.execution_successful = False
        
        # Subscribe to all events
        self.ui_service.subscribe_to_events(self._handle_event)
        
        debug_print(f"[SIMPLE_CLI] SimpleEventCLI initialized (debug={debug})")
    
    def _handle_event(self, event) -> None:
        """Handle events from the UI service."""
        event_name = event.__class__.__name__
        debug_print(f"[SIMPLE_CLI] Received event: {event_name}")
        
        if isinstance(event, SystemLoadedEvent):
            self._handle_system_loaded(event)
        elif isinstance(event, SessionCreatedEvent):
            self._handle_session_created(event)
        elif isinstance(event, FlowStartedEvent):
            self._handle_flow_started(event)
        elif isinstance(event, StepStartedEvent):
            self._handle_step_started(event)
        elif isinstance(event, StepCompletedEvent):
            self._handle_step_completed(event)
        elif isinstance(event, InputRequiredEvent):
            self._handle_input_required(event)
        elif isinstance(event, ChoiceRequiredEvent):
            self._handle_choice_required(event)
        elif isinstance(event, FlowCompletedEvent):
            self._handle_flow_completed(event)
        elif isinstance(event, ErrorOccurredEvent):
            self._handle_error_occurred(event)
        elif isinstance(event, FlowCancelledEvent):
            self._handle_flow_cancelled(event)
        else:
            debug_print(f"[SIMPLE_CLI] Unhandled event type: {event_name}")
    
    def _handle_system_loaded(self, event: SystemLoadedEvent) -> None:
        """Handle system loaded event."""
        print(f"✅ Loaded: {event.system_name} ({event.system_id})")
        print(f"   Flows: {event.flow_count}")
        print(f"   Models: {event.model_count}")
    
    def _handle_session_created(self, event: SessionCreatedEvent) -> None:
        """Handle session created event."""
        self.session_id = event.session_id
        debug_print(f"[SIMPLE_CLI] Session created: {self.session_id}")
    
    def _handle_flow_started(self, event: FlowStartedEvent) -> None:
        """Handle flow started event."""
        print(f"\n🚀 Starting flow: {event.flow_id}")
        if event.inputs:
            print(f"   With inputs: {event.inputs}")
    
    def _handle_step_started(self, event: StepStartedEvent) -> None:
        """Handle step started event."""
        step = event.step_info
        print(f"\n📋 Step: {step.id} ({step.type})")
        if step.name:
            print(f"   Name: {step.name}")
        if step.description:
            print(f"   Description: {step.description}")
    
    def _handle_step_completed(self, event: StepCompletedEvent) -> None:
        """Handle step completed event."""
        step = event.step_info
        print(f"✅ Step {step.id} completed")
        
        # Show any result data (excluding internal fields)
        if event.step_data:
            for key, value in event.step_data.items():
                if key not in ["resolved_message", "internal_state"]:
                    print(f"   {key}: {value}")
    
    def _handle_input_required(self, event: InputRequiredEvent) -> None:
        """Handle input required event."""
        self.waiting_for_input = True
        print(f"\n💬 {event.prompt}")
        
        # Get user input
        try:
            user_input = input("Enter input: ").strip()
            
            # Provide input to the service
            self.ui_service.provide_user_input(self.session_id, user_input)
            self.waiting_for_input = False
            print(f"✅ Input provided: {user_input}")
            
        except KeyboardInterrupt:
            print("\n⏹️  Cancelled by user")
            self.ui_service.cancel_execution(self.session_id)
        except Exception as e:
            print(f"❌ Error providing input: {e}")
            self.ui_service.cancel_execution(self.session_id)
    
    def _handle_choice_required(self, event: ChoiceRequiredEvent) -> None:
        """Handle choice required event."""
        self.waiting_for_choice = True
        print(f"\n📋 {event.prompt}")
        print("Available options:")
        
        for i, choice in enumerate(event.choices, 1):
            description = f" - {choice.description}" if choice.description else ""
            print(f"  {i}. {choice.label}{description}")
        
        # Get user choice
        try:
            while True:
                choice_input = input(f"\nEnter choice (1-{len(event.choices)}): ").strip()
                try:
                    choice_index = int(choice_input) - 1
                    if 0 <= choice_index < len(event.choices):
                        selected_choice = event.choices[choice_index]
                        break
                    else:
                        print(f"❌ Invalid choice. Please enter a number between 1 and {len(event.choices)}")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            # Make choice through the service
            self.ui_service.make_choice(self.session_id, selected_choice.id)
            self.waiting_for_choice = False
            print(f"✅ Selected: {selected_choice.label}")
            
        except KeyboardInterrupt:
            print("\n⏹️  Cancelled by user")
            self.ui_service.cancel_execution(self.session_id)
        except Exception as e:
            print(f"❌ Error making choice: {e}")
            self.ui_service.cancel_execution(self.session_id)
    
    def _handle_flow_completed(self, event: FlowCompletedEvent) -> None:
        """Handle flow completed event."""
        self.execution_complete = True
        self.execution_successful = True
        
        print(f"\n🎉 Flow '{event.flow_id}' completed successfully!")
        print(f"   Steps executed: {event.step_count}")
        
        # Show final outputs if any
        if event.outputs:
            print("\n📤 Final outputs:")
            for output_id, output_value in event.outputs.items():
                print(f"   {output_id}: {output_value}")
        
        # Show final variables if any (excluding system variables)
        if event.variables:
            print("\n📊 Final variables:")
            for var_name, var_value in event.variables.items():
                if not var_name.startswith('_'):  # Skip internal variables
                    print(f"   {var_name}: {var_value}")
    
    def _handle_error_occurred(self, event: ErrorOccurredEvent) -> None:
        """Handle error occurred event."""
        self.execution_complete = True
        self.execution_successful = False
        
        print(f"❌ Error occurred: {event.error_message}")
        if event.step_id:
            print(f"   At step: {event.step_id}")
        if event.error_type != "execution_error":
            print(f"   Error type: {event.error_type}")
    
    def _handle_flow_cancelled(self, event: FlowCancelledEvent) -> None:
        """Handle flow cancelled event."""
        self.execution_complete = True
        self.execution_successful = False
        
        print(f"⏹️  Flow '{event.flow_id}' cancelled: {event.reason}")
    
    def load_system(self, system_path: Path) -> bool:
        """Load a system using the UI service."""
        try:
            print(f"📂 Loading system: {system_path}")
            system_info = self.ui_service.load_system(system_path)
            return True
        except Exception as e:
            print(f"❌ Error loading system: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def list_flows(self, system_id: str) -> bool:
        """List flows in the loaded system."""
        try:
            flows = self.ui_service.list_flows(system_id)
            if flows:
                print(f"\n📋 Available flows in {system_id}:")
                for flow in flows:
                    print(f"  • {flow.id}: {flow.name or 'No name'}")
                    if flow.description:
                        print(f"    {flow.description}")
                    print(f"    Steps: {flow.step_count}, Inputs: {'Yes' if flow.requires_inputs else 'No'}, Outputs: {'Yes' if flow.produces_outputs else 'No'}")
            else:
                print(f"❌ No flows found in system {system_id}")
            return True
        except Exception as e:
            print(f"❌ Error listing flows: {e}")
            return False
    
    def execute_flow(self, system_id: str, flow_id: str, inputs: Dict[str, Any] = None) -> bool:
        """Execute a flow using the UI service."""
        try:
            # Start flow execution
            session = self.ui_service.start_flow_execution(system_id, flow_id, inputs)
            self.session_id = session.session_id
            
            # Wait for execution to complete
            while not self.execution_complete:
                time.sleep(0.1)  # Small delay to prevent busy waiting
            
            return self.execution_successful
            
        except Exception as e:
            print(f"❌ Error executing flow: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False


def log_event(event_type: str, data: Any = None) -> None:
    """Simple event logging for development (legacy function)."""
    if data:
        print(f"[EVENT] {event_type}: {data}")
    else:
        print(f"[EVENT] {event_type}")


def prompt_for_input(prompt: str, input_type: str = "text") -> str:
    """Simple input prompting (legacy function)."""
    if input_type == "text":
        return input(f"{prompt}: ")
    else:
        # For now, treat all other types as text
        return input(f"{prompt} ({input_type}): ")


def execute_flow_interactively(
    engine, flow_id: str, context, system
) -> bool:
    """Legacy function - replaced by new SimpleEventCLI."""
    print("❌ execute_flow_interactively is deprecated - use SimpleEventCLI instead")
    return False


def main():
    """Main entry point for the simple CLI."""
    parser = argparse.ArgumentParser(
        description="Minimal GRIMOIRE CLI for engine development using the new UI service interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  grimoire system.yaml character_creation
  grimoire --debug system.yaml test_flow
  grimoire systems/knave_1e combat_flow
  grimoire --list-flows system.yaml
        """
    )
    
    parser.add_argument(
        "system_path",
        type=Path,
        help="Path to GRIMOIRE system directory or YAML file"
    )
    
    parser.add_argument(
        "flow_id",
        nargs="?",
        help="ID of the flow to execute (omit to list flows)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output showing internal engine processing"
    )
    
    parser.add_argument(
        "--list-flows",
        action="store_true",
        help="List available flows in the system"
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
        # Create the CLI interface
        cli = SimpleEventCLI(debug=args.debug)
        
        # Load the system
        if not cli.load_system(args.system_path):
            return 1
        
        # Extract system ID from path for now (this could be improved)
        system_id = args.system_path.stem if args.system_path.is_file() else args.system_path.name
        
        # If listing flows or no flow specified, list flows
        if args.list_flows or not args.flow_id:
            cli.list_flows(system_id)
            if not args.flow_id:
                return 0
        
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
        
        # Execute the flow
        success = cli.execute_flow(system_id, args.flow_id, initial_inputs)
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
