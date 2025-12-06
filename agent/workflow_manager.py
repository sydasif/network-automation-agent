"""Workflow manager for the Network AI Agent with Persistence."""

import logging
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.constants import TOOL_CONFIG_COMMAND, TOOL_MULTI_COMMAND, TOOL_FINAL_RESPONSE
from agent.nodes import (
    ApprovalNode,
    ExecuteNode,
    PlannerNode,
    UnderstandingNode,
)
from agent.state import (
    NODE_APPROVAL,
    NODE_EXECUTE,
    NODE_PLANNER,
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
        db_path: str = ".agent_memory.db",
    ):
        self._llm_provider = llm_provider
        self._device_inventory = device_inventory
        self._task_executor = task_executor
        self._tools = tools
        self._max_history_tokens = max_history_tokens
        self._db_path = db_path
        self._graph = None
        self._conn = None

    def build(self):
        if self._graph is not None:
            return self._graph

        # Initialize Nodes
        understand_node = UnderstandingNode(
            self._llm_provider, self._device_inventory, self._tools
        )
        approval_node = ApprovalNode(self._llm_provider)
        planner_node = PlannerNode(self._llm_provider)
        execute_node = ExecuteNode(self._llm_provider, self._tools)

        workflow = StateGraph(State)

        # Add Nodes
        workflow.add_node(NODE_UNDERSTANDING, understand_node.execute)
        workflow.add_node(NODE_APPROVAL, approval_node.execute)
        workflow.add_node(NODE_PLANNER, planner_node.execute)
        workflow.add_node(NODE_EXECUTE, execute_node.execute)

        # Define Edges
        # START -> UNDERSTANDING
        workflow.set_entry_point(NODE_UNDERSTANDING)

        # UNDERSTANDING -> [APPROVAL, PLANNER, EXECUTE, END]
        workflow.add_conditional_edges(
            NODE_UNDERSTANDING,
            self._route_tool_calls,
            {
                NODE_APPROVAL: NODE_APPROVAL,
                NODE_PLANNER: NODE_PLANNER,
                NODE_EXECUTE: NODE_EXECUTE,
                END: END,
            },
        )

        # APPROVAL -> [EXECUTE, UNDERSTANDING (if denied)]
        workflow.add_conditional_edges(
            NODE_APPROVAL,
            self._route_approval,
            {
                NODE_EXECUTE: NODE_EXECUTE,
                NODE_UNDERSTANDING: NODE_UNDERSTANDING,
            },
        )

        # EXECUTE/PLANNER -> UNDERSTANDING (ReAct Loop)
        workflow.add_edge(NODE_EXECUTE, NODE_UNDERSTANDING)
        workflow.add_edge(NODE_PLANNER, NODE_UNDERSTANDING)

        # Persistence
        logger.info(f"Initializing persistence at {self._db_path}")
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        checkpointer = SqliteSaver(self._conn)

        self._graph = workflow.compile(checkpointer=checkpointer)

        return self._graph

    def _route_tool_calls(self, state: State) -> str:
        """Decide next node based on the tool selected by UnderstandingNode."""
        last_message = state["messages"][-1]

        # 1. SAFETY NET: If no tool calls and no content, force a retry
        if not last_message.tool_calls and not last_message.content.strip():
            # In a real scenario, we might want to inject a system error,
            # but for now, we assume the UI handles empty responses or we end.
            return END

        # 2. If no tool calls but has text, it's a direct response -> END
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return END

        tool_name = last_message.tool_calls[0]["name"]

        if tool_name == TOOL_CONFIG_COMMAND:
            return NODE_APPROVAL
        elif tool_name == TOOL_MULTI_COMMAND:
            return NODE_PLANNER
        elif tool_name == TOOL_FINAL_RESPONSE:
            return END
        else:
            return NODE_EXECUTE

    def _route_approval(self, state: State) -> str:
        from langchain_core.messages import ToolMessage

        last_message = state["messages"][-1]
        # If user denied, we injected a ToolMessage with error, loop back to LLM to handle it
        if isinstance(last_message, ToolMessage):
            return NODE_UNDERSTANDING
        return NODE_EXECUTE

    def create_session_config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    def get_approval_request(self, snapshot: StateSnapshot) -> dict | None:
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            return None
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        return {"tool_calls": interrupt_value.get("tool_calls", [])}

    def close(self):
        if self._conn:
            self._conn.close()
