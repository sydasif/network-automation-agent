"""Core infrastructure package for network automation.

This package provides the foundational infrastructure components:
- Configuration management
- Nornir lifecycle management
- Device inventory
- Task execution engine
- LLM provider

These components have no dependencies on agent or tools packages.
"""

from core.config import NetworkAgentConfig
from core.device_inventory import DeviceInventory
from core.llm_provider import LLMProvider
from core.nornir_manager import NornirManager
from core.task_executor import TaskExecutor

__all__ = [
    "NetworkAgentConfig",
    "NornirManager",
    "DeviceInventory",
    "TaskExecutor",
    "LLMProvider",
]
