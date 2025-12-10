"""Integration tests for Network Agent Workflow."""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage

from agent.workflow_manager import NetworkAgentWorkflow
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.nornir_manager import NornirManager
from core.task_executor import TaskExecutor
from tools import create_tools


@pytest.fixture
def mock_infrastructure():
    """Setup mock infrastructure components."""
    nornir_manager = MagicMock(spec=NornirManager)
    device_inventory = MagicMock(spec=DeviceInventory)
    task_executor = MagicMock(spec=TaskExecutor)

    # Create LLMProvider mock with required _config attribute
    llm_provider = MagicMock(spec=LLMProvider)
    mock_config = MagicMock()
    mock_config.max_history_tokens = 1500
    llm_provider._config = mock_config

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
    tools = create_tools(task_executor)

    # Setup LLM responses
    mock_llm = MagicMock()
    llm_provider.get_llm.return_value = mock_llm

    # Mock structured output for ExecutionPlan
    mock_execution_plan = MagicMock()
    mock_execution_plan.direct_response = None  # No direct response, will execute steps
    mock_execution_plan.steps = [
        MagicMock(action_type="read", device="R1", command="show version")
    ]
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = mock_execution_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # Setup structured LLM for response node
    mock_response_model = MagicMock()
    mock_response_model.model_dump.return_value = {"message": "R1 is running Version 1.0"}
    mock_response_structured_llm = MagicMock()
    mock_response_structured_llm.invoke.return_value = mock_response_model

    # The response node also uses with_structured_output but for AgentResponse
    def side_effect(schema):
        if schema.__name__ == "AgentResponse":
            return mock_response_structured_llm
        return mock_structured_llm

    mock_llm.with_structured_output.side_effect = side_effect

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

    # Verify final response content (now as natural language)
    last_msg = result["messages"][-1]
    assert "Version 1.0" in last_msg.content
    # Ensure we are NOT checking for 'structured_data' key


def test_workflow_config_approval(mock_infrastructure):
    """Test workflow with configuration approval."""
    task_executor = mock_infrastructure["task_executor"]
    llm_provider = mock_infrastructure["llm_provider"]

    tools = create_tools(task_executor)

    mock_llm = MagicMock()
    llm_provider.get_llm.return_value = mock_llm
    # llm_provider.get_llm_with_tools.return_value = mock_llm  # Not needed with new Planner

    # Mock structured output for ExecutionPlan
    mock_execution_plan = MagicMock()
    mock_execution_plan.direct_response = None  # No direct response, will execute steps
    mock_execution_plan.steps = [
        MagicMock(
            action_type="configure",
            device="R1",
            command="int lo0\nip addr 1.1.1.1 255.255.255.255",
        )
    ]
    mock_structured_llm = MagicMock()
    mock_structured_llm.invoke.return_value = mock_execution_plan
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # Setup structured LLM for response node
    mock_response_model = MagicMock()
    mock_response_model.model_dump.return_value = {
        "message": "Configuration applied successfully to R1"
    }
    mock_response_structured_llm = MagicMock()
    mock_response_structured_llm.invoke.return_value = mock_response_model

    # The response node also uses with_structured_output but for AgentResponse
    def side_effect(schema):
        if schema.__name__ == "AgentResponse":
            return mock_response_structured_llm
        return mock_structured_llm

    mock_llm.with_structured_output.side_effect = side_effect

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

    # Verify final response (now as natural language)
    last_msg = result["messages"][-1]
    assert "Configuration applied" in last_msg.content
    assert "R1" in last_msg.content
