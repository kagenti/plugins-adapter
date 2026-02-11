"""Unit tests for ext-proc server functions

These tests use dynamic import and mocking to avoid proto dependencies.
"""

# Standard
from unittest.mock import AsyncMock, Mock, MagicMock
import sys

# Third-Party
import pytest

# First-Party
from mcpgateway.plugins.framework import (
    ToolPostInvokeResult,
    ToolPostInvokePayload,
    PluginViolation,
)


@pytest.fixture
def mock_envoy_modules():
    """Mock envoy protobuf modules to avoid proto dependencies."""
    # Create mock modules
    mock_ep = MagicMock()
    mock_ep_grpc = MagicMock()
    mock_core = MagicMock()
    mock_http_status = MagicMock()

    # Add to sys.modules before importing server
    sys.modules["envoy"] = MagicMock()
    sys.modules["envoy.service"] = MagicMock()
    sys.modules["envoy.service.ext_proc"] = MagicMock()
    sys.modules["envoy.service.ext_proc.v3"] = MagicMock()
    sys.modules["envoy.service.ext_proc.v3.external_processor_pb2"] = mock_ep
    sys.modules["envoy.service.ext_proc.v3.external_processor_pb2_grpc"] = (
        mock_ep_grpc
    )
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

    # Cleanup
    for key in list(sys.modules.keys()):
        if key.startswith("envoy"):
            del sys.modules[key]
    if "src.server" in sys.modules:
        del sys.modules["src.server"]


@pytest.fixture
def mock_manager():
    """Create a mock PluginManager."""
    mock = Mock()
    mock.invoke_hook = AsyncMock()
    return mock


@pytest.fixture
def sample_tool_result_body():
    """Create a sample tool result body."""
    return {
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {
            "content": [{"type": "text", "text": "Tool execution result"}]
        },
    }


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_continue_processing(
    mock_envoy_modules, mock_manager, sample_tool_result_body
):
    """Test getToolPostInvokeResponse when plugin allows processing to continue."""
    # Setup mock response objects
    mock_response = MagicMock()
    mock_response.HasField.return_value = True
    mock_response.response_body.response.HasField.return_value = False
    mock_envoy_modules["ep"].ProcessingResponse.return_value = mock_response

    # Import server after mocking
    import src.server

    # Setup mock to return continue_processing=True
    mock_result = ToolPostInvokeResult(
        continue_processing=True,
        modified_payload=None,
    )
    mock_manager.invoke_hook.return_value = (mock_result, None)

    # Inject mock manager
    src.server.manager = mock_manager

    # Call the function
    _ = await src.server.getToolPostInvokeResponse(sample_tool_result_body)

    # Verify the hook was called
    assert mock_manager.invoke_hook.called
    call_args = mock_manager.invoke_hook.call_args[0]
    payload = call_args[1]
    assert isinstance(payload, ToolPostInvokePayload)
    assert payload.result == sample_tool_result_body["result"]
    # assert payload.name == "replaceme" # Replace this after better naming


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_blocked(
    mock_envoy_modules, mock_manager, sample_tool_result_body
):
    """Test getToolPostInvokeResponse when plugin blocks the response."""
    # Import server after mocking
    import src.server

    # Setup mock to return continue_processing=False with violation
    violation = PluginViolation(
        reason="Sensitive content detected",
        description="Tool response contains forbidden content",
        code="CONTENT_VIOLATION",
    )
    mock_result = ToolPostInvokeResult(
        continue_processing=False,
        violation=violation,
    )
    mock_manager.invoke_hook.return_value = (mock_result, None)

    # Inject mock manager
    src.server.manager = mock_manager

    # Call the function
    response = await src.server.getToolPostInvokeResponse(
        sample_tool_result_body
    )

    # Verify the hook was called with correct payload
    assert mock_manager.invoke_hook.called
    call_args = mock_manager.invoke_hook.call_args[0]
    payload = call_args[1]
    assert isinstance(payload, ToolPostInvokePayload)
    assert payload.result == sample_tool_result_body["result"]

    # Verify response was created (error path taken)
    assert response is not None


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_modified_payload(
    mock_envoy_modules, mock_manager, sample_tool_result_body
):
    """Test getToolPostInvokeResponse when plugin modifies the payload."""
    # Import server after mocking
    import src.server

    # Setup mock to return modified payload
    modified_result = {
        "content": [{"type": "text", "text": "Modified tool result"}]
    }
    modified_payload = ToolPostInvokePayload(
        name="test_tool", result=modified_result
    )
    mock_result = ToolPostInvokeResult(
        continue_processing=True,
        modified_payload=modified_payload,
    )
    mock_manager.invoke_hook.return_value = (mock_result, None)

    # Inject mock manager
    src.server.manager = mock_manager

    # Call the function
    response = await src.server.getToolPostInvokeResponse(
        sample_tool_result_body
    )

    # Verify the hook was called
    assert mock_manager.invoke_hook.called

    # Verify response was created
    assert response is not None


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_multiple_content_items(
    mock_envoy_modules, mock_manager
):
    """Test getToolPostInvokeResponse with multiple content items."""
    # Setup mock response
    mock_response = MagicMock()
    mock_envoy_modules["ep"].ProcessingResponse.return_value = mock_response

    # Import server after mocking
    import src.server

    body = {
        "jsonrpc": "2.0",
        "id": "test-789",
        "result": {
            "content": [
                {"type": "text", "text": "First item"},
                {"type": "text", "text": "Second item"},
                {"type": "image", "url": "http://example.com/img.png"},
            ]
        },
    }

    mock_result = ToolPostInvokeResult(continue_processing=True)
    mock_manager.invoke_hook.return_value = (mock_result, None)

    # Inject mock manager
    src.server.manager = mock_manager

    # Call the function
    _ = await src.server.getToolPostInvokeResponse(body)

    # Verify the payload passed to the hook contains all content
    call_args = mock_manager.invoke_hook.call_args[0]
    payload = call_args[1]
    assert len(payload.result["content"]) == 3
    assert payload.result["content"][0]["text"] == "First item"
    assert payload.result["content"][1]["text"] == "Second item"
    assert payload.result["content"][2]["url"] == "http://example.com/img.png"
