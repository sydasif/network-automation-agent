"""Tests for the monitoring functionality of the Network Automation Agent."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from monitoring.tracing import LangSmithTracer, NetworkAgentCallbackHandler
from monitoring.callbacks import MonitoringCallbackHandler, AlertingCallbackHandler
from monitoring.dashboard import MonitoringDashboard, PerformanceMetric
from monitoring.alerting import AlertManager, Alert, AlertSeverity, AlertType


class TestLangSmithTracer:
    """Tests for LangSmith tracing functionality."""

    def test_tracer_initialization_with_api_key(self):
        """Test tracer initialization with API key."""
        with patch.dict('os.environ', {'LANGSMITH_API_KEY': 'test-key'}):
            with patch('monitoring.tracing.LangSmithClient') as mock_client:
                tracer = LangSmithTracer()
                assert tracer.enabled is True
                assert tracer.api_key == 'test-key'

    def test_tracer_initialization_without_api_key(self):
        """Test tracer initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            tracer = LangSmithTracer()
            assert tracer.enabled is False

    def test_callback_handler_initialization(self):
        """Test callback handler initialization."""
        handler = NetworkAgentCallbackHandler()
        assert handler.tool_executions == []
        assert handler.llm_calls == []


class TestMonitoringCallbackHandler:
    """Tests for monitoring callback handler."""

    def test_session_management(self):
        """Test session management functionality."""
        handler = MonitoringCallbackHandler()
        handler.set_session_id("test-session-123")
        
        assert handler.session_id == "test-session-123"
        assert handler.session_start_time is not None

    def test_tool_execution_tracking(self):
        """Test tool execution tracking."""
        handler = MonitoringCallbackHandler()
        handler.set_session_id("test-session")
        
        # Simulate tool start
        serialized = {"name": "test_tool"}
        handler.on_tool_start(serialized, "test input")
        
        assert len(handler.tool_executions) == 1
        assert handler.current_tool is not None
        assert handler.current_tool.name == "test_tool"
        
        # Simulate tool end
        handler.on_tool_end("test output")
        
        assert handler.current_tool is None
        assert handler.tool_executions[0].status.value == "completed"
        assert handler.tool_executions[0].output_data == "test output"

    def test_llm_call_tracking(self):
        """Test LLM call tracking."""
        handler = MonitoringCallbackHandler()
        handler.set_session_id("test-session")
        
        # Mock LLMResult
        mock_result = Mock()
        mock_result.generations = [[Mock(text="test response", message="test message")]]
        
        # Simulate LLM start
        serialized = {"name": "gpt-3.5-turbo"}
        handler.on_llm_start(serialized, ["test prompt"])
        
        assert len(handler.llm_calls) == 1
        assert handler.current_llm_call is not None
        assert handler.current_llm_call.model == "gpt-3.5-turbo"
        
        # Simulate LLM end
        handler.on_llm_end(mock_result)
        
        assert handler.current_llm_call is None
        assert handler.llm_calls[0].status.value == "completed"
        assert "test response" in handler.llm_calls[0].response

    def test_session_statistics(self):
        """Test session statistics generation."""
        handler = MonitoringCallbackHandler()
        handler.set_session_id("test-session")
        
        # Add some mock data
        handler.on_tool_start({"name": "test_tool"}, "input")
        handler.on_tool_end("output")
        
        handler.on_llm_start({"name": "gpt-3.5-turbo"}, ["prompt"])
        mock_result = Mock()
        mock_result.generations = [[Mock(text="response", message="message")]]
        handler.on_llm_end(mock_result)
        
        stats = handler.get_session_stats()
        
        assert stats["session_id"] == "test-session"
        assert stats["tool_executions"]["total"] == 1
        assert stats["llm_calls"]["total"] == 1
        assert stats["tool_executions"]["successful"] == 1
        assert stats["llm_calls"]["successful"] == 1


class TestAlertingCallbackHandler:
    """Tests for alerting callback handler."""

    def test_slow_tool_alert(self):
        """Test alerting for slow tool execution."""
        thresholds = {"max_tool_duration": 0.001}  # 1ms threshold
        handler = AlertingCallbackHandler(alert_thresholds=thresholds)
        handler.set_session_id("test-session")
        
        # Simulate a slow tool
        handler.on_tool_start({"name": "slow_tool"}, "input")
        # Sleep to make it exceed threshold
        import time
        time.sleep(0.002)  # 2ms
        handler.on_tool_end("output")
        
        assert len(handler.alerts) >= 1
        slow_alert = handler.alerts[-1]
        assert "Slow tool execution" in slow_alert["message"]
        assert slow_alert["type"] == "performance"

    def test_error_alert(self):
        """Test alerting for errors."""
        handler = AlertingCallbackHandler()
        handler.set_session_id("test-session")
        
        # Simulate tool error
        handler.on_tool_start({"name": "failing_tool"}, "input")
        handler.on_tool_error(Exception("Test error"))
        
        assert len(handler.alerts) >= 1
        error_alert = handler.alerts[-1]
        assert "Tool execution failed" in error_alert["message"]
        assert error_alert["type"] == "error"


