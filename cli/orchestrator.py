"""Orchestrator for handling workflow execution and user interaction."""

import logging
import uuid
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agent import RESUME_APPROVED, RESUME_DENIED

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Handles workflow execution and user interaction."""

    def __init__(self, workflow, ui, config):
        self.workflow = workflow
        self.ui = ui
        self.config = config

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

        # Show thinking status
        with self.ui.thinking_status():
            self.workflow.invoke(
                {"messages": [HumanMessage(content=full_command)]},
                {"configurable": {"thread_id": session_id}},
            )

        # Handle approval loop if needed
        return self._handle_approval_loop(session_id)

    def _build_prompt(self, command: str, device: Optional[str] = None) -> str:
        """Build prompt with device context."""
        if device:
            return f"Execute on {device}: {command}"
        return command

    def _handle_approval_loop(self, session_id: str) -> dict:
        """Handle approval/denial cycle."""
        config = {"configurable": {"thread_id": session_id}}

        # Get current state to see if there's an interrupt
        try:
            snapshot = self.workflow.get_state(config)

            # Check if there's an interrupt (approval required)
            while snapshot and snapshot.next and snapshot.tasks and snapshot.tasks[0].interrupts:
                # Extract approval request
                approval_request = snapshot.tasks[0].interrupts[0].value
                if "tool_calls" in approval_request:
                    tool_calls = approval_request["tool_calls"]

                    # Show approval request to user
                    self.ui.print_approval_request(tool_calls)

                    # Get user decision
                    decision = self.ui.get_approval_decision()

                    # Prepare resume command based on user decision
                    if decision.startswith("y") or decision == "yes":
                        # User approved
                        resume_cmd = Command(resume=RESUME_APPROVED)
                    else:
                        # User denied
                        resume_cmd = Command(resume=RESUME_DENIED)

                    # Resume workflow with user decision
                    with self.ui.thinking_status("Processing decision..."):
                        # Update the state with the user's decision
                        snapshot = self.workflow.invoke(resume_cmd, config)

                        # Get new state after resuming
                        snapshot = self.workflow.get_state(config)

                        # If there are still interrupts, continue the loop
                        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
                            break

        except Exception as e:
            logger.error(f"Error in approval loop: {e}")
            # If there's an error in the approval loop, return the current state
            pass

        # Return final state after approval loop is complete
        return self.workflow.get_state(config)

    def _extract_approval_request(self, snapshot: dict) -> Optional[str]:
        """Extract approval request from workflow state (placeholder)."""
        # This is a simplified implementation - in a real scenario, you'd need to interact
        # with the workflow's state to determine if an approval is needed
        return None
