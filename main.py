"""Main entry point for the Network AI Agent.

This module provides the interactive CLI interface for the network automation agent,
allowing users to communicate with network devices using natural language commands.
"""

import logging

from langchain_core.messages import AIMessage, HumanMessage

from graph.router import create_graph


def chat_loop(app) -> None:
    """Handles the interactive chat session with the user."""
    config = {"configurable": {"thread_id": "network-agent-conversation"}}

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Get the current state with conversation history
            try:
                # Get current state including message history
                current_state = app.get_state(config)
                current_messages = current_state.values.get("messages", [])
            except:
                # If no state exists yet, start with empty messages
                current_messages = []

            # Add the new user message
            new_messages = current_messages + [HumanMessage(content=user_input)]

            # Invoke the app with the complete message history
            result = app.invoke({"messages": new_messages, "results": {}}, config)

            # Update the state with the complete conversation history
            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                response_text = final_message.content
            else:
                response_text = str(final_message)

            print(f"\n🤖 Agent: {response_text}\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logging.error(f"Error processing request: {e}")


def main() -> None:
    """Initialize and run the Network AI Agent in interactive mode.

    The function creates a graph-based workflow for processing user input,
    executing network commands, and returning formatted responses. It runs
    in a continuous loop until the user types 'quit', 'exit', or 'q'.

    The agent maintains conversation history and interacts with network
    devices through the configured LangGraph workflow.
    """
    logging.basicConfig(level=logging.INFO)

    try:
        app = create_graph()
    except Exception as e:
        logging.error(f"Failed to initialize the agent: {e}")
        return

    print("🤖 Network AI Agent Ready!")
    print("Type 'quit' to exit.\n")

    chat_loop(app)


if __name__ == "__main__":
    main()
