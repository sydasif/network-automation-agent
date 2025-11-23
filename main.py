"""Main entry point for the Network AI Agent."""

import logging
import uuid
from langchain_core.messages import HumanMessage
from langgraph.types import Command  # <--- Used to resume execution
from graph.router import create_graph


def chat_loop(app) -> None:
    """Runs the main chat interaction loop for the Network AI Agent.

    This function manages the conversation flow between the user and the agent
    in a continuous loop until the user exits. It handles user input, invokes
    the agent, processes any required human approvals, and displays responses.

    Args:
        app: The compiled LangGraph workflow instance to interact with.
    """
    session_id = str(uuid.uuid4())
    # Create a unique session configuration with thread ID for conversation history
    config = {"configurable": {"thread_id": f"session-{session_id}"}}

    print("🤖 Network AI Agent Ready! (Type 'quit' to exit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break
            if not user_input:
                continue

            # Initial invocation - send user input to the workflow
            result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)

            # --- NATIVE HITL HANDLING ---
            # If the graph paused at interrupt(), result is NOT the final state.
            # We check the snapshot to see if we are in an interrupted state.
            snapshot = app.get_state(config)

            # Process any pending interrupts (configuration changes requiring approval)
            while snapshot.tasks and snapshot.tasks[0].interrupts:
                # Get the payload passed to interrupt() inside the node
                interrupt_value = snapshot.tasks[0].interrupts[0].value
                tool_call = interrupt_value["tool_call"]

                print("\n⚠️  APPROVAL REQUIRED ⚠️")
                print(f"Action:  {tool_call['name']}")
                print(f"Args:    {tool_call['args']}")

                choice = input("Authorize? (yes/no): ").strip().lower()
                resume_value = "approved" if choice in ["yes", "y"] else "denied"

                # Resume execution with the user's decision
                # This value ("approved"/"denied") becomes the return value of interrupt() in the node
                result = app.invoke(Command(resume=resume_value), config)

                # Update snapshot to check if there are MORE interrupts or if we are done
                snapshot = app.get_state(config)

            # Display the final response to the user
            if "messages" in result and result["messages"]:
                print(f"\n🤖 Agent: {result['messages'][-1].content}\n")

        except Exception as e:
            logging.error(f"Error processing request: {e}")


def main() -> None:
    logging.basicConfig(level=logging.ERROR)
    try:
        app = create_graph()
        chat_loop(app)
    except Exception as e:
        logging.error(f"Failed to initialize: {e}")


if __name__ == "__main__":
    main()
