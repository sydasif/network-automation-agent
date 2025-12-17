"""Workflow manager for the Network AI Agent with Persistence and Monitoring."""

import logging
from functools import partial

# Changed: Use In-Memory checkpointer instead of SQLite
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.constants import TOOL_CONFIG_COMMAND
from agent.nodes import (
    approval_node as approval_func,
)
from agent.nodes import (
    execute_node as execute_func,
)
from agent.nodes import (
    response_node as response_func,
)
from agent.nodes import (
    understanding_node as understanding_func,
)
from agent.state import (
    NODE_APPROVAL,
    NODE_EXECUTE,
    NODE_RESPONSE,
    NODE_UNDERSTANDING,
    State,
)
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.task_executor import TaskExecutor

# Import monitoring components
from monitoring.callbacks import AlertingCallbackHandler
from monitoring.tracing import get_callback_handler

logger = logging.getLogger(__name__)


class NetworkAgentWorkflow:
    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        task_executor: TaskExecutor,
        tools: list,
        max_history_tokens: int = 3500,
        enable_monitoring: bool = True,
    ):
        self._llm_provider = llm_provider
        self._device_inventory = device_inventory
        self._task_executor = task_executor
        self._tools = tools
        self._max_history_tokens = max_history_tokens
        self._graph = None
        self._enable_monitoring = enable_monitoring
        self._monitoring_handler = None

        if self._enable_monitoring:
            self._monitoring_handler = AlertingCallbackHandler()

    def build(self):
        if self._graph is not None:
            return self._graph

        # Bind node functions with required parameters using functools.partial
        understanding_with_deps = partial(
            understanding_func,
            llm_provider=self._llm_provider,
            device_inventory=self._device_inventory,
            tools=self._tools,
        )
        execute_with_deps = partial(
            execute_func,
            tools=self._tools,
        )
        response_with_deps = partial(
            response_func,
            llm_provider=self._llm_provider,
        )

        workflow = StateGraph(State)

        # Add Nodes
        workflow.add_node(NODE_UNDERSTANDING, understanding_with_deps)
        workflow.add_node(NODE_APPROVAL, approval_func)
        workflow.add_node(NODE_EXECUTE, execute_with_deps)
        workflow.add_node(NODE_RESPONSE, response_with_deps)

        # Define Edges
        # START -> UNDERSTANDING
        workflow.set_entry_point(NODE_UNDERSTANDING)

        # UNDERSTANDING -> [APPROVAL, EXECUTE, END]
        workflow.add_conditional_edges(
            NODE_UNDERSTANDING,
            self._route_tool_calls,
            {
                NODE_APPROVAL: NODE_APPROVAL,
                NODE_EXECUTE: NODE_EXECUTE,
                END: END,
            },
        )

        # APPROVAL -> [EXECUTE, RESPONSE (if denied)]
        workflow.add_conditional_edges(
            NODE_APPROVAL,
            self._route_approval,
            {
                NODE_EXECUTE: NODE_EXECUTE,
                NODE_RESPONSE: NODE_RESPONSE,
            },
        )

        # EXECUTE -> RESPONSE (Linear Flow: Output is passed to Summarizer)
        workflow.add_edge(NODE_EXECUTE, NODE_RESPONSE)

        # RESPONSE -> END
        workflow.add_edge(NODE_RESPONSE, END)

        # Persistence: Use In-Memory Checkpointer
        logger.info("Initializing in-memory persistence")
        checkpointer = MemorySaver()

        # Compile with monitoring if enabled
        if self._enable_monitoring and self._monitoring_handler:
            # For now, we'll compile without the handler but can be extended to use it
            self._graph = workflow.compile(checkpointer=checkpointer)
        else:
            self._graph = workflow.compile(checkpointer=checkpointer)

        return self._graph

    def get_monitoring_handler(self):
        """Get the monitoring callback handler."""
        return self._monitoring_handler

    def get_session_stats(self, session_id: str = None):
        """Get monitoring statistics for a session."""
        if self._monitoring_handler:
            return self._monitoring_handler.get_session_stats()
        return None

    def reset_monitoring_session(self):
        """Reset monitoring for a new session."""
        if self._monitoring_handler:
            self._monitoring_handler.reset_session()

    def set_session_id(self, session_id: str):
        """Set session ID for monitoring."""
        if self._monitoring_handler:
            self._monitoring_handler.set_session_id(session_id)

    def _route_tool_calls(self, state: State) -> str:
        """Decide next node based on the tool selected by UnderstandingNode."""
        last_message = state["messages"][-1]

        # If no tool calls, it's a direct conversational response -> END
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return END

        # Intelligent Batch Routing:
        # Check ALL tool calls in the list.
        # If ANY tool call is a config command, route to APPROVAL.
        # Otherwise (all are show commands), route to EXECUTE.
        tool_calls = last_message.tool_calls
        if any(tc["name"] == TOOL_CONFIG_COMMAND for tc in tool_calls):
            return NODE_APPROVAL

        return NODE_EXECUTE

    def _route_approval(self, state: State) -> str:
        from langchain_core.messages import ToolMessage

        last_message = state["messages"][-1]
        # If user denied, we injected a ToolMessage with error.
        # In linear flow, we send this error to ResponseNode to be summarized/displayed.
        if isinstance(last_message, ToolMessage):
            return NODE_RESPONSE
        return NODE_EXECUTE

    def create_session_config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    def get_approval_request(self, snapshot: StateSnapshot) -> dict | None:
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            return None
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        return {"tool_calls": interrupt_value.get("tool_calls", [])}

    def close(self):
        # No DB connection to close anymore
        pass
