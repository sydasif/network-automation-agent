"""Unit tests for RouterNode."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.nodes.router_node import RouterNode
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock(spec=LLMProvider)
    # Mock LLM
    mock_llm = MagicMock()
    provider.get_llm.return_value = mock_llm
    provider.get_llm_with_tools.return_value = mock_llm
    return provider


@pytest.fixture
def mock_device_inventory():
    inventory = MagicMock(spec=DeviceInventory)
    inventory.get_device_info.return_value = "Device Info"
    return inventory


@pytest.fixture
def router_node(mock_llm_provider, mock_device_inventory):
    return RouterNode(
        llm_provider=mock_llm_provider,
        device_inventory=mock_device_inventory,
        tools=[],
        max_history_tokens=1000,
    )


def test_process_user_input(router_node, mock_llm_provider):
    """Test processing user input."""
    # Setup mock response
    mock_response = AIMessage(content="Response")
    mock_llm_provider.get_llm_with_tools.return_value.invoke.return_value = mock_response

    state = {"messages": [HumanMessage(content="Hello")]}
    result = router_node.execute(state)

    assert "messages" in result
    assert result["messages"][0] == mock_response

    # Verify LLM was called with tools
    mock_llm_provider.get_llm_with_tools.assert_called_once()


def test_trim_messages(router_node):
    """Test message trimming."""
    # Create many messages
    messages = [HumanMessage(content=f"Msg {i}") for i in range(20)]

    # Mock count_tokens_approximately to return high count
    with patch("agent.nodes.router_node.count_tokens_approximately") as mock_count:
        mock_count.side_effect = lambda msgs: len(msgs) * 100

        # Mock trim_messages to actually trim
        with patch("agent.nodes.router_node.trim_messages") as mock_trim:
            mock_trim.return_value = messages[-5:]

            trimmed = router_node._trim_messages(messages)

            # Should be 5 trimmed messages + 1 summary message
            assert len(trimmed) == 6
            mock_trim.assert_called_once()


def test_handle_llm_error(router_node):
    """Test error handling."""
    error = ValueError("Test Error")
    result = router_node._handle_llm_error(error)

    assert "messages" in result
    assert "An internal error occurred" in result["messages"][0].content
