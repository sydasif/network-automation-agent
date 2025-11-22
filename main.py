"""Main entry point for the Network AI Agent.

This module provides the interactive CLI interface for the network automation agent,
allowing users to communicate with network devices using natural language commands.
"""

import logging
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.messages.utils import trim_messages
from langmem.short_term import summarize_messages

from graph.router import create_graph
from llm.client import create_llm


def summarize_conversation_history(messages, llm, max_tokens=2000):
    """Use langmem to summarize conversation history when it gets too long."""
    if len(messages) > 20:  # Summarize when we have more than 20 messages to preserve context
        try:
            # Use langmem's summarize_messages to create a summary of older messages
            result = summarize_messages(
                messages=messages,
                model=llm,
                max_tokens=max_tokens,
                max_summary_tokens=512,  # Reserve some tokens for summary
            )
            return result.messages
        except Exception as e:
            logging.warning(f"Failed to summarize messages: {e}")
            # Fall back to trimming if summarization fails
            return trim_messages(
                messages,
                max_tokens=15,  # Keep last 15 messages when summarization fails
                strategy="last",
                token_counter=len,
                start_on="human",
                end_on=("human", "ai"),
            )
    return messages


def chat_loop(app) -> None:
    """Handles the interactive chat session with the user."""
    # Generate a unique session ID for this conversation
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": f"session-{session_id}"}}

    # Get the LLM to use for summarization
    llm = create_llm()

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
            except Exception:
                # If no state exists yet, start with empty messages
                current_messages = []

            # Add the new user message
            new_messages = current_messages + [HumanMessage(content=user_input)]

            # First, try to summarize if conversation is getting too long
            if len(new_messages) > 20:  # If we have more than 20 messages, consider summarizing
                processed_messages = summarize_conversation_history(new_messages, llm)
            else:
                # Use LangChain's trim_messages to limit conversation history
                processed_messages = trim_messages(
                    new_messages,
                    max_tokens=15,  # Keep last 15 messages when using trimming (more conservative)
                    strategy="last",  # Keep the most recent messages
                    token_counter=len,  # Use len to count number of messages rather than tokens
                    start_on="human",  # Start counting from human messages
                    end_on=("human", "ai"),  # End counting on human or AI messages
                )

            # Invoke the app with the processed message history
            result = app.invoke({"messages": processed_messages, "results": {}}, config)

            # Get the final response message
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
