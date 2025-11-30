"""Enhanced UI components for the Network AI Agent with color separation.

This module provides improved user interface elements with clear separation
between logging, input, and output using color coding and visual boundaries.
"""

import json
import logging

from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class NetworkAgentUI:
    """Enhanced UI for the Network AI Agent with color separation."""

    def __init__(self):
        self.console = Console()
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
        header_text = Text("🚀 Network AI Agent", style="bold blue")
        header_text.append("\n\nNetwork Automation with AI", style="italic")

        self.console.print(
            Panel(
                header_text,
                title="[bold green]Welcome[/bold green]",
                border_style="green",
                expand=False,
            )
        )
        self.console.print()  # Empty line for spacing

    def print_footer(self):
        """Print footer with help information."""
        footer_text = Text("Type 'exit' or 'quit' to end the session", style="dim")
        footer_text.append(
            "\nFor network commands, simply describe what you want to do", style="dim"
        )

        self.console.print(
            Panel(
                footer_text,
                title="[bold yellow]Usage[/bold yellow]",
                border_style="yellow",
                expand=False,
            )
        )

    def print_command_input_prompt(self) -> str:
        """Display input prompt and get command from user."""
        # Use prompt_toolkit for input with history
        message = [
            ("class:username", "User"),
            ("class:colon", " > "),
        ]
        try:
            command = self.session.prompt(message).strip()
            return command
        except KeyboardInterrupt:
            return ""

    def _print_structured_data(self, data: dict):
        """Helper to print structured network response."""
        self.console.print("[bold cyan]Structured Data:[/bold cyan]")
        self.console.print_json(data=data.get("structured_data"))

        self.console.print("\n[bold green]Summary:[/bold green]")
        self.console.print(Markdown(data.get("summary", "")))
        self.console.print()

        if data.get("errors"):
            self.console.print(f"\n[bold red]Errors:[/bold red] {data['errors']}")

    def print_output(self, content: str | dict):
        """Display the command output with clear separation."""

        data_to_print = content

        # 1. Normalize input to dict if possible
        if isinstance(content, str):
            try:
                data_to_print = json.loads(content)
            except json.JSONDecodeError:
                # Not JSON, treat as Markdown string
                self.console.print(Markdown(content))
                self.console.print()  # Empty line
                return

        # 2. Print based on type
        if isinstance(data_to_print, dict) and "structured_data" in data_to_print:
            self._print_structured_data(data_to_print)
        elif isinstance(data_to_print, (dict, list)):
            self.console.print_json(data=data_to_print)
        else:
            # Fallback for non-json string or other types
            self.console.print(content)

        # Add empty line for spacing
        self.console.print()

    def print_logging_separator(self):
        """Print a separator specifically for logging messages."""
        self.console.print("-" * 60, style="dim")

    def print_goodbye(self):
        """Display goodbye message."""
        self.console.print("\n[bold blue]👋 Goodbye![/bold blue]")

    def print_session_interruption(self):
        """Display session interruption message."""
        self.console.print("\n[bold blue]👋 Session interrupted. Goodbye![/bold blue]")

    def print_error(self, error_msg: str):
        """Display error messages with appropriate styling."""
        self.console.print(f"[bold red]❌ Error:[/bold red] {error_msg}")

    def print_warning(self, warning_msg: str):
        """Display warning messages with appropriate styling."""
        self.console.print(f"[bold yellow]⚠️  Warning:[/bold yellow] {warning_msg}")

    def print_approval_request(self, action: str, args: dict):
        """Display approval request with clear visual indication."""
        self.console.print(
            Panel(
                f"[bold]Action:[/bold] {action}\n[bold]Args:[/bold] {args}",
                title="[bold red]⚠️  CONFIGURATION CHANGE DETECTED ⚠️[/bold red]",
                border_style="red",
                expand=False,
            )
        )

    def get_approval_decision(self) -> str:
        """Get user decision for approval with styling."""
        message = [
            ("bold", "Proceed with configuration change? (yes/no): "),
        ]
        return self.session.prompt(message).strip().lower()

    def thinking_status(self, message: str = "Thinking..."):
        """Return a status spinner context manager."""
        return self.console.status(f"[bold green]{message}[/bold green]", spinner="dots")


class ColoredLogHandler(logging.Handler):
    """Custom log handler that displays logs with colors separate from user interaction."""

    def __init__(self, console: Console):
        super().__init__()
        self.console = console

    def emit(self, record):
        """Emit a log record with appropriate coloring."""
        try:
            # Color mapping based on log level
            if record.levelno >= logging.ERROR:
                style = "bold red"
                level_prefix = "ERROR"
            elif record.levelno >= logging.WARNING:
                style = "bold yellow"
                level_prefix = "WARN"
            elif record.levelno >= logging.INFO:
                style = "cyan"
                level_prefix = "INFO"
            else:
                style = "dim"
                level_prefix = "DEBUG"

            # Skip very verbose logs from third-party libraries that clutter the UI
            from settings import LOG_SKIP_MODULES

            if any(skip_name in record.name for skip_name in LOG_SKIP_MODULES):
                return  # Skip these logs to keep UI clean

            # Display log message with color-coded level and visual separation
            message = record.getMessage()
            if record.levelno >= logging.ERROR and "failed with traceback" in message:
                message = message.splitlines()[0]

            self.console.print(f"[{style}]│ {level_prefix}: {message} │[/]", style=style)

        except Exception:
            self.handleError(record)


def setup_colored_logging():
    """Setup colored logging that doesn't interfere with UI elements.

    Creates its own Console instance for logging to avoid requiring
    external console management.
    """
    console = Console()
    handler = ColoredLogHandler(console)
    handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    return handler
