"""Enhanced UI components for the Network AI Agent with color separation.

This module provides improved user interface elements with clear separation
between logging, input, and output using color coding and visual boundaries.
"""

import json
import logging
import re
from typing import ContextManager

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status  # Import Status type
from rich.table import Table
from rich.text import Text
from rich.theme import Theme


# Emoji constants for consistent usage throughout the UI
class Emoji:
    """Emoji constants for the Network AI Agent UI."""

    # Status indicators
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = ""
    DEBUG = "🔍"

    # Actions
    ROCKET = "🚀"
    GEAR = "⚙️"
    WRENCH = "🔧"
    THINKING = ""
    EXECUTING = "🌐"
    WRITE = "📝"  # Added for Response Node

    # Network specific
    NETWORK = "🌐"
    DEVICE = "🖥️"
    CONNECTED = "🔗"
    DISCONNECTED = "🔌"

    # Results
    RESULT = "📊"
    DATA = "📋"
    CONFIG = "📝"

    # User interaction
    USER = "👤"
    AI = "🔷"
    WAVE = "👋"
    QUESTION = "❓"
    APPROVAL = "🔐"


class NetworkAgentUI:
    """Enhanced UI for the Network AI Agent with color separation."""

    def __init__(self):
        # Define custom theme for distinct JSON highlighting
        custom_theme = Theme(
            {
                "json.str": "orange1",
                "json.number": "orange1",
                "json.bool": "orange1",
                "json.null": "orange1",
                "json.key": "bold cyan",
                "markdown.strong": "bold cyan",
            }
        )
        self.console = Console(theme=custom_theme)
        self.log_handler = None
        # Create a style for the prompt
        self.style = Style.from_dict(
            {
                "username": "#ansiblue bold",
                "at": "#ansigreen",
                "host": "#ansicyan bold",
                "colon": "#ansiyellow",
            }
        )
        self.session = PromptSession(style=self.style)

    def print_header(self):
        """Print the application header with session information."""
        header_text = Text(f"{Emoji.ROCKET} AI Agent", style="bold blue")
        header_text.append(f"\n{Emoji.NETWORK} Network Automation with AI", style="italic")

        self.console.print(
            Panel(
                header_text,
                title=f"[bold green]{Emoji.SUCCESS} Welcome[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        self.console.print()  # Empty line for spacing

    def print_footer(self):
        """Print footer with help information."""
        footer_text = Text(f"{Emoji.INFO} Type 'exit' or 'quit' to end the session", style="dim")
        footer_text.append(
            f"\n{Emoji.WRENCH} For network commands, simply describe what you want to do",
            style="dim",
        )

        self.console.print(
            Panel(
                footer_text,
                title=f"[bold yellow]{Emoji.QUESTION} Usage[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    def print_command_input_prompt(self) -> str:
        """Display input prompt and get command from user."""
        # Use prompt_toolkit for input with history
        message = [
            ("class:username", f"{Emoji.USER} User"),
            ("class:colon", " > "),
        ]
        try:
            command = self.session.prompt(message).strip()
            return command
        except KeyboardInterrupt:
            return ""

    def _style_summary_keys(self, text: str) -> str:
        """Enhance markdown summary by bolding keys in list items."""
        pattern = r"(?m)^(\s*[-*]\s+)([^:\n*]+)(:)"
        return re.sub(pattern, r"\1**\2**\3", text)

    def print_output(self, content, metadata=None):
        """Display the command output with clear separation."""

        metadata = metadata or {}

        def render_content(text_content):
            """Helper to render content inline with the label using a Grid."""
            grid = Table.grid(padding=(0, 1))
            grid.add_column(style="bold blue", no_wrap=True)
            grid.add_column()  # Content column expands

            # The Markdown class renders block elements, but inside a grid cell
            # it aligns relatively well with the label.
            grid.add_row(f"{Emoji.AI} AI >", Markdown(text_content))
            self.console.print(grid)
            self.console.print()  # Add spacing

        # Handle structured data as dictionary (new standard)
        if isinstance(content, dict):
            # A. Print the conversational message (Summary)
            if "message" in content and content["message"]:
                render_content(content["message"])
            elif "error" in content:
                # Fallback if message is missing but error exists
                self.console.print(f"[bold red]{Emoji.ERROR} Error:[/bold red] {content['error']}")
                self.console.print()
            elif not content:
                # Empty dictionary
                pass
            else:
                # Dictionary with other keys but no message
                self.console.print(f"[bold blue]{Emoji.AI} AI (Raw Output) >[/bold blue]")
                self.console.print(JSON.from_data(content))
                self.console.print()
        # Handle string content
        elif isinstance(content, str):
            # Check if this is structured response type (from response node with metadata)
            if metadata.get("type") == "structured_response":
                try:
                    parsed_content = json.loads(content)
                    # If it's a structured response, handle as dict
                    if isinstance(parsed_content, dict):
                        if "message" in parsed_content and parsed_content["message"]:
                            render_content(parsed_content["message"])
                        elif "error" in parsed_content:
                            self.console.print(
                                f"[bold red]{Emoji.ERROR} Error:[/bold red] {parsed_content['error']}"
                            )
                            self.console.print()
                        elif not parsed_content:
                            pass
                        else:
                            self.console.print(
                                f"[bold blue]{Emoji.AI} AI (Raw Output) >[/bold blue]"
                            )
                            self.console.print(JSON.from_data(parsed_content))
                            self.console.print()
                        return
                except json.JSONDecodeError:
                    pass

            # For regular strings or if JSON parsing failed, use the inline renderer
            render_content(content)
        else:
            # Handle other types by converting to string
            render_content(str(content))

    def print_logging_separator(self):
        """Print a separator specifically for logging messages."""
        self.console.print("-" * 60, style="dim")

    def print_goodbye(self):
        """Display goodbye message."""
        self.console.print(f"\n[bold blue]{Emoji.WAVE} Goodbye![/bold blue]")

    def print_session_interruption(self):
        """Display session interruption message."""
        self.console.print(f"\n[bold blue]{Emoji.WAVE} Session interrupted. Goodbye![/bold blue]")

    def print_error(self, error_msg: str):
        """Display error messages with appropriate styling."""
        self.console.print(f"[bold red]{Emoji.ERROR} Error:[/bold red] {error_msg}")

    def print_warning(self, warning_msg: str):
        """Display warning messages with appropriate styling."""
        self.console.print(f"[bold yellow]{Emoji.WARNING}  Warning:[/bold yellow] {warning_msg}")

    def print_approval_request(self, tool_calls: list[dict]):
        """Display approval request for multiple tool calls with enhanced risk assessment."""
        content = Text()

        # Get risk summary if available
        risk_summary = None
        if isinstance(tool_calls, dict) and "tool_calls" in tool_calls:
            # Handle the case where the input is the full approval request dict
            risk_summary = tool_calls.get("risk_summary", {})
            tool_calls = tool_calls.get("tool_calls", [])
        elif len(tool_calls) > 0 and "risk_level" in tool_calls[0]:
            # If individual calls have risk level, calculate summary
            risk_summary = {
                "high": sum(1 for call in tool_calls if call.get("risk_level") == "high"),
                "medium": sum(1 for call in tool_calls if call.get("risk_level") == "medium"),
                "low": sum(1 for call in tool_calls if call.get("risk_level") == "low")
            }

        # Display risk summary if available
        if risk_summary:
            high_risk = risk_summary.get("high", 0)
            medium_risk = risk_summary.get("medium", 0)
            low_risk = risk_summary.get("low", 0)

            risk_text = Text()
            if high_risk > 0:
                risk_text.append(f"{Emoji.ERROR} HIGH RISK: {high_risk} operations ", style="bold red")
            if medium_risk > 0:
                risk_text.append(f"{Emoji.WARNING} MEDIUM RISK: {medium_risk} operations ", style="bold yellow")
            if low_risk > 0:
                risk_text.append(f"{Emoji.INFO} LOW RISK: {low_risk} operations ", style="bold green")

            content.append(risk_text)
            content.append("\n")
            content.append("=" * 60 + "\n", style="bold")

        for i, call in enumerate(tool_calls, 1):
            action = call.get("name")
            args = call.get("args")
            risk_level = call.get("risk_level", "unknown")

            # Determine styling based on risk level
            if risk_level == "high":
                risk_emoji = Emoji.ERROR
                risk_style = "bold red"
            elif risk_level == "medium":
                risk_emoji = Emoji.WARNING
                risk_style = "bold yellow"
            elif risk_level == "low":
                risk_emoji = Emoji.SUCCESS
                risk_style = "bold green"
            else:
                risk_emoji = Emoji.QUESTION
                risk_style = "bold white"

            content.append(f"\n{Emoji.GEAR} Operation {i} ({risk_emoji} {risk_level.upper()} RISK):\n", style=risk_style)
            content.append(f"{Emoji.DATA} Action: {action}\n", style="bold cyan")
            content.append(f"{Emoji.CONFIG} Args: {json.dumps(args, indent=2)}\n", style="yellow")

            if i < len(tool_calls):
                content.append("-" * 60 + "\n", style="dim")

        # Add warning about irreversible changes
        if risk_summary and risk_summary.get("high", 0) > 0:
            content.append(f"\n{Emoji.WARNING} WARNING: High-risk operations may cause service disruption!\n", style="bold red")
            content.append("Please review carefully before approving.\n", style="bold red")

        self.console.print(
            Panel(
                content,
                title=f"[bold red]{Emoji.APPROVAL} CONFIGURATION CHANGE REQUEST ({len(tool_calls)} Operations) {Emoji.APPROVAL}[/bold red]",
                border_style="red",
                expand=False,
            )
        )

    def get_approval_decision(self) -> str:
        """Get user decision for approval with styling."""
        message = [
            ("bold", f"{Emoji.QUESTION} Proceed with configuration change? (yes/no): "),
        ]
        return self.session.prompt(message).strip().lower()

    def thinking_status(self, message: str = "Thinking...") -> ContextManager[Status]:
        """Return a status spinner context manager.

        The returned object is a rich.status.Status which supports .update(text="new text").
        """
        return self.console.status(
            f"[bold green]{Emoji.THINKING} {message}[/bold green]", spinner="dots"
        )

    def print_device_status(self, device: str, status: str, message: str = ""):
        """Display device connection status."""
        if status == "connected":
            emoji = Emoji.CONNECTED
            style = "green"
        elif status == "disconnected":
            emoji = Emoji.DISCONNECTED
            style = "red"
        else:
            emoji = Emoji.DEVICE
            style = "yellow"

        output = f"[{style}]{emoji} {Emoji.DEVICE} {device}[/{style}]"
        if message:
            output += f": {message}"
        self.console.print(output)

    def print_executing(self, action: str):
        """Display action being executed."""
        self.console.print(f"[cyan]{Emoji.EXECUTING} Executing: {action}[/cyan]")

    def print_config_applied(self, device: str):
        """Display configuration applied message."""
        self.console.print(
            f"[green]{Emoji.SUCCESS} {Emoji.CONFIG} Configuration applied to {device}[/green]"
        )

    def print_result_header(self, title: str):
        """Print result section header with emoji."""
        self.console.print(f"\n[bold]{Emoji.RESULT} {title}[/bold]")


class ColoredLogHandler(logging.Handler):
    """Custom log handler that displays logs with colors separate from user interaction."""

    def __init__(self, console: Console):
        super().__init__()
        self.console = console

    def emit(self, record):
        """Emit a log record with appropriate coloring and emojis."""
        try:
            # Color and emoji mapping based on log level
            if record.levelno >= logging.ERROR:
                style = "bold red"
                level_prefix = f"{Emoji.ERROR}  ERROR"
            elif record.levelno >= logging.WARNING:
                style = "bold yellow"
                level_prefix = f"{Emoji.WARNING}  WARN"
            elif record.levelno >= logging.INFO:
                style = "dim green"
                level_prefix = f"{Emoji.INFO}  INFO"
            else:
                style = "dim"
                level_prefix = f"{Emoji.DEBUG}  DEBUG"

            # Skip very verbose logs from third-party libraries that clutter the UI
            from core.config import NetworkAgentConfig

            # Get log skip modules from config
            config = NetworkAgentConfig()
            if any(skip_name in record.name for skip_name in config.log_skip_modules):
                return  # Skip these logs to keep UI clean

            # Display log message with color-coded level and visual separation
            message = record.getMessage()
            if record.levelno >= logging.ERROR and "failed with traceback" in message:
                message = message.splitlines()[0]

            self.console.print(f"[{style}]{level_prefix}: {message}[/]", style=style)

        except Exception:
            self.handleError(record)


def setup_colored_logging(level: int = logging.INFO):
    """Setup colored logging that doesn't interfere with UI elements.

    Args:
        level: logging level for the console handler.

    Creates its own Console instance for logging to avoid requiring
    external console management.
    """
    console = Console()
    handler = ColoredLogHandler(console)
    handler.setFormatter(logging.Formatter("{levelname} - {message}", style="{"))
    handler.setLevel(level)  # Set the handler's level

    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)

    # Suppress INFO messages from nornir.core regardless of handler level
    # because they are very verbose during execution
    logging.getLogger("nornir.core").setLevel(logging.WARNING)

    return handler
