"""Main entry point for the Network AI Agent.

This module provides the interactive CLI interface for the network automation agent,
allowing users to communicate with network devices using natural language commands.
"""

import logging
import uuid

from langchain_core.messages import HumanMessage

from graph.router import create_graph


def chat_loop(app) -> None:
    """Handles the interactive chat session with the user."""
    session_id = str(uuid.uuid4())
    # The thread_id is what LangGraph uses to retrieve previous history from memory
    config = {"configurable": {"thread_id": f"session-{session_id}"}}

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            if not user_input:
                continue

            # DRY: We just send the NEW message.
            # LangGraph handles fetching history and appending this new one.
            result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)

            # Get the final response
            final_message = result["messages"][-1]
            print(f"\n🤖 Agent: {final_message.content}\n")

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
    logging.basicConfig(level=logging.ERROR)  # Reduce noise
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
