"""Custom monitoring callbacks for the Network Automation Agent."""

import logging
from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of execution for monitoring."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class ToolExecutionRecord:
    """Record of a tool execution for monitoring."""
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    error: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, output: str = "", error: Optional[str] = None):
        """Mark execution as complete."""
        self.end_time = datetime.now()
        if error:
            self.error = error
            self.status = ExecutionStatus.FAILED
        else:
            self.output_data = output
            self.status = ExecutionStatus.COMPLETED
        self.duration = (self.end_time - self.start_time).total_seconds()


@dataclass
class LLMCallRecord:
    """Record of an LLM call for monitoring."""
    model: str
    start_time: datetime
    end_time: Optional[datetime] = None
    prompts: Optional[list] = None
    response: Optional[str] = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    error: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, response: str = "", error: Optional[str] = None):
        """Mark LLM call as complete."""
        self.end_time = datetime.now()
        if error:
            self.error = error
            self.status = ExecutionStatus.FAILED
        else:
            self.response = response
            self.status = ExecutionStatus.COMPLETED
        self.duration = (self.end_time - self.start_time).total_seconds()


class MonitoringCallbackHandler(BaseCallbackHandler):
    """Advanced monitoring callback handler for the Network Automation Agent."""

    def __init__(self):
        """Initialize the monitoring callback handler."""
        super().__init__()
        self.session_id: Optional[str] = None
        self.session_start_time: Optional[datetime] = None
        self.tool_executions: list[ToolExecutionRecord] = []
        self.llm_calls: list[LLMCallRecord] = []
        self.current_tool: Optional[ToolExecutionRecord] = None
        self.current_llm_call: Optional[LLMCallRecord] = None

    def set_session_id(self, session_id: str):
        """Set the current session ID for tracking."""
        self.session_id = session_id
        self.session_start_time = datetime.now()

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain starts."""
        chain_name = serialized.get("name", "unknown")
        logger.info(f"[Session {self.session_id}] Chain started: {chain_name}")
        
        # Add metadata to track the chain
        if "run_id" in kwargs:
            metadata = {"run_id": kwargs["run_id"], "chain_name": chain_name}
        else:
            metadata = {"chain_name": chain_name}

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when a chain ends."""
        logger.info(f"[Session {self.session_id}] Chain ended")

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when a tool starts."""
        tool_name = serialized.get("name", "unknown")
        logger.info(f"[Session {self.session_id}] Tool started: {tool_name}")
        
        # Create a new tool execution record
        tool_record = ToolExecutionRecord(
            name=tool_name,
            start_time=datetime.now(),
            input_data=input_str if isinstance(input_str, dict) else {"input": str(input_str)},
            metadata=kwargs.get("metadata", {})
        )
        
        self.current_tool = tool_record
        self.tool_executions.append(tool_record)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when a tool ends."""
        if self.current_tool:
            self.current_tool.complete(output=output)
            logger.info(
                f"[Session {self.session_id}] Tool completed: {self.current_tool.name} "
                f"in {self.current_tool.duration:.2f}s"
            )
            self.current_tool = None

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when a tool errors."""
        if self.current_tool:
            self.current_tool.complete(error=str(error))
            logger.error(
                f"[Session {self.session_id}] Tool failed: {self.current_tool.name} - {error}"
            )
            self.current_tool = None

    def on_llm_start(self, serialized: Dict[str, Any], prompts: list, **kwargs: Any) -> None:
        """Called when LLM starts."""
        model_name = serialized.get("name", "unknown")
        logger.info(f"[Session {self.session_id}] LLM call started: {model_name}")
        
        # Create a new LLM call record
        llm_record = LLMCallRecord(
            model=model_name,
            start_time=datetime.now(),
            prompts=prompts,
            metadata=kwargs.get("metadata", {})
        )
        
        self.current_llm_call = llm_record
        self.llm_calls.append(llm_record)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends."""
        if self.current_llm_call:
            # Extract response text from LLMResult
            response_text = ""
            if response and response.generations:
                # Get the first generation text
                first_generation = response.generations[0][0] if response.generations[0] else None
                if first_generation:
                    response_text = first_generation.text or str(first_generation.message)
            
            self.current_llm_call.complete(response=response_text)
            logger.info(
                f"[Session {self.session_id}] LLM call completed: {self.current_llm_call.model} "
                f"in {self.current_llm_call.duration:.2f}s"
            )
            self.current_llm_call = None

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Called when LLM errors."""
        if self.current_llm_call:
            self.current_llm_call.complete(error=str(error))
            logger.error(
                f"[Session {self.session_id}] LLM call failed: {self.current_llm_call.model} - {error}"
            )
            self.current_llm_call = None

    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics."""
        session_duration = 0
        if self.session_start_time:
            session_duration = (
                (datetime.now() - self.session_start_time).total_seconds()
                if self.session_start_time
                else 0
            )

        # Tool execution stats
        total_tools = len(self.tool_executions)
        successful_tools = len([t for t in self.tool_executions if t.status == ExecutionStatus.COMPLETED])
        failed_tools = len([t for t in self.tool_executions if t.status == ExecutionStatus.FAILED])
        avg_tool_duration = (
            sum(t.duration for t in self.tool_executions if t.duration) / total_tools
            if total_tools > 0
            else 0
        )

        # LLM call stats
        total_llms = len(self.llm_calls)
        successful_llms = len([l for l in self.llm_calls if l.status == ExecutionStatus.COMPLETED])
        failed_llms = len([l for l in self.llm_calls if l.status == ExecutionStatus.FAILED])
        avg_llm_duration = (
            sum(l.duration for l in self.llm_calls if l.duration) / total_llms
            if total_llms > 0
            else 0
        )

        return {
            "session_id": self.session_id,
            "session_duration": session_duration,
            "tool_executions": {
                "total": total_tools,
                "successful": successful_tools,
                "failed": failed_tools,
                "avg_duration": avg_tool_duration,
                "executions": [
                    {
                        "name": t.name,
                        "duration": t.duration,
                        "status": t.status.value,
                        "error": t.error
                    }
                    for t in self.tool_executions
                ]
            },
            "llm_calls": {
                "total": total_llms,
                "successful": successful_llms,
                "failed": failed_llms,
                "avg_duration": avg_llm_duration,
                "calls": [
                    {
                        "model": l.model,
                        "duration": l.duration,
                        "status": l.status.value,
                        "error": l.error
                    }
                    for l in self.llm_calls
                ]
            }
        }

    def reset_session(self):
        """Reset the current session for a new execution."""
        self.session_id = None
        self.session_start_time = None
        self.tool_executions.clear()
        self.llm_calls.clear()
        self.current_tool = None
        self.current_llm_call = None


