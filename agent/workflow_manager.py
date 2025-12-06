"""Workflow manager for the Network AI Agent with Persistence."""

import logging
import sqlite3

# CHANGED: Import SqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph
from langgraph.types import StateSnapshot

from agent.constants import TOOL_CONFIG_COMMAND, TOOL_MULTI_COMMAND, TOOL_RESPOND
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
    def __init__(
        self,
        llm_provider: LLMProvider,
        device_inventory: DeviceInventory,
        task_executor: TaskExecutor,
        tools: list,
        max_history_tokens: int = 3500,
        # CHANGED: DB Path
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
        """Build and compile the workflow graph with Persistence."""
        if self._graph is not None:
            return self._graph

        context_manager_node = ContextManagerNode(self._llm_provider, self._max_history_tokens)
        understanding_node = UnderstandingNode(
            self._llm_provider, self._device_inventory, self._tools
        )
        validation_node = ValidationNode(self._llm_provider, self._device_inventory)
        approval_node = ApprovalNode(self._llm_provider)
        planner_node = PlannerNode(self._llm_provider)
        execute_node = ExecuteNode(self._llm_provider, self._tools)
        format_node = FormatNode(self._llm_provider, create_format_tool())

        workflow = StateGraph(State)

        workflow.add_node(NODE_CONTEXT_MANAGER, context_manager_node.execute)
        workflow.add_node(NODE_UNDERSTANDING, understanding_node.execute)
        workflow.add_node(NODE_VALIDATION, validation_node.execute)
        workflow.add_node(NODE_APPROVAL, approval_node.execute)
        workflow.add_node(NODE_PLANNER, planner_node.execute)
        workflow.add_node(NODE_EXECUTE, execute_node.execute)
        workflow.add_node(NODE_FORMAT, format_node.execute)

        workflow.set_entry_point(NODE_CONTEXT_MANAGER)

        workflow.add_edge(NODE_CONTEXT_MANAGER, NODE_UNDERSTANDING)
        workflow.add_edge(NODE_UNDERSTANDING, NODE_VALIDATION)

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

        workflow.add_conditional_edges(
            NODE_APPROVAL,
            self._route_approval,
            {
                NODE_EXECUTE: NODE_EXECUTE,
                NODE_CONTEXT_MANAGER: NODE_CONTEXT_MANAGER,
            },
        )

        workflow.add_edge(NODE_EXECUTE, NODE_FORMAT)
        workflow.add_edge(NODE_PLANNER, NODE_FORMAT)
        # Loop back to Context Manager to allow multi-step autonomy
        workflow.add_edge(NODE_FORMAT, NODE_CONTEXT_MANAGER)

        # CHANGED: Initialize SQLite Checkpointer
        logger.info(f"Initializing persistence at {self._db_path}")
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        checkpointer = SqliteSaver(self._conn)

        self._graph = workflow.compile(checkpointer=checkpointer)

        return self._graph

    def _route_after_validation(self, state: State) -> str:
        last_message = state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return END
        tool_name = last_message.tool_calls[0]["name"]

        if tool_name == TOOL_CONFIG_COMMAND:
            return NODE_APPROVAL
        elif tool_name == TOOL_MULTI_COMMAND:
            return NODE_PLANNER
        elif tool_name == TOOL_RESPOND:
            return END
        else:
            return NODE_EXECUTE

    def _route_approval(self, state: State) -> str:
        from langchain_core.messages import ToolMessage

        last_message = state["messages"][-1]
        if isinstance(last_message, ToolMessage):
            return NODE_CONTEXT_MANAGER
        return NODE_EXECUTE

    def create_session_config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    def get_approval_request(self, snapshot: StateSnapshot) -> dict | None:
        if not snapshot.tasks or not snapshot.tasks[0].interrupts:
            return None
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        if "tool_calls" in interrupt_value:
            return {"tool_calls": interrupt_value["tool_calls"]}
        elif "tool_call" in interrupt_value:
            return {"tool_calls": [interrupt_value["tool_call"]]}
        return None

    # CHANGED: Added close method
    def close(self):
        """Clean up DB connection."""
        if self._conn:
            try:
                self._conn.close()
                logger.info("Database connection closed.")
            except Exception as e:
                logger.error(f"Error closing database: {e}")
            finally:
                self._conn = None
