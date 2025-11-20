from langchain_core.messages import AIMessage

from graph.router import create_graph


def main():
    app = create_graph()

    print("🤖 Network AI Agent Ready!")
    print("Type 'quit' to exit.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            conversation_history.append(user_input)

            result = app.invoke({"messages": conversation_history, "results": {}})

            final_message = result["messages"][-1]
            if isinstance(final_message, AIMessage):
                response_text = final_message.content
            else:
                response_text = str(final_message)

            print(f"\n🤖 Agent: {response_text}\n")

            conversation_history = result["messages"]

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
