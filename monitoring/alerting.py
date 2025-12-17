"""Alerting system for the Network Automation Agent."""

import logging
from typing import Dict, Any, Callable, List
from datetime import datetime, timedelta
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""
    PERFORMANCE = "performance"
    ERROR = "error"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SECURITY = "security"


class Alert:
    """Represents an alert in the system."""

    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Dict[str, Any] = None,
        session_id: str = None
    ):
        self.id = f"alert_{datetime.now().timestamp()}"
        self.timestamp = datetime.now()
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.details = details or {}
        self.session_id = session_id
        self.resolved = False
        self.resolved_at = None

    def resolve(self):
        """Mark the alert as resolved."""
        self.resolved = True
        self.resolved_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "session_id": self.session_id,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class AlertManager:
    """Manages alerting for the Network Automation Agent."""

    def __init__(self):
        self.alerts: List[Alert] = []
        self.handlers: List[Callable[[Alert], None]] = []
        self.email_config = None
        self.slack_webhook_url = None

    def set_email_config(self, smtp_server: str, smtp_port: int, username: str, password: str, recipients: List[str]):
        """Configure email alerting."""
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "recipients": recipients
        }

    def set_slack_webhook(self, webhook_url: str):
        """Configure Slack alerting."""
        self.slack_webhook_url = webhook_url

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add an alert handler function."""
        self.handlers.append(handler)

    def trigger_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        details: Dict[str, Any] = None,
        session_id: str = None
    ) -> Alert:
        """Trigger a new alert."""
        alert = Alert(alert_type, severity, message, details, session_id)
        self.alerts.append(alert)

        logger.warning(f"ALERT [{severity.value.upper()} - {alert_type.value.upper()}]: {message}")

        # Execute handlers
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

        # Send notifications
        self._send_notifications(alert)

        return alert

    def _send_notifications(self, alert: Alert):
        """Send alert notifications."""
        if alert.severity.value in ["high", "critical"]:
            if self.email_config:
                self._send_email_notification(alert)
            if self.slack_webhook_url:
                self._send_slack_notification(alert)

    def _send_email_notification(self, alert: Alert):
        """Send email notification for the alert."""
        if not self.email_config:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = ', '.join(self.email_config['recipients'])
            msg['Subject'] = f"Network Agent Alert: {alert.severity.value.upper()} - {alert.message[:50]}..."

            body = f"""
            Network Automation Agent Alert

            Type: {alert.alert_type.value}
            Severity: {alert.severity.value.upper()}
            Message: {alert.message}
            Timestamp: {alert.timestamp}
            Session ID: {alert.session_id}

            Details: {alert.details}
            """

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()

            logger.info(f"Email notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification for the alert."""
        if not self.slack_webhook_url:
            return

        import requests

        try:
            color_map = {
                "low": "#65C365",  # Green
                "medium": "#FFA500",  # Orange
                "high": "#FF6B6B",  # Red
                "critical": "#FF0000"  # Bright Red
            }

            payload = {
                "text": f"🚨 Network Agent Alert: {alert.message}",
                "attachments": [
                    {
                        "color": color_map.get(alert.severity.value, "#36a64f"),
                        "fields": [
                            {
                                "title": "Type",
                                "value": alert.alert_type.value,
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Session ID",
                                "value": alert.session_id or "N/A",
                                "short": True
                            },
                            {
                                "title": "Details",
                                "value": str(alert.details),
                                "short": False
                            }
                        ],
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }

            response = requests.post(self.slack_webhook_url, json=payload)
            if response.status_code == 200:
                logger.info(f"Slack notification sent for alert {alert.id}")
            else:
                logger.error(f"Failed to send Slack notification: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    def get_unresolved_alerts(self) -> List[Alert]:
        """Get all unresolved alerts."""
        return [alert for alert in self.alerts if not alert.resolved]

    def get_alerts_by_severity(self, severity: AlertSeverity) -> List[Alert]:
        """Get alerts by severity level."""
        return [alert for alert in self.alerts if alert.severity == severity]

    def get_alerts_by_type(self, alert_type: AlertType) -> List[Alert]:
        """Get alerts by type."""
        return [alert for alert in self.alerts if alert.alert_type == alert_type]

    def get_alerts_in_time_range(self, start_time: datetime, end_time: datetime) -> List[Alert]:
        """Get alerts in a specific time range."""
        return [
            alert for alert in self.alerts
            if start_time <= alert.timestamp <= end_time
        ]

    def resolve_alert(self, alert_id: str):
        """Resolve an alert by ID."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolve()
                logger.info(f"Alert {alert_id} resolved")
                return True
        return False

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get a summary of alerts."""
        total_alerts = len(self.alerts)
        unresolved_alerts = len(self.get_unresolved_alerts())
        
        severity_counts = {}
        type_counts = {}
        
        for alert in self.alerts:
            severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
            type_counts[alert.alert_type.value] = type_counts.get(alert.alert_type.value, 0) + 1

        return {
            "total_alerts": total_alerts,
            "unresolved_alerts": unresolved_alerts,
            "severity_breakdown": severity_counts,
            "type_breakdown": type_counts,
            "last_24h_count": len(self.get_alerts_in_time_range(
                datetime.now() - timedelta(hours=24),
                datetime.now()
            ))
        }


# Global alert manager instance
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """Get the global alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def trigger_workflow_failure_alert(error: Exception, session_id: str = None):
    """Helper function to trigger workflow failure alerts."""
    alert_manager = get_alert_manager()
    return alert_manager.trigger_alert(
        AlertType.FAILURE,
        AlertSeverity.HIGH,
        f"Workflow execution failed: {str(error)}",
        {"error_type": type(error).__name__, "session_id": session_id},
        session_id
    )


def trigger_slow_execution_alert(duration: float, threshold: float, session_id: str = None):
    """Helper function to trigger slow execution alerts."""
    alert_manager = get_alert_manager()
    return alert_manager.trigger_alert(
        AlertType.PERFORMANCE,
        AlertSeverity.MEDIUM,
        f"Slow execution detected: {duration:.2f}s (threshold: {threshold}s)",
        {"duration": duration, "threshold": threshold},
        session_id
    )
