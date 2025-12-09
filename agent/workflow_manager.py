"""Workflow manager for the Network AI Agent with Persistence."""

import logging

# Changed: Use In-Memory checkpointer instead of SQLite
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.constants import TOOL_CONFIG_COMMAND
from agent.nodes import (
    ApprovalNode,
    ExecuteNode,
    ResponseNode,
    UnderstandingNode,
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

logger = logging.getLogger(__name__)


class NetworkAgentWorkflow:
    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        task_executor: TaskExecutor,
        tools: list,
        max_history_tokens: int = 3500,
    ):
        self._llm_provider = llm_provider
        self._device_inventory = device_inventory
        self._task_executor = task_executor
        self._tools = tools
        self._max_history_tokens = max_history_tokens
        self._graph = None

    def build(self):
        if self._graph is not None:
            return self._graph

        # Initialize Nodes
        understand_node = UnderstandingNode(
            self._llm_provider, self._device_inventory, self._tools
        )
        approval_node = ApprovalNode(self._llm_provider)
        execute_node = ExecuteNode(self._llm_provider, self._tools)
        response_node = ResponseNode(self._llm_provider)

        workflow = StateGraph(State)

        # Add Nodes
        workflow.add_node(NODE_UNDERSTANDING, understand_node.execute)
        workflow.add_node(NODE_APPROVAL, approval_node.execute)
        workflow.add_node(NODE_EXECUTE, execute_node.execute)
        workflow.add_node(NODE_RESPONSE, response_node.execute)

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

        self._graph = workflow.compile(checkpointer=checkpointer)

        return self._graph

    def _route_tool_calls(self, state: State) -> str:
        """Decide next node based on the tool selected by UnderstandingNode."""
        last_message = state["messages"][-1]

        # If no tool calls, it's a direct conversational response -> END
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return END

        # Handle Tool Calls
        tool_name = last_message.tool_calls[0]["name"]

        if tool_name == TOOL_CONFIG_COMMAND:
            return NODE_APPROVAL
        else:
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
