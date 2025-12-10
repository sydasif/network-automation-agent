"""Unit tests for understanding_node function."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from agent.nodes import understanding_node as understanding_func
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider


@pytest.fixture
def llm_provider():
    mock_config = Mock()
    mock_config.max_history_tokens = 1500
    mock_provider = Mock(spec=LLMProvider)
    mock_provider._config = mock_config
    return mock_provider


@pytest.fixture
def device_inventory():
    return Mock(spec=DeviceInventory)


def test_understanding_node_function_with_dependencies(llm_provider, device_inventory):
    """Test understanding_node function with dependencies."""
    mock_tool = Mock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    tools = [mock_tool]

    messages = [HumanMessage(content="Show me the status of router1")]
    state = {"messages": messages}

    # Mock the LLM and its structured output
    mock_execution_plan = Mock()
    mock_execution_plan.direct_response = "Router1 is running normally"
    mock_execution_plan.steps = []
    mock_structured_llm = Mock()
    mock_structured_llm.invoke.return_value = mock_execution_plan
    mock_llm = Mock()
    mock_llm.with_structured_output.return_value = mock_structured_llm

    # Mock LLM provider's method
    llm_provider.get_llm = Mock(return_value=mock_llm)

    result = understanding_func(
        state=state, llm_provider=llm_provider, device_inventory=device_inventory, tools=tools
    )

    assert "messages" in result
    # The result should contain a message from the LLM with tools
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 1
