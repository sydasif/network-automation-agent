#!/usr/bin/env python3
"""Test script to verify that the chat functionality works for general conversation."""

import uuid
from langchain_core.messages import HumanMessage
from agent.workflow import create_graph

def test_general_chat():
    """Test that the agent can handle general conversation."""
    print("Testing general chat functionality...")
    
    # Create the workflow
    app = create_graph()
    
    # Create a session config
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": f"session-{session_id}"}}
    
    # Test cases for general conversation
    test_cases = [
        "Hi",
        "Hello",
        "Just chat with me",
        "How are you?",
        "What's your name?"
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: '{test_case}' ---")
        try:
            # Send the message to the agent
            result = app.invoke({"messages": [HumanMessage(content=test_case)]}, config)
            
            # Print the response
            if "messages" in result and result["messages"]:
                response = result["messages"][-1].content
                print(f"Response: {response}")
            else:
                print("No response received")
                
        except Exception as e:
            print(f"Error processing test case '{test_case}': {e}")
    
    print("\n--- Testing network command (as a control) ---")
    try:
        result = app.invoke({"messages": [HumanMessage(content="Show IP interfaces on R1")]}, config)
        if "messages" in result and result["messages"]:
            response = result["messages"][-1].content
            print(f"Network command response: {response}")
        else:
            print("No response for network command")
    except Exception as e:
        print(f"Error with network command: {e}")

if __name__ == "__main__":
    test_general_chat()