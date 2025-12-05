"""Workflow manager for the Network AI Agent.

This module provides the NetworkAgentWorkflow class that manages
the LangGraph workflow creation and execution.
"""

import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.nodes import (
    ApprovalNode,
    ExecuteNode,
    FormatNode,
    PlannerNode,
    RouterNode,
)
from agent.state import (
    NODE_APPROVAL,
    NODE_EXECUTE,
    NODE_FORMAT,
    NODE_PLANNER,
    NODE_ROUTER,
    State,
)
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.task_executor import TaskExecutor
from tools import create_format_tool

logger = logging.getLogger(__name__)


class NetworkAgentWorkflow:
    """Manages the LangGraph workflow for the network agent.

    This class encapsulates workflow creation, configuration,
    and provides utilities for workflow management.
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
        """Build and compile the workflow graph.

        Returns:
            Compiled LangGraph workflow ready to process requests
        """
        if self._graph is not None:
            return self._graph

        # Create node instances
        router_node = RouterNode(
            self._llm_provider,
            self._device_inventory,
            self._tools,
            self._max_history_tokens,
        )
        approval_node = ApprovalNode(self._llm_provider)
        planner_node = PlannerNode(self._llm_provider)
        execute_node = ExecuteNode(self._llm_provider, self._tools)
        format_node = FormatNode(self._llm_provider, create_format_tool())

        # Create the state graph
        workflow = StateGraph(State)

        # Add nodes to the workflow
        workflow.add_node(NODE_ROUTER, router_node.execute)
        workflow.add_node(NODE_APPROVAL, approval_node.execute)
        workflow.add_node(NODE_PLANNER, planner_node.execute)
        workflow.add_node(NODE_EXECUTE, execute_node.execute)
        workflow.add_node(NODE_FORMAT, format_node.execute)

        # Set the starting node
        workflow.set_entry_point(NODE_ROUTER)

        # Add conditional routing from Router node
        workflow.add_conditional_edges(
            NODE_ROUTER,
            self._route_tools,
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
                NODE_ROUTER: NODE_ROUTER,
            },
        )

        # Execution and planning output go to Format node
        workflow.add_edge(NODE_EXECUTE, NODE_FORMAT)
        workflow.add_edge(NODE_PLANNER, NODE_FORMAT)
        workflow.add_edge(NODE_FORMAT, END)

        # Compile the workflow with memory saver
        self._graph = workflow.compile(checkpointer=MemorySaver())

        logger.info("Workflow graph built and compiled successfully")
        return self._graph

    def _route_tools(self, state: State) -> str:
        """Route based on tool called in the last message.

        Args:
            state: Current workflow state

        Returns:
            Next node name or END
        """
        last_message = state["messages"][-1]

        # If no tool calls, end the workflow
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
            return NODE_ROUTER

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
        """Extract approval request from a state snapshot.

        Args:
            snapshot: Workflow state snapshot

        Returns:
            Tool call dict if there's an approval request, None otherwise
        """
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            return None

        return snapshot.tasks[0].interrupts[0].value.get("tool_call")
