#!/usr/bin/env python3
"""
Minimal CLI tool for GRIMOIRE engine development and testing.

This is a development tool to test engine changes without the complexity
of the full Rich TUI interface. It provides simple command-line interaction
with event logging and user input prompting using blinker signals.

Phase 1, Step 4: Enhanced to use blinker signal-based event system.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict

from .services.ui_service import GrimoireUIService, InputType
from .services import event_signals
from .services.event_signals import (
    SystemLoadedData, SessionCreatedData, FlowStartedData, StepStartedData,
    StepCompletedData, InputRequiredData, ChoiceRequiredData, FlowCompletedData,
    ErrorOccurredData, FlowCancelledData, DisplayValueData, LogMessageData
)
from .utils.debug import debug_print, set_debug_enabled


class SimpleEventCLI:
    """Minimal CLI that uses blinker signals for event handling."""
    
    def __init__(self, debug: bool = False):
        self.ui_service = GrimoireUIService()
        self.debug = debug
        self.session_id = None
        self.waiting_for_input = False
        self.waiting_for_choice = False
        self.execution_complete = False
        self.execution_successful = False
        
        # Connect to blinker signals instead of subscribing to events
        self._connect_signals()
        
        debug_print(f"[SIMPLE_CLI] SimpleEventCLI initialized (debug={debug})")
    
    def _connect_signals(self):
        """Connect to all blinker signals."""
        event_signals.system_loaded.connect(self._handle_system_loaded)
        event_signals.session_created.connect(self._handle_session_created)
        event_signals.flow_started.connect(self._handle_flow_started)
        event_signals.step_started.connect(self._handle_step_started)
        event_signals.step_completed.connect(self._handle_step_completed)
        event_signals.input_required.connect(self._handle_input_required)
        event_signals.choice_required.connect(self._handle_choice_required)
        event_signals.flow_completed.connect(self._handle_flow_completed)
        event_signals.error_occurred.connect(self._handle_error_occurred)
        event_signals.flow_cancelled.connect(self._handle_flow_cancelled)
        event_signals.display_value.connect(self._handle_display_value)
        event_signals.log_message.connect(self._handle_log_message)
    
    def _handle_system_loaded(self, sender, **kwargs):
        """Handle system loaded event."""
        data = kwargs.get('data')
        debug_print(f"System loaded: {data.system_name} ({data.system_id})")
        debug_print(f"  Path: {data.system_path}")
        debug_print(f"  Flows: {data.flow_count}, Models: {data.model_count}")
        print(f"Loaded system: {data.system_name}")
    
    def _handle_session_created(self, sender, **kwargs):
        """Handle session created event."""
        data = kwargs.get('data')
        self.session_id = data.session_id
        debug_print(f"Session created: {data.session_id} for flow {data.flow_id}")
    
    def _handle_flow_started(self, sender, **kwargs):
        """Handle flow started event."""
        data = kwargs.get('data')
        debug_print(f"Flow started: {data.flow_id} with inputs: {data.inputs}")
        print(f"Starting Flow: {data.flow_name}")
    
    def _handle_step_started(self, sender=None, **kwargs):
        """Handle step started signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: step_started")
        step = data.step_info
        step_number = data.step_number
        
        # Add emoji for different step types
        step_emoji = "📋"
        if step.type == "name_generation":
            step_emoji = "🎲"
        elif step.type == "dice_roll":
            step_emoji = "🎲"
        elif step.type == "player_input":
            step_emoji = "💬"
        elif step.type == "player_choice":
            step_emoji = "🔀"
        elif step.type == "table_roll":
            step_emoji = "📊"
        
        # Use step name if available, fallback to step id
        step_display_name = step.name or step.id
        print(f"\n{step_emoji} Step {step_number}: {step_display_name} ({step.type})")
        if step.description:
            print(f"   Description: {step.description}")
        
        # Add specific handling for name generation steps
        if step.type == "name_generation":
            print(f"   🎯 Generating random name...")
    
    def _handle_step_completed(self, sender=None, **kwargs):
        """Handle step completed signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: step_completed")
        step = data.step_info
        step_number = data.step_number
        
        # Add emoji for different step types
        step_emoji = "✅"
        if step.type == "name_generation":
            step_emoji = "🎯"
        elif step.type == "dice_roll":
            step_emoji = "🎲"
        elif step.type == "player_input":
            step_emoji = "💬"
        elif step.type == "player_choice":
            step_emoji = "🔀"
        elif step.type == "table_roll":
            step_emoji = "📊"
        
        # Show resolved message if available (for result_message templates)
        if data.step_data and "resolved_message" in data.step_data:
            print(f"💬 {data.step_data['resolved_message']}")
        
        print(f"{step_emoji} Step {step_number} ({step.id}) completed")
        
        # Show any result data (excluding internal fields)
        if data.step_data:
            for key, value in data.step_data.items():
                if key not in ["resolved_message", "internal_state"]:
                    # Special formatting for name generation results
                    if step.type == "name_generation" and key == "generated_name":
                        print(f"   🎯 Generated name: {value}")
                    else:
                        print(f"   {key}: {value}")

    def _handle_input_required(self, sender=None, **kwargs):
        """Handle input required signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: input_required")
        self.waiting_for_input = True
        print(f"\n💬 {data.prompt}")
        
        # Get user input
        try:
            user_input = input("Enter input: ").strip()
            
            # Provide input to the service
            self.ui_service.provide_user_input(self.session_id, user_input)
            self.waiting_for_input = False
            
        except KeyboardInterrupt:
            print("\n⏹️  Cancelled by user")
            self.ui_service.cancel_execution(self.session_id)

    def _handle_choice_required(self, sender=None, **kwargs):
        """Handle choice required signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: choice_required")
        self.waiting_for_choice = True
        print(f"\n📋 {data.prompt}")
        
        selection_count = getattr(data, 'selection_count', 1)
        
        if selection_count > 1:
            # Handle multiple choice selection
            self._handle_multiple_choices(data, selection_count)
        else:
            # Handle single choice selection
            self._handle_single_choice(data)

    def _handle_single_choice(self, data):
        """Handle single choice selection."""
        print("Available options:")
        
        for i, choice in enumerate(data.choices, 1):
            description = f" - {choice.description}" if choice.description else ""
            print(f"  {i}. {choice.label}{description}")
        
        # Get user choice
        try:
            while True:
                try:
                    choice_input = input(f"\nEnter choice (1-{len(data.choices)}): ").strip()
                    choice_index = int(choice_input) - 1
                    if 0 <= choice_index < len(data.choices):
                        selected_choice = data.choices[choice_index]
                        self.ui_service.make_choice(self.session_id, selected_choice.id)
                        self.waiting_for_choice = False
                        break
                    else:
                        print(f"❌ Invalid choice. Please enter a number between 1 and {len(data.choices)}")
                except ValueError:
                    print("❌ Please enter a valid number")
                    
        except KeyboardInterrupt:
            print("\n⏹️  Cancelled by user")
            self.ui_service.cancel_execution(self.session_id)

    def _handle_multiple_choices(self, data, selection_count):
        """Handle multiple choice selection."""
        print(f"You need to select {selection_count} options:")
        selected_choices = []
        available_choices = data.choices.copy()
        
        try:
            for selection_num in range(selection_count):
                print(f"\n🔢 Selection {selection_num + 1} of {selection_count}:")
                print("Available options:")
                
                # Show remaining choices
                choice_map = {}
                for i, choice in enumerate(available_choices, 1):
                    description = f" - {choice.description}" if choice.description else ""
                    print(f"  {i}. {choice.label}{description}")
                    choice_map[str(i)] = choice
                
                # Show previously selected items
                if selected_choices:
                    selected_labels = [c.label for c in selected_choices]
                    print(f"\n✅ Already selected: {', '.join(selected_labels)}")
                
                # Get user choice
                while True:
                    try:
                        choice_input = input(f"\nEnter choice (1-{len(available_choices)}): ").strip()
                        
                        if choice_input in choice_map:
                            selected_choice = choice_map[choice_input]
                            selected_choices.append(selected_choice)
                            print(f"✅ Selected: {selected_choice.label}")
                            
                            # Remove from available choices
                            available_choices.remove(selected_choice)
                            break
                        else:
                            choices_text = " / ".join([str(i) for i in range(1, len(available_choices) + 1)])
                            print(f"❌ Invalid choice. Please choose from: {choices_text}")
                    except ValueError:
                        print("❌ Please enter a valid number")
            
            # All choices made, process multiple selection
            choice_ids = [choice.id for choice in selected_choices]
            self.ui_service.make_multiple_choices(self.session_id, choice_ids)
            self.waiting_for_choice = False
            
        except KeyboardInterrupt:
            print("\n⏹️  Cancelled by user")
            self.ui_service.cancel_execution(self.session_id)

    def _handle_flow_completed(self, sender=None, **kwargs):
        """Handle flow completed signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: flow_completed")
        self.execution_complete = True
        self.execution_successful = True
        
        print(f"\n🎉 Flow '{data.flow_id}' completed successfully!")
        print(f"   Steps executed: {data.step_count}")
        
        # Show final outputs if any
        if data.outputs:
            print("\n📊 Final outputs:")
            for output_id, output_value in data.outputs.items():
                print(f"   {output_id}: {output_value}")
        
        # Show variables if any (debug mode only)
        if self.debug and data.variables:
            print("\n🔧 Variables (debug):")
            for var_name, var_value in data.variables.items():
                print(f"   {var_name}: {var_value}")

    def _handle_error_occurred(self, sender=None, **kwargs):
        """Handle error occurred signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: error_occurred")
        self.execution_complete = True
        self.execution_successful = False
        
        print(f"❌ Error occurred: {data.error_message}")
        if data.step_id:
            print(f"   At step: {data.step_id}")
        if data.error_type != "execution_error":
            print(f"   Error type: {data.error_type}")

    def _handle_flow_cancelled(self, sender=None, **kwargs):
        """Handle flow cancelled signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: flow_cancelled")
        self.execution_complete = True
        self.execution_successful = False
        
        print(f"⏹️  Flow '{data.flow_id}' cancelled: {data.reason}")

    def _handle_display_value(self, sender=None, **kwargs):
        """Handle display value signal with structured data formatting."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: display_value")
        
        # Format the display value based on the structured data
        formatted_output = self._format_display_value(data.path, data.value)
        print(formatted_output)

    def _format_display_value(self, path: str, value: Any) -> str:
        """Format a display value based on its type and content.
        
        This is the presentation layer handling the formatting of structured data.
        Generic formatting that doesn't assume specific data structures.
        """
        from rich.console import Console
        from rich.table import Table
        from io import StringIO
        
        # Create a console for formatting
        console = Console(file=StringIO(), width=100, force_terminal=True)
        
        if value is None:
            return f"Display Value: {path}\n   (No value)"
        
        # Handle different value types generically
        if isinstance(value, dict):
            console.print(f"Display Value: {path}")
            
            if value:
                # Create a vertical table: key-value pairs as rows
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="white")
                
                # Add each key-value pair as a row
                for key, val in value.items():
                    # Format key to be more readable
                    formatted_key = key.replace('_', ' ').title()
                    formatted_val = str(val) if val is not None else "(none)"
                    table.add_row(formatted_key, formatted_val)
                
                console.print(table)
            else:
                console.print("   (empty)")
            
            # Get the formatted output
            output = console.file.getvalue()
            console.file.close()
            return output.strip()
        
        elif isinstance(value, list):
            if not value:
                return f"Display Value: {path}\n   (empty list)"
            else:
                # Format list with summary
                if len(value) == 1:
                    return f"Display Value: {path}\n   [1 item: {value[0]}]"
                else:
                    sample = ", ".join(str(item) for item in value[:2])
                    suffix = ", ..." if len(value) > 2 else ""
                    return f"Display Value: {path}\n   [{len(value)} items: {sample}{suffix}]"
        
        else:
            # Simple values
            if isinstance(value, str):
                display_value = f'"{value}"' if len(str(value)) < 50 else f'"{str(value)[:47]}..."'
            else:
                display_value = str(value)
            
            return f"Display Value: {path}\n   {display_value}"

    def _handle_log_message(self, sender=None, **kwargs):
        """Handle log message signal."""
        data = kwargs.get('data')
        debug_print(f"[SIMPLE_CLI] Received signal: log_message")
        
        # Print the log message
        print(f"📝 {data.resolved_message}")
    
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
        description="Minimal GRIMOIRE CLI for engine development using blinker signals",
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
