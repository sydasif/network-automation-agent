"""LangSmith tracing integration for the Network Automation Agent."""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from langchain_core.callbacks import BaseCallbackHandler
from langsmith import Client as LangSmithClient
from langsmith.utils import LangSmithError

logger = logging.getLogger(__name__)


class LangSmithTracer:
    """Manages LangSmith tracing integration for the workflow."""

    def __init__(self, api_key: Optional[str] = None, project_name: str = "network-automation-agent"):
        """Initialize the LangSmith tracer.

        Args:
            api_key: LangSmith API key (defaults to LANGSMITH_API_KEY env var)
            project_name: LangSmith project name for tracking runs
        """
        self.api_key = api_key or os.getenv("LANGSMITH_API_KEY")
        self.project_name = project_name
        self.client = None
        self.enabled = False

        if self.api_key:
            try:
                self.client = LangSmithClient(api_key=self.api_key)
                # Verify connection
                self.client.list_projects(limit=1)
                self.enabled = True
                logger.info("LangSmith tracing enabled")
            except LangSmithError as e:
                logger.warning(f"LangSmith connection failed: {e}")
                self.enabled = False
        else:
            logger.info("LangSmith API key not provided, tracing disabled")

    def get_traced_workflow(self, workflow):
        """Wrap a workflow with LangSmith tracing if enabled.

        Args:
            workflow: The LangGraph workflow to wrap

        Returns:
            Traced workflow or original workflow if tracing disabled
        """
        if not self.enabled:
            return workflow

        # Import here to avoid circular imports
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.pregel import Pregel
        import inspect

        # We need to recompile the workflow with tracing enabled
        # For now, return the original workflow and rely on callbacks
        return workflow

    def trace_execution(self, func):
        """Decorator to trace function execution with LangSmith."""
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)

            run_name = kwargs.get('run_name', func.__name__)
            try:
                # Start a LangSmith run manually if needed
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Log error to LangSmith if possible
                logger.error(f"Error in traced function {func.__name__}: {e}")
                raise
        return wrapper


class NetworkAgentCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for tracking tool execution and LLM calls."""

    def __init__(self, tracer: Optional[LangSmithTracer] = None):
        """Initialize the callback handler.

        Args:
            tracer: Optional LangSmith tracer instance
        """
        super().__init__()
        self.tracer = tracer or LangSmithTracer()
        self.session_start_time = None
        self.current_run_id = None
        self.tool_executions = []
        self.llm_calls = []

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain starts."""
        if self.tracer.enabled:
            logger.info(f"Chain started: {serialized.get('name', 'unknown')}")
            self.session_start_time = datetime.now()

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain ends."""
        if self.tracer.enabled:
            duration = (datetime.now() - self.session_start_time).total_seconds() if self.session_start_time else 0
            logger.info(f"Chain ended. Duration: {duration:.2f}s")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when a tool starts."""
        if self.tracer.enabled:
            tool_name = serialized.get("name", "unknown")
            logger.info(f"Tool started: {tool_name}")

            execution_record = {
                "tool_name": tool_name,
                "start_time": datetime.now(),
                "input": input_str,
                "status": "running"
            }
            self.tool_executions.append(execution_record)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool ends."""
        if self.tracer.enabled:
            if self.tool_executions:
                last_execution = self.tool_executions[-1]
                last_execution["end_time"] = datetime.now()
                last_execution["duration"] = (
                    last_execution["end_time"] - last_execution["start_time"]
                ).total_seconds()
                last_execution["output"] = output[:500]  # Limit output size
                last_execution["status"] = "completed"

                logger.info(f"Tool completed: {last_execution['tool_name']} in {last_execution['duration']:.2f}s")

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when a tool errors."""
        if self.tracer.enabled:
            if self.tool_executions:
                last_execution = self.tool_executions[-1]
                last_execution["end_time"] = datetime.now()
                last_execution["duration"] = (
                    last_execution["end_time"] - last_execution["start_time"]
                ).total_seconds()
                last_execution["error"] = str(error)
                last_execution["status"] = "failed"

                logger.error(f"Tool failed: {last_execution['tool_name']} - {error}")

    def on_llm_start(self, serialized: Dict[str, Any], prompts: list, **kwargs: Any) -> None:
        """Called when LLM starts."""
        if self.tracer.enabled:
            model_name = serialized.get("name", "unknown")
            logger.info(f"LLM call started: {model_name}")

            call_record = {
                "model": model_name,
                "start_time": datetime.now(),
                "prompts": prompts,
                "status": "running"
            }
            self.llm_calls.append(call_record)

    def on_llm_end(self, response, **kwargs: Any) -> None:
        """Called when LLM ends."""
        if self.tracer.enabled:
            if self.llm_calls:
                last_call = self.llm_calls[-1]
                last_call["end_time"] = datetime.now()
                last_call["duration"] = (
                    last_call["end_time"] - last_call["start_time"]
                ).total_seconds()
                last_call["response"] = str(response)[:1000]  # Limit response size
                last_call["status"] = "completed"

                logger.info(f"LLM call completed: {last_call['model']} in {last_call['duration']:.2f}s")

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when LLM errors."""
        if self.tracer.enabled:
            if self.llm_calls:
                last_call = self.llm_calls[-1]
                last_call["end_time"] = datetime.now()
                last_call["duration"] = (
                    last_call["end_time"] - last_call["start_time"]
                ).total_seconds()
                last_call["error"] = str(error)
                last_call["status"] = "failed"

                logger.error(f"LLM call failed: {last_call['model']} - {error}")

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics for monitoring."""
        total_tools = len(self.tool_executions)
        successful_tools = len([t for t in self.tool_executions if t.get("status") == "completed"])
        failed_tools = len([t for t in self.tool_executions if t.get("status") == "failed"])

        total_llms = len(self.llm_calls)
        successful_llms = len([l for l in self.llm_calls if l.get("status") == "completed"])
        failed_llms = len([l for l in self.llm_calls if l.get("status") == "failed"])

        stats = {
            "session_start_time": self.session_start_time,
            "tool_executions": {
                "total": total_tools,
                "successful": successful_tools,
                "failed": failed_tools,
                "avg_duration": sum(t.get("duration", 0) for t in self.tool_executions) / total_tools if total_tools > 0 else 0
            },
            "llm_calls": {
                "total": total_llms,
                "successful": successful_llms,
                "failed": failed_llms,
                "avg_duration": sum(l.get("duration", 0) for l in self.llm_calls) / total_llms if total_llms > 0 else 0
            }
        }

        return stats


# Global tracer instance
_global_tracer = None


def get_tracer() -> LangSmithTracer:
    """Get the global LangSmith tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = LangSmithTracer()
    return _global_tracer


def get_callback_handler() -> NetworkAgentCallbackHandler:
    """Get a callback handler instance."""
    tracer = get_tracer()
    return NetworkAgentCallbackHandler(tracer)