class TestMonitoringDashboard:
    """Tests for monitoring dashboard."""

    def test_dashboard_initialization(self):
        """Test dashboard initialization."""
        dashboard = MonitoringDashboard()
        assert dashboard.metrics_history == []
        assert dashboard.alerts_history == []
        assert dashboard.current_metrics == {}

    def test_add_session_metrics(self):
        """Test adding session metrics."""
        dashboard = MonitoringDashboard()
        
        mock_stats = {
            "session_id": "test-session",
            "session_duration": 10.5,
            "tool_executions": {
                "total": 5,
                "successful": 4,
                "failed": 1,
                "avg_duration": 2.3
            },
            "llm_calls": {
                "total": 3,
                "successful": 3,
                "failed": 0,
                "avg_duration": 1.2
            }
        }
        
        dashboard.add_session_metrics(mock_stats)
        
        assert len(dashboard.metrics_history) == 1
        assert dashboard.current_metrics != {}

    def test_performance_metrics(self):
        """Test performance metrics calculation."""
        dashboard = MonitoringDashboard()
        
        # Add some mock data to make current_metrics not empty
        mock_stats = {
            "session_id": "test-session",
            "session_duration": 10.5,
            "tool_executions": {
                "total": 5,
                "successful": 4,
                "failed": 1,
                "avg_duration": 0.5  # Good performance
            },
            "llm_calls": {
                "total": 3,
                "successful": 3,
                "failed": 0,
                "avg_duration": 1.0  # Good performance
            }
        }
        
        dashboard.add_session_metrics(mock_stats)
        
        metrics = dashboard.get_performance_metrics()
        assert len(metrics) == 3  # avg_tool_duration, avg_llm_duration, success_rate
        
        # Check that metrics have appropriate status
        for metric in metrics:
            assert isinstance(metric, PerformanceMetric)
            assert metric.status in ["good", "warning", "critical"]

    def test_system_health(self):
        """Test system health calculation."""
        dashboard = MonitoringDashboard()
        health = dashboard.get_system_health()
        
        assert "status" in health
        assert "total_sessions" in health
        assert "active_alerts" in health
        assert "uptime" in health
        assert "performance_score" in health

    def test_dashboard_report_generation(self):
        """Test dashboard report generation."""
        dashboard = MonitoringDashboard()
        report = dashboard.generate_dashboard_report()
        
        assert isinstance(report, str)
        assert "NETWORK AUTOMATION AGENT" in report
        assert "MONITORING DASHBOARD" in report
        assert "=" in report  # Header separator


class TestAlertManager:
    """Tests for alert manager."""

    def test_alert_creation(self):
        """Test creating alerts."""
        manager = AlertManager()
        
        alert = manager.trigger_alert(
            AlertType.ERROR,
            AlertSeverity.HIGH,
            "Test error message",
            {"key": "value"},
            "session-123"
        )
        
        assert alert.id.startswith("alert_")
        assert alert.alert_type == AlertType.ERROR
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Test error message"
        assert alert.details == {"key": "value"}
        assert alert.session_id == "session-123"
        assert not alert.resolved

    def test_alert_resolution(self):
        """Test resolving alerts."""
        manager = AlertManager()
        
        alert = manager.trigger_alert(
            AlertType.ERROR,
            AlertSeverity.HIGH,
            "Test error message"
        )
        
        manager.resolve_alert(alert.id)
        
        assert alert.resolved
        assert alert.resolved_at is not None

    def test_alert_filtering(self):
        """Test filtering alerts by type and severity."""
        manager = AlertManager()
        
        # Create different types of alerts
        manager.trigger_alert(AlertType.ERROR, AlertSeverity.HIGH, "High error")
        manager.trigger_alert(AlertType.PERFORMANCE, AlertSeverity.MEDIUM, "Medium perf")
        manager.trigger_alert(AlertType.ERROR, AlertSeverity.LOW, "Low error")
        
        # Test filtering by severity
        high_severity = manager.get_alerts_by_severity(AlertSeverity.HIGH)
        assert len(high_severity) == 1
        assert high_severity[0].severity == AlertSeverity.HIGH
        
        # Test filtering by type
        error_alerts = manager.get_alerts_by_type(AlertType.ERROR)
        assert len(error_alerts) == 2
        for alert in error_alerts:
            assert alert.alert_type == AlertType.ERROR

    def test_alert_summary(self):
        """Test alert summary generation."""
        manager = AlertManager()
        
        # Create some alerts
        manager.trigger_alert(AlertType.ERROR, AlertSeverity.HIGH, "High error")
        manager.trigger_alert(AlertType.PERFORMANCE, AlertSeverity.MEDIUM, "Medium perf")
        
        summary = manager.get_alert_summary()
        
        assert "total_alerts" in summary
        assert "unresolved_alerts" in summary
        assert "severity_breakdown" in summary
        assert "type_breakdown" in summary
        assert summary["total_alerts"] == 2


if __name__ == "__main__":
    pytest.main([__file__])
