from langchain_core.messages import HumanMessage

from agent.nodes import understand_node


def test_understand_node_basic(mock_llm, monkeypatch):
    """Test that understand_node processes a basic message."""
    # Mock the LLM to return a predictable response
    monkeypatch.setattr("agent.nodes.get_llm_with_tools", lambda: mock_llm)

    state = {"messages": [HumanMessage(content="Hello")]}
    result = understand_node(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    # The content will be whatever the mock returns
    assert result["messages"][0].content == "Mocked response"


def test_planner_node(mock_llm, monkeypatch):
    """Test that planner_node generates a plan."""
    from agent.nodes import Plan, planner_node

    # Mock the structured output response
    mock_plan = Plan(steps=["Step 1", "Step 2"])
    mock_llm.with_structured_output.return_value.invoke.return_value = mock_plan

    monkeypatch.setattr("agent.nodes.get_llm", lambda: mock_llm)

    state = {"messages": [HumanMessage(content="Upgrade everything")]}
    result = planner_node(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert "Step 1" in result["messages"][0].content
    assert "Step 2" in result["messages"][0].content


def test_respond_tool(mock_llm):
    """Test that the respond tool is available and works."""
    from tools.response import respond

    # Test the tool directly
    resp = respond.invoke(
        {"summary": "Test summary", "structured_data": {"test": "data"}, "errors": []}
    )
    assert resp == "Response delivered."
