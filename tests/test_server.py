"""Unit tests for ext-proc server functions

These tests use dynamic import and mocking to avoid proto dependencies.
"""

# Standard
from unittest.mock import AsyncMock, Mock, MagicMock
import sys
import json

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


def setup_response_mocks(mock_envoy_modules):
    """Setup common response mocks."""
    mock_envoy_modules["ep"].ProcessingResponse.return_value = MagicMock()
    mock_envoy_modules["ep"].BodyResponse.return_value = MagicMock()
    mock_envoy_modules["ep"].CommonResponse.return_value = MagicMock()


def setup_manager_with_result(mock_manager, continue_processing=True):
    """Setup mock manager with a tool post-invoke result."""
    mock_result = ToolPostInvokeResult(continue_processing=continue_processing)
    mock_manager.invoke_hook.return_value = (mock_result, None)
    return mock_manager


def verify_payload_content(payload, expected_result, expected_text):
    """Verify payload contains expected content."""
    assert isinstance(payload, ToolPostInvokePayload)
    assert payload.result == expected_result
    assert payload.result["content"][0]["type"] == "text"
    assert payload.result["content"][0]["text"] == expected_text


# ============================================================================
# Tool Post-Invoke Hook Tests
# ============================================================================


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
    """Test getToolPostInvokeResponse when plugin blocks the response.

    This test verifies that when continue_processing=False, the function
    uses immediate_response (not response_body) and includes violation details.
    """
    # Setup mocks for immediate_response path
    setup_response_mocks(mock_envoy_modules)

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

    # Capture json.dumps calls to verify error body content
    original_dumps = json.dumps
    captured_bodies = []

    def spy_dumps(obj, **kwargs):
        if isinstance(obj, dict) and "error" in obj:
            captured_bodies.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy_dumps
    try:
        # Call the function
        response = await src.server.getToolPostInvokeResponse(
            sample_tool_result_body
        )
    finally:
        json.dumps = original_dumps

    # Verify the hook was called with correct payload
    assert mock_manager.invoke_hook.called
    call_args = mock_manager.invoke_hook.call_args[0]
    payload = call_args[1]
    assert isinstance(payload, ToolPostInvokePayload)
    assert payload.result == sample_tool_result_body["result"]

    # Verify response was created (error path taken)
    assert response is not None

    # Verify error body was created with violation details
    assert len(captured_bodies) > 0
    error_body = captured_bodies[0]
    assert "error" in error_body
    assert error_body["error"]["code"] == -32000
    # Verify violation message is included
    assert "Sensitive content detected" in error_body["error"]["message"]
    assert (
        "Tool response contains forbidden content"
        in error_body["error"]["message"]
    )


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

    # Spy on json.dumps to capture what body is being serialized
    original_dumps = json.dumps
    captured_body = None

    def spy_dumps(obj, **kwargs):
        nonlocal captured_body
        # Capture the body dict that's being serialized
        if isinstance(obj, dict) and "result" in obj and "jsonrpc" in obj:
            captured_body = obj
        return original_dumps(obj, **kwargs)

    json.dumps = spy_dumps
    try:
        # Call the function
        response = await src.server.getToolPostInvokeResponse(
            sample_tool_result_body
        )
    finally:
        json.dumps = original_dumps

    # Verify the hook was called
    assert mock_manager.invoke_hook.called

    # Verify response was created
    assert response is not None

    # Verify the body was modified with the new result
    assert captured_body is not None, (
        "json.dumps should have been called with the modified body"
    )
    assert captured_body["result"] == modified_result
    assert (
        captured_body["result"]["content"][0]["text"] == "Modified tool result"
    )
    # Verify original metadata (jsonrpc, id) is preserved
    assert captured_body["jsonrpc"] == sample_tool_result_body["jsonrpc"]
    assert captured_body["id"] == sample_tool_result_body["id"]


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


# ============================================================================
# Response Body Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_response_body_buffer_with_tool_result(
    mock_envoy_modules, mock_manager
):
    """Test process_response_body_buffer with a tool result."""
    setup_response_mocks(mock_envoy_modules)
    import src.server

    setup_manager_with_result(mock_manager)
    src.server.manager = mock_manager

    tool_result = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {"content": [{"type": "text", "text": "Result"}]},
    }
    buffer = bytearray(json.dumps(tool_result).encode("utf-8"))
    response = await src.server.process_response_body_buffer(buffer)

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    verify_payload_content(payload, tool_result["result"], "Result")
    # Verify ProcessingResponse was returned
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_with_sse_format(
    mock_envoy_modules, mock_manager
):
    """Test process_response_body_buffer with SSE formatted content."""
    setup_response_mocks(mock_envoy_modules)
    import src.server

    setup_manager_with_result(mock_manager)
    src.server.manager = mock_manager

    tool_result = {
        "jsonrpc": "2.0",
        "id": "test-sse",
        "result": {"content": [{"type": "text", "text": "SSE data"}]},
    }
    sse_body = f"event: message\ndata: {json.dumps(tool_result)}\n\n"
    buffer = bytearray(sse_body.encode("utf-8"))
    response = await src.server.process_response_body_buffer(buffer)

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    verify_payload_content(payload, tool_result["result"], "SSE data")
    # Verify ProcessingResponse was returned
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_multiple_chunks_scenario(
    mock_envoy_modules, mock_manager
):
    """Test buffering: content in chunks, then empty end_of_stream chunk.

    Simulates: chunk1 (content) + chunk2 (content) + chunk3 (empty, end_of_stream).
    """
    setup_response_mocks(mock_envoy_modules)
    import src.server

    setup_manager_with_result(mock_manager)
    src.server.manager = mock_manager

    tool_result = {
        "jsonrpc": "2.0",
        "id": "test-multi-chunk",
        "result": {"content": [{"type": "text", "text": "Multi chunk data"}]},
    }
    body_bytes = json.dumps(tool_result).encode("utf-8")

    # Simulate buffering: chunk1 + chunk2 + empty chunk
    buffer = bytearray()
    buffer.extend(body_bytes[:25])  # Chunk 1
    buffer.extend(body_bytes[25:])  # Chunk 2
    buffer.extend(b"")  # Chunk 3 (empty, triggers processing)

    response = await src.server.process_response_body_buffer(buffer)

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    verify_payload_content(payload, tool_result["result"], "Multi chunk data")
    # Verify ProcessingResponse was returned
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_empty(
    mock_envoy_modules, mock_manager
):
    """Test process_response_body_buffer with empty buffer."""
    setup_response_mocks(mock_envoy_modules)
    import src.server

    src.server.manager = mock_manager
    response = await src.server.process_response_body_buffer(bytearray())

    # Verify hook is NOT called for empty buffer
    assert not mock_manager.invoke_hook.called, (
        "Tool post-invoke hook should not be called for empty buffer"
    )
    # Verify response is returned (function doesn't crash on empty buffer)
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_non_tool_result(
    mock_envoy_modules, mock_manager
):
    """Test process_response_body_buffer with non-tool result (error response)."""
    setup_response_mocks(mock_envoy_modules)
    import src.server

    src.server.manager = mock_manager

    error_response = {
        "jsonrpc": "2.0",
        "id": "test-error",
        "error": {"code": -32000, "message": "Error"},
    }
    buffer = bytearray(json.dumps(error_response).encode("utf-8"))
    response = await src.server.process_response_body_buffer(buffer)

    # Verify hook is NOT called for error responses
    assert not mock_manager.invoke_hook.called, (
        "Tool post-invoke hook should not be called for error responses"
    )
    # Verify response is returned (function handles error responses gracefully)
    assert response is not None
