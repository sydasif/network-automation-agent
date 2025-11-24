"""Main entry point for the Network AI Agent."""

import logging
import uuid

from langchain_core.messages import HumanMessage
from langgraph.types import Command  # <--- Used to resume execution

from graph.router import create_graph


def chat_loop(app) -> None:
    """Runs the main chat interaction loop for the Network AI Agent."""
    session_id = str(uuid.uuid4())
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

            result = app.invoke({"messages": [HumanMessage(content=user_input)]}, config)

            snapshot = app.get_state(config)

            while snapshot.tasks and snapshot.tasks[0].interrupts:
                interrupt_value = snapshot.tasks[0].interrupts[0].value
                tool_call = interrupt_value["tool_call"]

                print("\n⚠️  APPROVAL REQUIRED ⚠️")
                print(f"Action:  {tool_call['name']}")
                print(f"Args:    {tool_call['args']}")

                choice = input("Authorize? (yes/no): ").strip().lower()
                resume_value = "approved" if choice in ["yes", "y"] else "denied"

                result = app.invoke(Command(resume=resume_value), config)

                snapshot = app.get_state(config)

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
