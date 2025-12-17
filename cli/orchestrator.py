"""Orchestrator for handling workflow execution and user interaction with monitoring."""

import logging
import uuid
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent import (
    RESUME_APPROVED,
    RESUME_DENIED,
)
from agent.state import (
    NODE_APPROVAL,
    NODE_EXECUTE,
    NODE_UNDERSTANDING,
)
from ui.console_ui import Emoji

# Import monitoring components
from monitoring.callbacks import AlertingCallbackHandler

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Handles workflow execution and user interaction with monitoring."""

    def __init__(self, workflow, ui, config):
        self.workflow = workflow
        self.ui = ui
        self.config = config
        # Get monitoring handler from workflow if available
        self.monitoring_handler = getattr(workflow, '_monitoring_handler', None)

    def execute_command(
        self,
        command: str,
        device: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> dict:
        """Execute user command with full workflow and approval loop."""
        # Add device context
        full_command = self._build_prompt(command, device)

        if session_id is None:
            session_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": session_id}}

        # Initialize monitoring for this session
        if self.monitoring_handler:
            self.monitoring_handler.set_session_id(session_id)
            self.monitoring_handler.reset_session()  # Reset for new session

        # Run the workflow using streaming to update UI
        final_state = self._run_workflow_stream(
            {"messages": [HumanMessage(content=full_command)]},
            config,
            initial_status="🧠 Analyzing request...",
        )

        # Handle approval loop if needed
        result = self._handle_approval_loop(session_id, final_state)

        # Log session statistics
        if self.monitoring_handler:
            stats = self.monitoring_handler.get_session_stats()
            logger.info(f"Session {session_id} completed. Stats: {stats}")

        return result

    def _build_prompt(self, command: str, device: Optional[str] = None) -> str:
        """Build prompt with device context."""
        if device:
            return f"Execute on {device}: {command}"
        return command

    def _run_workflow_stream(self, input_data: dict, config: dict, initial_status: str) -> dict:
        """Run the workflow in streaming mode and update UI spinner."""
        final_state = None

        with self.ui.thinking_status(initial_status) as status:
            try:
                # stream() yields events as the graph progresses
                for event in self.workflow.stream(input_data, config):
                    self._update_spinner_status(event, status)

                    # Keep track of the latest state from the event
                    # Events are usually dicts like {'node_name': {state_updates}}
                    for value in event.values():
                        if isinstance(value, dict):
                            final_state = value
            except Exception as e:
                # If an interrupt happens, stream() might raise or just stop.
                # In LangGraph, it usually just stops.
                # Real exceptions we should log.
                # However, GraphInterrupt is not an exception you catch here usually.
                logger.debug(f"Stream finished or interrupted. Details: {e}")

        # If we didn't get a final state from the stream (e.g. immediate interrupt),
        # fetch it from the graph.
        if final_state is None:
            final_state = self.workflow.get_state(config).values

        return final_state

    def _update_spinner_status(self, event: dict, status):
        """Update the spinner text based on the workflow node event."""
        # Check which node just finished or sent an update
        if NODE_UNDERSTANDING in event:
            status.update(f"[bold cyan]{Emoji.THINKING} Plan generated. Proceeding...[/bold cyan]")
        elif NODE_EXECUTE in event:
            status.update(f"[bold green]{Emoji.WRITE} Formatting final report...[/bold green]")
        elif NODE_APPROVAL in event:
            status.update(f"[bold red]{Emoji.APPROVAL} Approval required...[/bold red]")

        # When entering Execute, we want to say "Executing..."
        # But stream events happen *after* the node.
        # So if 'understanding' finished, we are likely moving to 'execute' or 'approval'.
        if NODE_UNDERSTANDING in event:
            # Look ahead logic isn't perfect in stream, but we can set the message for the NEXT step
            # If we routed to Execute, the next long wait is execution.
            status.update(
                f"[bold yellow]{Emoji.EXECUTING} Connecting to devices & running commands...[/bold yellow]"
            )

    def _handle_approval_loop(self, session_id: str, current_state: dict = None) -> dict:
        """Handle approval/denial cycle."""
        config = {"configurable": {"thread_id": session_id}}

        # Get current snapshot to verify interrupts
        snapshot = self.workflow.get_state(config)

        # Loop to handle interrupts
        while snapshot and snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
            # Extract approval request
            approval_request = snapshot.tasks[0].interrupts[0].value
            if "tool_calls" in approval_request:
                # Pass the entire approval request to include risk summary and enhanced data
                self.ui.print_approval_request(approval_request)

                # Get user decision
                decision = self.ui.get_approval_decision()

                # Prepare resume command based on user decision
                if decision.startswith("y") or decision == "yes":
                    resume_cmd = Command(resume=RESUME_APPROVED)
                    status_text = "Resuming execution..."
                else:
                    resume_cmd = Command(resume=RESUME_DENIED)
                    status_text = "Skipping execution..."

                # Resume workflow with streaming to show progress of post-approval steps
                self._run_workflow_stream(resume_cmd, config, initial_status=status_text)

                # Get new state after resuming to check for more interrupts or finish
                snapshot = self.workflow.get_state(config)

                if not snapshot.tasks or not snapshot.tasks[0].interrupts:
                    break

        # Return final state
        return self.workflow.get_state(config)
