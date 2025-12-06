"""Unit tests for UnderstandingNode."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from agent.nodes.understanding_node import UnderstandingNode
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider


@pytest.fixture
def llm_provider():
    return Mock(spec=LLMProvider)


@pytest.fixture
def device_inventory():
    return Mock(spec=DeviceInventory)


@pytest.fixture
def understanding_node(llm_provider, device_inventory):
    mock_tool = Mock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    tools = [mock_tool]
    return UnderstandingNode(llm_provider, device_inventory, tools)


def test_understanding_node_initialization(llm_provider, device_inventory):
    """Test UnderstandingNode initialization."""
    mock_tool = Mock()
    mock_tool.name = "test_tool"
    tools = [mock_tool]
    node = UnderstandingNode(llm_provider, device_inventory, tools)

    assert node._device_inventory == device_inventory
    assert node._tools == tools
    assert node._llm_provider == llm_provider


def test_understanding_node_execute(understanding_node):
    """Test UnderstandingNode execute method."""
    messages = [HumanMessage(content="Show me the status of router1")]
    state = {"messages": messages}

    # Mock the LLM and its response
    mock_response = Mock()
    mock_response.tool_calls = []
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    # Patch _get_llm_with_tools to return our mock LLM
    understanding_node._get_llm_with_tools = Mock(return_value=mock_llm)

    result = understanding_node.execute(state)

    assert "messages" in result
    # The result should contain a message from the LLM with tools
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 1
