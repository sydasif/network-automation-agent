"""Workflow manager for the Network AI Agent with split router responsibilities.

This module provides the NetworkAgentWorkflow class that manages
the LangGraph workflow creation and execution using split router responsibilities.
"""

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.nodes import (
    ApprovalNode,
    ContextManagerNode,
    ExecuteNode,
    FormatNode,
    PlannerNode,
    UnderstandingNode,
    ValidationNode,
)
from agent.state import (
    NODE_APPROVAL,
    NODE_CONTEXT_MANAGER,
    NODE_EXECUTE,
    NODE_FORMAT,
    NODE_PLANNER,
    NODE_UNDERSTANDING,
    NODE_VALIDATION,
    State,
)
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.task_executor import TaskExecutor
from tools import create_format_tool

logger = logging.getLogger(__name__)


class NetworkAgentWorkflow:
    """Manages the LangGraph workflow for the network agent with split router responsibilities.

    This class encapsulates workflow creation, configuration, and provides utilities
    for workflow management. It implements a specific architectural pattern using
    a "Context Manager -> Understanding -> Validation" flow before routing to execution
    or planning, ensuring requests are fully understood and validated before action.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        task_executor: TaskExecutor,
        tools: list,
        max_history_tokens: int = 3500,
    ):
        """Initialize the workflow manager.

        Args:
            llm_provider: LLMProvider instance
            device_inventory: DeviceInventory instance
            task_executor: TaskExecutor instance
            tools: List of available tools
            max_history_tokens: Maximum tokens for conversation history
        """
        self._llm_provider = llm_provider
        self._device_inventory = device_inventory
        self._task_executor = task_executor
        self._tools = tools
        self._max_history_tokens = max_history_tokens
        self._graph = None

    def build(self):
        """Build and compile the workflow graph with split router responsibilities.

        Returns:
            Compiled LangGraph workflow ready to process requests
        """
        if self._graph is not None:
            return self._graph

        # Create node instances with split responsibilities
        # - ContextManager: Handles conversation history and context
        # - Understanding: Analyzes user intent and selects potential tools
        # - Validation: Verifies if the intent is actionable and safe
        context_manager_node = ContextManagerNode(
            self._llm_provider,
            self._max_history_tokens,
        )
        understanding_node = UnderstandingNode(
            self._llm_provider,
            self._device_inventory,
            self._tools,
        )
        validation_node = ValidationNode(
            self._llm_provider,
            self._device_inventory,
        )
        approval_node = ApprovalNode(self._llm_provider)
        planner_node = PlannerNode(self._llm_provider)
        execute_node = ExecuteNode(self._llm_provider, self._tools)
        format_node = FormatNode(self._llm_provider, create_format_tool())

        # Create the state graph
        workflow = StateGraph(State)

        # Add nodes to the workflow
        workflow.add_node(NODE_CONTEXT_MANAGER, context_manager_node.execute)
        workflow.add_node(NODE_UNDERSTANDING, understanding_node.execute)
        workflow.add_node(NODE_VALIDATION, validation_node.execute)
        workflow.add_node(NODE_APPROVAL, approval_node.execute)
        workflow.add_node(NODE_PLANNER, planner_node.execute)
        workflow.add_node(NODE_EXECUTE, execute_node.execute)
        workflow.add_node(NODE_FORMAT, format_node.execute)

        # Set the starting node
        workflow.set_entry_point(NODE_CONTEXT_MANAGER)

        # Define the new workflow: CONTEXT_MANAGER → UNDERSTANDING → VALIDATION → [routing]
        # This linear sequence ensures state is built up progressively
        workflow.add_edge(NODE_CONTEXT_MANAGER, NODE_UNDERSTANDING)
        workflow.add_edge(NODE_UNDERSTANDING, NODE_VALIDATION)

        # After validation, conditionally route to appropriate nodes
        workflow.add_conditional_edges(
            NODE_VALIDATION,
            self._route_after_validation,
            {
                NODE_EXECUTE: NODE_EXECUTE,
                NODE_APPROVAL: NODE_APPROVAL,
                NODE_PLANNER: NODE_PLANNER,
                END: END,
            },
        )

        # Add conditional routing from Approval node
        workflow.add_conditional_edges(
            NODE_APPROVAL,
            self._route_approval,
            {
                NODE_EXECUTE: NODE_EXECUTE,
                NODE_CONTEXT_MANAGER: NODE_CONTEXT_MANAGER,  # Go back to context manager if rejected
            },
        )

        # Execution and planning output go to Format node
        # This ensures all final outputs are consistently formatted before returning to user
        workflow.add_edge(NODE_EXECUTE, NODE_FORMAT)
        workflow.add_edge(NODE_PLANNER, NODE_FORMAT)
        workflow.add_edge(NODE_FORMAT, END)

        # Compile the workflow with memory saver
        self._graph = workflow.compile(checkpointer=MemorySaver())

        logger.info(
            "New workflow graph with split router responsibilities built and compiled successfully"
        )
        return self._graph

    def _route_after_validation(self, state: State) -> str:
        """Route based on tool called in the last message after validation.

        Args:
            state: Current workflow state

        Returns:
            Next node name or END
        """
        last_message = state["messages"][-1]

        # If validation failed or no tool calls, end the workflow
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return END

        tool_name = last_message.tool_calls[0]["name"]

        # Route based on tool name
        if tool_name == "config_command":
            return NODE_APPROVAL
        elif tool_name == "multi_command":
            return NODE_PLANNER
        elif tool_name == "respond":
            return END
        else:
            # For show_command and other tools, execute directly
            return NODE_EXECUTE

    def _route_approval(self, state: State) -> str:
        """Route after approval based on user decision.

        Args:
            state: Current workflow state

        Returns:
            Next node name
        """
        from langchain_core.messages import ToolMessage

        last_message = state["messages"][-1]

        # If ToolMessage present, user denied the action
        if isinstance(last_message, ToolMessage):
            return NODE_CONTEXT_MANAGER  # Go back to context manager to continue conversation

        # Otherwise, proceed to execute
        return NODE_EXECUTE

    def create_session_config(self, session_id: str) -> dict:
        """Create configuration for a workflow session.

        Args:
            session_id: Unique session identifier

        Returns:
            Configuration dict for workflow invocation
        """
        return {"configurable": {"thread_id": f"session-{session_id}"}}

    def get_approval_request(self, snapshot: StateSnapshot) -> dict | None:
        """Extract approval request from a state snapshot."""
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            return None

        interrupt_value = snapshot.tasks[0].interrupts[0].value

        # Backwards compatibility if needed, but we expect "tool_calls" list now
        if "tool_calls" in interrupt_value:
            return {"tool_calls": interrupt_value["tool_calls"]}
        elif "tool_call" in interrupt_value:
            return {"tool_calls": [interrupt_value["tool_call"]]}

        return None
