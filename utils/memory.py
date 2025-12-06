"""Memory optimization middleware for the Agent."""

import logging
from typing import List

from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.messages.utils import count_tokens_approximately

logger = logging.getLogger(__name__)

def sanitize_messages(
    messages: List[BaseMessage],
    max_tokens: int = 1500,
    max_tool_output_length: int = 800
) -> List[BaseMessage]:
    """
    Sanitize messages before sending to LLM to prevent 413/Rate Limit errors.
    
    Acts as middleware to:
    1. Compress massive tool outputs (like 'show running-config') in history.
    2. Strictly trim conversation to token limits using LangChain's trimmer.
    
    Args:
        messages: The full message history.
        max_tokens: The strict token limit for the context window.
        max_tool_output_length: Max characters allowed for OLD tool outputs.
    """
    if not messages:
        return []

    # --- Step 1: Compress Old Tool Outputs ---
    # We keep the last 2 turns (User+AI+Tool+AI) intact. 
    # Anything older gets its Tool Outputs heavily truncated.
    
    # Heuristic: Keep last 6 messages untouched to allow "follow-up" logic to work
    keep_intact_count = 6 
    
    optimized_messages = []
    
    # Process history (everything before the last few messages)
    if len(messages) > keep_intact_count:
        history_msgs = messages[:-keep_intact_count]
        recent_msgs = messages[-keep_intact_count:]
        
        for msg in history_msgs:
            if isinstance(msg, ToolMessage) and len(msg.content) > max_tool_output_length:
                # Create a lightweight clone of the message
                # We MUST preserve tool_call_id so the conversation structure remains valid
                compressed_msg = ToolMessage(
                    tool_call_id=msg.tool_call_id,
                    content=(
                        f"{msg.content[:max_tool_output_length]}...\n"
                        f"[Output truncated by Memory Middleware. Original len: {len(msg.content)} chars]"
                    ),
                    name=msg.name,
                    status=msg.status,
                    artifact=msg.artifact
                )
                optimized_messages.append(compressed_msg)
            else:
                optimized_messages.append(msg)
        
        # Add recent messages back fully intact
        optimized_messages.extend(recent_msgs)
    else:
        optimized_messages = list(messages)

    # --- Step 2: Strict Token Trimming ---
    # This uses LangChain's official logic to ensure we fit in the context window
    try:
        final_messages = trim_messages(
            optimized_messages,
            max_tokens=max_tokens,
            strategy="last",
            token_counter=count_tokens_approximately,
            include_system=False, # System prompts are added by the Node templates later
            allow_partial=False,
            start_on="human"
        )
        
        # Log if we cut things out
        if len(final_messages) < len(optimized_messages):
            diff = len(optimized_messages) - len(final_messages)
            logger.info(f"Memory Middleware: Trimmed {diff} messages to fit {max_tokens} token limit.")
            
        return final_messages
        
    except Exception as e:
        logger.error(f"Memory trimming failed: {e}. Falling back to raw truncation.")
        return optimized_messages[-10:]