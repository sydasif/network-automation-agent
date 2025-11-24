"""agent.py: The complete Network AI Agent logic."""

from typing import Annotated, Any, List, Literal, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage, ToolMessage, trim_messages
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import StateSnapshot, interrupt

from settings import GROQ_API_KEY, LLM_MAX_TOKENS, LLM_MODEL_NAME, LLM_TEMPERATURE
from tools.commands import config_command, show_command
from utils.devices import get_all_device_names

# --- CONSTANTS ---
NODE_UNDERSTAND = "understand"
NODE_APPROVAL = "approval"
NODE_EXECUTE = "execute"
NODE_RESPOND = "respond"

RESUME_APPROVED = "approved"
RESUME_DENIED = "denied"

# --- PROMPTS ---
UNDERSTAND_PROMPT = """
You are a network automation assistant.

You have access to two tools:
1. show_command: For retrieving information (Read-Only).
2. config_command: For applying changes (Read-Write).

Rules:
- Always check device TYPES before issuing commands.
- If the user asks to CHANGE configuration (create, delete, set, update config), use 'config_command'.
- If the user asks to SHOW information, use 'show_command'.

Available devices: {device_names}
"""

RESPOND_PROMPT = """
You are a technical documentation assistant.
Receive raw JSON/Python dictionary output from network devices.
Convert it into a clean, concise Markdown summary.
Use tables for lists. Do not include the raw JSON in the output.
"""


# --- LLM SETUP ---
def _create_llm():
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")
    return ChatGroq(temperature=LLM_TEMPERATURE, model_name=LLM_MODEL_NAME, api_key=GROQ_API_KEY)


def _manage_chat_history(messages: List[BaseMessage]) -> List[BaseMessage]:
    return trim_messages(
        messages,
        max_tokens=LLM_MAX_TOKENS,
        strategy="last",
        token_counter=len,
        start_on="human",
        end_on=("human", "ai"),
        include_system=False,
    )


llm = _create_llm()
tools = [show_command, config_command]
llm_with_tools = llm.bind_tools(tools)
execute_node = ToolNode(tools)


# --- NODES ---
def understand_node(state: dict[str, Any]) -> dict[str, Any]:
    messages = state.get("messages", [])
    trimmed_messages = _manage_chat_history(messages)
    device_names = get_all_device_names()

    system_msg = SystemMessage(
        content=UNDERSTAND_PROMPT.format(device_names=", ".join(device_names))
    )

    response = llm_with_tools.invoke([system_msg] + trimmed_messages)
    return {"messages": [response]}


def approval_node(state: dict[str, Any]) -> dict[str, Any] | None:
    last_msg = state["messages"][-1]
    if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
        return None

    tool_call = last_msg.tool_calls[0]
    decision = interrupt({"type": "approval_request", "tool_call": tool_call})

    if decision == RESUME_APPROVED:
        return None

    return {
        "messages": [
            ToolMessage(
                tool_call_id=tool_call["id"],
                content=f"❌ User denied permission to execute: {tool_call['name']}",
            )
        ]
    }


def respond_node(state: dict[str, Any]) -> dict[str, Any]:
    messages = state["messages"]
    synthesis_prompt = SystemMessage(content=RESPOND_PROMPT)
    response = llm.invoke(messages + [synthesis_prompt])
    return {"messages": [response]}


# --- ROUTING ---
class State(TypedDict):
    messages: Annotated[list, add_messages]


def route_tools(state: State) -> Literal[NODE_EXECUTE, NODE_APPROVAL, NODE_RESPOND]:
    last_message = state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return NODE_RESPOND

    tool_name = last_message.tool_calls[0]["name"]
    if tool_name == "config_command":
        return NODE_APPROVAL

    return NODE_EXECUTE


def route_approval(state: State) -> Literal[NODE_EXECUTE, NODE_RESPOND]:
    last_message = state["messages"][-1]
    if isinstance(last_message, ToolMessage):
        return NODE_RESPOND
    return NODE_EXECUTE


# --- GRAPH COMPILE ---
def create_graph():
    workflow = StateGraph(State)
    workflow.add_node(NODE_UNDERSTAND, understand_node)
    workflow.add_node(NODE_APPROVAL, approval_node)
    workflow.add_node(NODE_EXECUTE, execute_node)
    workflow.add_node(NODE_RESPOND, respond_node)

    workflow.set_entry_point(NODE_UNDERSTAND)

    workflow.add_conditional_edges(
        NODE_UNDERSTAND,
        route_tools,
        {NODE_EXECUTE: NODE_EXECUTE, NODE_APPROVAL: NODE_APPROVAL, NODE_RESPOND: NODE_RESPOND},
    )
    workflow.add_conditional_edges(
        NODE_APPROVAL, route_approval, {NODE_EXECUTE: NODE_EXECUTE, NODE_RESPOND: NODE_RESPOND}
    )

    workflow.add_edge(NODE_EXECUTE, NODE_RESPOND)
    workflow.add_edge(NODE_RESPOND, END)

    return workflow.compile(checkpointer=MemorySaver())


# --- HELPER (Formerly utils/graph.py) ---
def get_approval_request(snapshot: StateSnapshot) -> dict | None:
    if not snapshot.tasks or not snapshot.tasks[0].interrupts:
        return None
    return snapshot.tasks[0].interrupts[0].value.get("tool_call")