class AlertingCallbackHandler(MonitoringCallbackHandler):
    """Enhanced callback handler with alerting capabilities."""

    def __init__(self, alert_thresholds: Optional[Dict[str, Any]] = None):
        """Initialize with alert thresholds.

        Args:
            alert_thresholds: Dictionary with alert thresholds (e.g., max tool duration, failure rate)
        """
        super().__init__()
        self.alert_thresholds = alert_thresholds or {
            "max_tool_duration": 30.0,  # seconds
            "max_llm_duration": 60.0,   # seconds
            "max_failure_rate": 0.1,    # 10% failure rate
            "alert_on_error": True,
        }
        self.alerts = []

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Override to add alerting logic."""
        super().on_tool_end(output, **kwargs)
        
        if self.current_tool and self.current_tool.duration:
            # Check for slow tools
            if (self.current_tool.duration > 
                self.alert_thresholds.get("max_tool_duration", 30.0)):
                alert_msg = (
                    f"Slow tool execution: {self.current_tool.name} took "
                    f"{self.current_tool.duration:.2f}s (threshold: "
                    f"{self.alert_thresholds['max_tool_duration']}s)"
                )
                self._trigger_alert(alert_msg, "performance")
    
    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        """Override to add alerting logic."""
        super().on_tool_error(error, **kwargs)
        
        if self.alert_thresholds.get("alert_on_error", True):
            alert_msg = f"Tool execution failed: {str(error)}"
            self._trigger_alert(alert_msg, "error")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Override to add alerting logic."""
        super().on_llm_end(response, **kwargs)
        
        if self.current_llm_call and self.current_llm_call.duration:
            # Check for slow LLM calls
            if (self.current_llm_call.duration > 
                self.alert_thresholds.get("max_llm_duration", 60.0)):
                alert_msg = (
                    f"Slow LLM call: {self.current_llm_call.model} took "
                    f"{self.current_llm_call.duration:.2f}s (threshold: "
                    f"{self.alert_thresholds['max_llm_duration']}s)"
                )
                self._trigger_alert(alert_msg, "performance")

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        """Override to add alerting logic."""
        super().on_llm_error(error, **kwargs)
        
        if self.alert_thresholds.get("alert_on_error", True):
            alert_msg = f"LLM call failed: {str(error)}"
            self._trigger_alert(alert_msg, "error")

    def _trigger_alert(self, message: str, alert_type: str):
        """Trigger an alert."""
        alert = {
            "timestamp": datetime.now(),
            "type": alert_type,
            "message": message,
            "session_id": self.session_id
        }
        self.alerts.append(alert)
        logger.warning(f"ALERT [{alert_type.upper()}]: {message}")
        
        # Here you could add integration with external alerting systems
        # like Slack, email, etc.