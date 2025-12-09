"""Bootstrapper for initializing application dependencies."""

from agent.workflow_manager import NetworkAgentWorkflow
from core.config import NetworkAgentConfig
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.nornir_manager import NornirManager
from core.task_executor import TaskExecutor
from tools import create_tools
from ui.console_ui import NetworkAgentUI


class AppBootstrapper:
    """Handles dependency initialization and app setup."""

    def __init__(self, config: NetworkAgentConfig):
        self.config = config
        self._objects = {}

    def build_app(self) -> dict:
        """Build all dependencies in correct order."""
        # Initialize in dependency order
        self._objects["nornir"] = NornirManager(self.config)
        self._objects["inventory"] = DeviceInventory(self._objects["nornir"])
        self._objects["executor"] = TaskExecutor(self._objects["nornir"])
        self._objects["llm"] = LLMProvider(self.config)
        # Create tools registry (tools will obtain runtime dependencies via InjectedState)
        self._objects["tools"] = create_tools(self._objects["executor"])
        self._objects["workflow"] = NetworkAgentWorkflow(
            llm_provider=self._objects["llm"],
            device_inventory=self._objects["inventory"],
            task_executor=self._objects["executor"],
            tools=self._objects["tools"],
        ).build()
        self._objects["ui"] = NetworkAgentUI()

        return self._objects
