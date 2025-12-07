"""Response node for formatting final output."""

import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from agent.nodes.base_node import AgentNode
from agent.prompts import NetworkAgentPrompts

class ResponseNode(AgentNode):
    """Formats the final response by combining LLM summary with raw data."""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        messages = state.get("messages", [])

        # 1. Identify User Query
        user_query = "Unknown request"
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                user_query = msg.content
                break

        # 2. Extract Data (Fix for Multi-Tool Batches)
        collected_data = [] # List to hold all found tool outputs
        last_tool_output_str = "No data found."

        # Iterate backwards
        for msg in reversed(messages):
            # Stop if we hit a HumanMessage or an AI message that ISN'T the final_response call
            # This ensures we only grab the tool outputs that just happened.
            if isinstance(msg, HumanMessage):
                break

            if isinstance(msg, ToolMessage):
                # Ignore the routing signal tool
                if msg.name == "final_response":
                    continue

                # Ignore error/denied messages
                if msg.content.startswith("❌"):
                    continue

                # Process valid tool output
                try:
                    data = json.loads(msg.content)
                    collected_data.append(data)
                    # Keep the text version for the LLM prompt
                    last_tool_output_str += f"\nOutput from {msg.name}: {msg.content}"
                except:
                    collected_data.append({"raw_text": msg.content})
                    last_tool_output_str += f"\nOutput from {msg.name}: {msg.content}"

        # 3. Merge Data for UI
        # If we have multiple outputs (e.g., s1 and s2), we want to show them all.
        merged_raw_data = None
        if collected_data:
            if len(collected_data) == 1:
                merged_raw_data = collected_data[0]
            else:
                # Merge logic: Create a wrapper to hold multiple results
                merged_raw_data = {"batch_results": collected_data}

                # OPTIONAL: If they all have "devices" key (standard Nornir format),
                # we can try to merge them into one cleaner dict.
                try:
                    combined_devices = {}
                    for item in collected_data:
                        if isinstance(item, dict) and "devices" in item:
                            combined_devices.update(item["devices"])

                    if combined_devices:
                        merged_raw_data = {"devices": combined_devices}
                except Exception:
                    # Fallback to simple list if merge fails
                    merged_raw_data = {"batch_results": collected_data}

        # 4. Generate Summary
        prompt = NetworkAgentPrompts.RESPONSE_PROMPT.invoke({
            "user_query": user_query,
            "data": last_tool_output_str[:25000] # Increased limit slightly
        })

        response_msg = self._get_llm().invoke(prompt)
        summary = response_msg.content

        # 5. Construct Payload
        final_payload = {
            "message": summary,
        }

        if merged_raw_data:
            final_payload["structured_data"] = merged_raw_data

        return {
            "messages": [AIMessage(content=json.dumps(final_payload))]
        }