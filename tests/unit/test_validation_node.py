"""Unit tests for ValidationNode."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.nodes.validation_node import ValidationNode
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider


@pytest.fixture
def llm_provider():
    return Mock(spec=LLMProvider)


@pytest.fixture
def device_inventory():
    return Mock(spec=DeviceInventory)


@pytest.fixture
def validation_node(llm_provider, device_inventory):
    return ValidationNode(llm_provider, device_inventory)


def test_validation_node_initialization(llm_provider, device_inventory):
    """Test ValidationNode initialization."""
    node = ValidationNode(llm_provider, device_inventory)

    assert node._device_inventory == device_inventory
    assert node._llm_provider == llm_provider


def test_validation_node_execute_no_messages(validation_node):
    """Test ValidationNode execute with no messages."""
    state = {"messages": []}
    result = validation_node.execute(state)

    assert result == state  # Should return original state when no messages


def test_validation_node_execute_no_tool_calls(validation_node):
    """Test ValidationNode execute with messages but no tool calls."""
    messages = [HumanMessage(content="Hello")]
    state = {"messages": messages}

    result = validation_node.execute(state)

    assert result == state  # Should return original state when no tool calls


def test_validation_node_execute_with_valid_tool_calls(validation_node):
    """Test ValidationNode execute with valid tool calls."""
    # Create a mock message with valid tool calls
    mock_message = Mock(spec=AIMessage)
    mock_message.tool_calls = [
        {"name": "show_command", "args": {"devices": ["router1"], "command": "show version"}}
    ]

    # Mock the validation to pass
    validation_node._device_inventory.validate_devices.return_value = (["router1"], [])

    state = {"messages": [HumanMessage(content="Test"), mock_message]}
    result = validation_node.execute(state)

    assert result == state  # Should return original state when validation passes


def test_validation_node_execute_with_invalid_device(validation_node):
    """Test ValidationNode execute with invalid device in tool call."""
    # Create a mock message with invalid device in tool calls
    mock_message = Mock(spec=AIMessage)
    mock_message.tool_calls = [
        {
            "name": "show_command",
            "args": {"devices": ["invalid_router"], "command": "show version"},
        }
    ]

    # Mock the validation to fail
    validation_node._device_inventory.validate_devices.return_value = ([], ["invalid_router"])
    validation_node._device_inventory.get_all_device_names.return_value = ["router1", "router2"]

    state = {"messages": [HumanMessage(content="Test"), mock_message]}
    result = validation_node.execute(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    # Should return an error message
    assert "❌ Validation Error:" in result["messages"][0].content
    assert "Unknown devices: invalid_router" in result["messages"][0].content
