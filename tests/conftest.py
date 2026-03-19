"""Shared pytest fixtures for plugins-adapter unit tests."""

# Standard
import json
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

# Third-Party
import pytest


def make_hook_result(continue_processing=True, modified_payload=None, violation=None):
    """Build a mock hook result for plugin manager invoke_hook calls."""
    result = Mock()
    result.continue_processing = continue_processing
    result.modified_payload = modified_payload
    result.violation = violation
    return result


@pytest.fixture
def mock_envoy_modules():
    """Mock envoy protobuf modules to avoid proto build dependencies."""
    mock_ep = MagicMock()
    mock_ep_grpc = MagicMock()
    mock_core = MagicMock()
    mock_http_status = MagicMock()

    sys.modules["envoy"] = MagicMock()
    sys.modules["envoy.service"] = MagicMock()
    sys.modules["envoy.service.ext_proc"] = MagicMock()
    sys.modules["envoy.service.ext_proc.v3"] = MagicMock()
    sys.modules["envoy.service.ext_proc.v3.external_processor_pb2"] = mock_ep
    sys.modules["envoy.service.ext_proc.v3.external_processor_pb2_grpc"] = mock_ep_grpc
    sys.modules["envoy.config"] = MagicMock()
    sys.modules["envoy.config.core"] = MagicMock()
    sys.modules["envoy.config.core.v3"] = MagicMock()
    sys.modules["envoy.config.core.v3.base_pb2"] = mock_core
    sys.modules["envoy.type"] = MagicMock()
    sys.modules["envoy.type.v3"] = MagicMock()
    sys.modules["envoy.type.v3.http_status_pb2"] = mock_http_status

    yield {
        "ep": mock_ep,
        "ep_grpc": mock_ep_grpc,
        "core": mock_core,
        "http_status": mock_http_status,
    }

    for key in list(sys.modules.keys()):
        if key.startswith("envoy"):
            del sys.modules[key]
    if "src.server" in sys.modules:
        del sys.modules["src.server"]


@pytest.fixture
def mock_manager():
    """Create a mock PluginManager with async invoke_hook."""
    mock = Mock()
    mock.invoke_hook = AsyncMock()
    return mock


@pytest.fixture
def sample_tool_result_body():
    """Sample MCP tool result response body."""
    return {
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {"content": [{"type": "text", "text": "Tool execution result"}]},
    }
