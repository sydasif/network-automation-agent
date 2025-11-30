import os
import sys
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def mock_llm():
    """Mock the LLM to avoid API calls during tests."""
    mock = MagicMock()
    mock.invoke.return_value.content = "Mocked response"
    return mock


@pytest.fixture
def mock_nornir():
    """Mock Nornir to avoid network calls."""
    mock = MagicMock()
    return mock
