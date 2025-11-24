from langgraph.types import StateSnapshot


def get_approval_request(snapshot: StateSnapshot) -> dict | None:
    """
    Parses a LangGraph snapshot to see if execution is paused for approval.
    Returns the tool_call dictionary if an interrupt exists, otherwise None.
    """
    if not snapshot.tasks:
        return None

    if not snapshot.tasks[0].interrupts:
        return None

    # Extract the first interrupt value
    interrupt_value = snapshot.tasks[0].interrupts[0].value

    # Return the specific tool call payload
    return interrupt_value.get("tool_call")
