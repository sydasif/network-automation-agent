"""Context management for optimizing LLM token usage."""

from typing import List
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)

class ContextManager:
    """Manages the conversation context to fit within token limits."""

    @staticmethod
    def compress_history(
        messages: List[BaseMessage], 
        keep_last: int = 6, 
        max_tool_output: int = 100
    ) -> List[BaseMessage]:
        """Compress older messages while preserving the most recent context.
        
        Strategy:
        1. Always keep SystemMessages.
        2. Keep the last `keep_last` messages fully intact.
        3. For older messages:
           - Keep Human/AI messages (conversation flow).
           - Truncate ToolMessages (bulk data) to save space.
        """
        if not messages:
            return []

        # 1. Separate System Messages (Always keep)
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        other_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

        # 2. Split into "Old" and "Recent"
        if len(other_msgs) <= keep_last:
            return system_msgs + other_msgs
            
        recent_msgs = other_msgs[-keep_last:]
        old_msgs = other_msgs[:-keep_last]

        # 3. Compress Old Messages
        compressed_old = []
        for msg in old_msgs:
            if isinstance(msg, ToolMessage):
                # Compress massive tool outputs
                content_str = str(msg.content)
                if len(content_str) > max_tool_output:
                    new_content = (
                        f"{content_str[:max_tool_output]}...\n"
                        f"[Output truncated. Original length: {len(content_str)} chars]"
                    )
                    # Create a copy with truncated content
                    compressed_msg = ToolMessage(
                        content=new_content,
                        tool_call_id=msg.tool_call_id,
                        name=msg.name,
                        status=msg.status
                    )
                    compressed_old.append(compressed_msg)
                else:
                    compressed_old.append(msg)
            else:
                # Keep Human and AI messages intact so the "story" makes sense
                compressed_old.append(msg)

        # 4. Reassemble
        return system_msgs + compressed_old + recent_msgs