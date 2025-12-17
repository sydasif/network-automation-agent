"""Monitoring dashboard for the Network Automation Agent."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a performance metric for dashboard display."""
    name: str
    value: float
    unit: str
    description: str
    status: str  # 'good', 'warning', 'critical'


class MonitoringDashboard:
    """Provides monitoring dashboard functionality for the Network Automation Agent."""

    def __init__(self):
        """Initialize the monitoring dashboard."""
        self.metrics_history = []
        self.alerts_history = []
        self.current_metrics = {}

    def add_session_metrics(self, session_stats: Dict[str, Any]):
        """Add session metrics to the dashboard."""
        self.metrics_history.append({
            "timestamp": datetime.now(),
            "session_stats": session_stats,
            "session_id": session_stats.get("session_id", "unknown")
        })

        # Update current metrics
        self.current_metrics = self._calculate_current_metrics()

    def get_performance_metrics(self) -> List[PerformanceMetric]:
        """Calculate and return current performance metrics."""
        metrics = []

        if self.current_metrics:
            # Average tool execution time
            avg_tool_time = self.current_metrics.get("avg_tool_duration", 0)
            if avg_tool_time > 10:  # More than 10 seconds is critical
                status = "critical"
            elif avg_tool_time > 5:  # More than 5 seconds is warning
                status = "warning"
            else:
                status = "good"
            
            metrics.append(PerformanceMetric(
                name="avg_tool_duration",
                value=avg_tool_time,
                unit="seconds",
                description="Average tool execution time",
                status=status
            ))

            # Average LLM call time
            avg_llm_time = self.current_metrics.get("avg_llm_duration", 0)
            if avg_llm_time > 30:  # More than 30 seconds is critical
                status = "critical"
            elif avg_llm_time > 15:  # More than 15 seconds is warning
                status = "warning"
            else:
                status = "good"
            
            metrics.append(PerformanceMetric(
                name="avg_llm_duration",
                value=avg_llm_time,
                unit="seconds",
                description="Average LLM call duration",
                status=status
            ))

            # Success rate
            total_tools = self.current_metrics.get("total_tools", 0)
            successful_tools = self.current_metrics.get("successful_tools", 0)
            success_rate = (successful_tools / total_tools * 100) if total_tools > 0 else 100
            
            if success_rate < 80:  # Less than 80% is critical
                status = "critical"
            elif success_rate < 95:  # Less than 95% is warning
                status = "warning"
            else:
                status = "good"
            
            metrics.append(PerformanceMetric(
                name="success_rate",
                value=success_rate,
                unit="%",
                description="Tool execution success rate",
                status=status
            ))

        return metrics

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        health = {
            "status": "healthy",
            "last_session_time": None,
            "total_sessions": len(self.metrics_history),
            "active_alerts": len([a for a in self.alerts_history if a.get("active", True)]),
            "uptime": self._calculate_uptime(),
            "performance_score": self._calculate_performance_score()
        }

        # Determine overall health status
        if health["active_alerts"] > 5:
            health["status"] = "critical"
        elif health["active_alerts"] > 0:
            health["status"] = "warning"

        return health

    def _calculate_current_metrics(self) -> Dict[str, Any]:
        """Calculate current metrics from history."""
        if not self.metrics_history:
            return {}

        total_tools = 0
        successful_tools = 0
        total_llms = 0
        successful_llms = 0
        total_tool_duration = 0
        total_llm_duration = 0

        for record in self.metrics_history[-10:]:  # Look at last 10 sessions
            stats = record["session_stats"]["tool_executions"]
            total_tools += stats["total"]
            successful_tools += stats["successful"]
            total_tool_duration += stats["avg_duration"] * stats["total"]

            stats = record["session_stats"]["llm_calls"]
            total_llms += stats["total"]
            successful_llms += stats["successful"]
            total_llm_duration += stats["avg_duration"] * stats["total"]

        return {
            "total_tools": total_tools,
            "successful_tools": successful_tools,
            "total_llms": total_llms,
            "successful_llms": successful_llms,
            "avg_tool_duration": total_tool_duration / total_tools if total_tools > 0 else 0,
            "avg_llm_duration": total_llm_duration / total_llms if total_llms > 0 else 0
        }

    def _calculate_uptime(self) -> str:
        """Calculate system uptime."""
        if not self.metrics_history:
            return "0d 0h 0m"
        
        first_timestamp = self.metrics_history[0]["timestamp"]
        uptime = datetime.now() - first_timestamp
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"

    def _calculate_performance_score(self) -> int:
        """Calculate an overall performance score (0-100)."""
        if not self.current_metrics:
            return 100

        score = 100

        # Deduct points for slow tool execution
        avg_tool_time = self.current_metrics.get("avg_tool_duration", 0)
        if avg_tool_time > 10:
            score -= 30
        elif avg_tool_time > 5:
            score -= 15
        elif avg_tool_time > 2:
            score -= 5

        # Deduct points for slow LLM calls
        avg_llm_time = self.current_metrics.get("avg_llm_duration", 0)
        if avg_llm_time > 30:
            score -= 30
        elif avg_llm_time > 15:
            score -= 15
        elif avg_llm_time > 5:
            score -= 5

        # Deduct points for low success rate
        total_tools = self.current_metrics.get("total_tools", 1)
        successful_tools = self.current_metrics.get("successful_tools", 0)
        success_rate = successful_tools / total_tools * 100
        if success_rate < 80:
            score -= 30
        elif success_rate < 95:
            score -= 10

        return max(0, min(100, score))  # Clamp between 0 and 100

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent session information."""
        return [
            {
                "session_id": record["session_id"],
                "timestamp": record["timestamp"],
                "duration": record["session_stats"]["session_duration"],
                "tools_executed": record["session_stats"]["tool_executions"]["total"],
                "llm_calls": record["session_stats"]["llm_calls"]["total"],
                "status": "completed"  # Could be enhanced with actual status
            }
            for record in self.metrics_history[-limit:]
        ]

    def get_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of recent alerts."""
        recent_alerts = [a for a in self.alerts_history[-20:] if a.get("timestamp", datetime.min) >= datetime.now() - timedelta(hours=24)]
        
        return {
            "total_alerts": len(recent_alerts),
            "error_alerts": len([a for a in recent_alerts if a.get("type") == "error"]),
            "performance_alerts": len([a for a in recent_alerts if a.get("type") == "performance"]),
            "recent_alerts": recent_alerts[-5:]  # Last 5 alerts
        }

    def add_alert(self, alert: Dict[str, Any]):
        """Add an alert to the dashboard."""
        self.alerts_history.append(alert)

    def generate_dashboard_report(self) -> str:
        """Generate a text-based dashboard report."""
        health = self.get_system_health()
        metrics = self.get_performance_metrics()
        alerts = self.get_alerts_summary()
        recent_sessions = self.get_recent_sessions(limit=5)

        report = []
        report.append("=" * 60)
        report.append("NETWORK AUTOMATION AGENT - MONITORING DASHBOARD")
        report.append("=" * 60)
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"System Status: {health['status'].upper()}")
        report.append(f"Uptime: {health['uptime']}")
        report.append(f"Performance Score: {health['performance_score']}/100")
        report.append(f"Total Sessions: {health['total_sessions']}")
        report.append(f"Active Alerts: {health['active_alerts']}")
        report.append("")

        report.append("PERFORMANCE METRICS:")
        report.append("-" * 30)
        for metric in metrics:
            status_emoji = {"good": "✅", "warning": "⚠️", "critical": "❌"}[metric.status]
            report.append(f"{status_emoji} {metric.name}: {metric.value:.2f} {metric.unit} - {metric.description}")
        report.append("")

        report.append("RECENT SESSIONS:")
        report.append("-" * 30)
        for session in recent_sessions:
            report.append(f"• {session['session_id'][:8]} - Duration: {session['duration']:.2f}s, "
                         f"Tools: {session['tools_executed']}, LLM: {session['llm_calls']}")
        report.append("")

        report.append("ALERT SUMMARY:")
        report.append("-" * 30)
        report.append(f"Total Recent Alerts: {alerts['total_alerts']}")
        report.append(f"Error Alerts: {alerts['error_alerts']}")
        report.append(f"Performance Alerts: {alerts['performance_alerts']}")
        report.append("")

        if alerts["recent_alerts"]:
            report.append("RECENT ALERTS:")
            report.append("-" * 30)
            for alert in alerts["recent_alerts"][-3:]:  # Show last 3 alerts
                report.append(f"• [{alert['type'].upper()}] {alert['message'][:100]}...")
        report.append("")

        report.append("=" * 60)

        return "\n".join(report)


# Global dashboard instance
_dashboard_instance = None


def get_dashboard() -> MonitoringDashboard:
    """Get the global monitoring dashboard instance."""
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = MonitoringDashboard()
    return _dashboard_instance
