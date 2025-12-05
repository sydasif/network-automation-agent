"""Unit tests for ContextManagerNode."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from agent.nodes.context_manager_node import ContextManagerNode
from core.llm_provider import LLMProvider


@pytest.fixture
def llm_provider():
    return Mock(spec=LLMProvider)


@pytest.fixture
def context_manager_node(llm_provider):
    return ContextManagerNode(llm_provider, max_history_tokens=1000)


def test_context_manager_initialization(llm_provider):
    """Test ContextManagerNode initialization."""
    node = ContextManagerNode(llm_provider, max_history_tokens=2000)

    assert node._max_history_tokens == 2000
    assert node._llm_provider == llm_provider


def test_context_manager_execute_empty_messages(context_manager_node):
    """Test ContextManagerNode execute with empty messages."""
    state = {"messages": []}
    result = context_manager_node.execute(state)

    assert "messages" in result
    assert result["messages"] == []


def test_context_manager_execute_with_messages(context_manager_node):
    """Test ContextManagerNode execute with messages."""
    messages = [
        HumanMessage(content="Hello"),
        HumanMessage(content="How are you?"),
        HumanMessage(content="I need help with my router."),
    ]
    state = {"messages": messages}

    result = context_manager_node.execute(state)

    assert "messages" in result
    # The result should contain the messages, possibly trimmed
    assert isinstance(result["messages"], list)
