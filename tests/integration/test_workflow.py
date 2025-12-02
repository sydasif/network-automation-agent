"""Integration tests for Network Agent Workflow."""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.workflow_manager import NetworkAgentWorkflow
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.nornir_manager import NornirManager
from core.task_executor import TaskExecutor
from tools import get_all_tools


@pytest.fixture
def mock_infrastructure():
    """Setup mock infrastructure components."""
    nornir_manager = MagicMock(spec=NornirManager)
    device_inventory = MagicMock(spec=DeviceInventory)
    task_executor = MagicMock(spec=TaskExecutor)
    llm_provider = MagicMock(spec=LLMProvider)

    # Setup device inventory
    device_inventory.get_device_info.return_value = "R1 (cisco_ios)"
    device_inventory.get_all_device_names.return_value = ["R1"]
    device_inventory.validate_devices.return_value = ({"R1"}, set())

    return {
        "nornir_manager": nornir_manager,
        "device_inventory": device_inventory,
        "task_executor": task_executor,
        "llm_provider": llm_provider,
    }


def test_workflow_show_command(mock_infrastructure):
    """Test end-to-end workflow for a show command."""
    task_executor = mock_infrastructure["task_executor"]
    llm_provider = mock_infrastructure["llm_provider"]

    # Setup tools
    tools = get_all_tools(task_executor)

    # Setup LLM responses
    mock_llm = MagicMock()
    llm_provider.get_llm.return_value = mock_llm
    llm_provider.get_llm_with_tools.return_value = mock_llm

    # Sequence of LLM responses:
    # 1. UnderstandNode: Calls show_command tool
    # 2. UnderstandNode (after tool): Formats final response

    tool_call_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "show_command",
                "args": {"devices": ["R1"], "command": "show version"},
                "id": "call_1",
            }
        ],
    )

    final_response_msg = AIMessage(
        content='{"summary": "Version info", "structured_data": {"version": "1.0"}, "errors": []}'
    )

    mock_llm.invoke.side_effect = [
        tool_call_msg,  # First call (Understand -> Tool)
        final_response_msg,  # Second call (Understand -> Output)
    ]

    # Setup TaskExecutor response
    task_executor.execute_task.return_value = {"R1": "Cisco IOS Version 1.0"}

    # Build workflow
    workflow = NetworkAgentWorkflow(
        llm_provider=llm_provider,
        device_inventory=mock_infrastructure["device_inventory"],
        task_executor=task_executor,
        tools=tools,
    )
    graph = workflow.build()

    # Run workflow
    result = graph.invoke(
        {"messages": [HumanMessage(content="show version on R1")]},
        {"configurable": {"thread_id": "test_session"}},
    )

    # Verify results
    assert len(result["messages"]) >= 3  # Human, AI(ToolCall), Tool, AI(Final)

    # Verify tool execution
    task_executor.execute_task.assert_called_once()
    call_args = task_executor.execute_task.call_args
    assert call_args.kwargs["target_devices"] == ["R1"]
    assert call_args.kwargs["command_string"] == "show version"

    # Verify final response structure
    last_msg = result["messages"][-1]
    assert "summary" in last_msg.content
    assert "Version info" in last_msg.content


def test_workflow_config_approval(mock_infrastructure):
    """Test workflow with configuration approval."""
    task_executor = mock_infrastructure["task_executor"]
    llm_provider = mock_infrastructure["llm_provider"]

    tools = get_all_tools(task_executor)

    mock_llm = MagicMock()
    llm_provider.get_llm.return_value = mock_llm
    llm_provider.get_llm_with_tools.return_value = mock_llm

    # LLM Responses
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "config_command",
                "args": {
                    "devices": ["R1"],
                    "configs": ["int lo0", "ip addr 1.1.1.1 255.255.255.255"],
                },
                "id": "call_1",
            }
        ],
    )

    final_response_msg = AIMessage(
        content='{"summary": "Config applied", "structured_data": {}, "errors": []}'
    )

    mock_llm.invoke.side_effect = [
        tool_call_msg,  # First call
        final_response_msg,  # Second call
    ]

    # Setup TaskExecutor response for config command
    task_executor.execute_task.return_value = {"R1": "Configuration applied"}

    # Build workflow
    workflow = NetworkAgentWorkflow(
        llm_provider=llm_provider,
        device_inventory=mock_infrastructure["device_inventory"],
        task_executor=task_executor,
        tools=tools,
    )
    graph = workflow.build()

    config = {"configurable": {"thread_id": "test_session"}}

    # 1. Initial run - should stop at approval
    # We need to handle the interrupt. graph.invoke will raise GraphInterrupt if not handled?
    # No, LangGraph interrupts are handled by returning state, but invoke() might wait?
    # Actually, invoke() runs until interrupt.

    # We expect it to stop before executing the tool.
    # However, since we are mocking the LLM, we need to be careful about state.

    # Let's use a try-except block or check the state after invoke
    # LangGraph's invoke raises GraphInterrupt when it hits an interrupt point
    from langgraph.errors import GraphInterrupt

    try:
        graph.invoke({"messages": [HumanMessage(content="configure loopback")]}, config)
    except GraphInterrupt:
        pass

    # Check state - should be waiting for approval
    snapshot = graph.get_state(config)
    assert snapshot.next
    # The next node should be the one after approval?
    # Actually, the interrupt happens inside ApprovalNode or before ExecuteNode?
    # In our implementation, ApprovalNode raises Interrupt.

    # Verify tool was NOT executed yet
    task_executor.execute_task.assert_not_called()

    # 2. Approve and resume
    from langgraph.types import Command

    from agent import RESUME_APPROVED

    result = graph.invoke(Command(resume=RESUME_APPROVED), config)

    # Verify tool execution
    task_executor.execute_task.assert_called_once()
    call_args = task_executor.execute_task.call_args
    assert call_args.kwargs["target_devices"] == ["R1"]

    # Verify final response
    last_msg = result["messages"][-1]
    assert "Config applied" in last_msg.content
