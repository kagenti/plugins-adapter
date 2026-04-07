"""Unit tests for getToolPostInvokeResponse and process_response_body_buffer.

These tests use dynamic import and mocking to avoid proto dependencies.
Shared fixtures (mock_envoy_modules, mock_manager, sample_tool_result_body)
come from conftest.py.
"""

# Standard
import json
from unittest.mock import MagicMock

# Third-Party
import pytest

# First-Party
from cpex.framework import (
    PluginViolation,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
)


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
async def test_getToolPostInvokeResponse_continue_processing(mock_envoy_modules, mock_manager, sample_tool_result_body):
    """Plugin allows processing to continue — hook is called with correct payload."""
    mock_response = MagicMock()
    mock_response.HasField.return_value = True
    mock_response.response_body.response.HasField.return_value = False
    mock_envoy_modules["ep"].ProcessingResponse.return_value = mock_response

    import src.server

    mock_result = ToolPostInvokeResult(continue_processing=True, modified_payload=None)
    mock_manager.invoke_hook.return_value = (mock_result, None)
    src.server.manager = mock_manager

    _ = await src.server.getToolPostInvokeResponse(sample_tool_result_body)

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    assert isinstance(payload, ToolPostInvokePayload)
    assert payload.result == sample_tool_result_body["result"]


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_blocked(mock_envoy_modules, mock_manager, sample_tool_result_body):
    """Plugin blocks the response — immediate_response is used with violation details."""
    setup_response_mocks(mock_envoy_modules)

    import src.server

    violation = PluginViolation(
        reason="Sensitive content detected",
        description="Tool response contains forbidden content",
        code="CONTENT_VIOLATION",
    )
    mock_result = ToolPostInvokeResult(continue_processing=False, violation=violation)
    mock_manager.invoke_hook.return_value = (mock_result, None)
    src.server.manager = mock_manager

    original_dumps = json.dumps
    captured_bodies = []

    def spy_dumps(obj, **kwargs):
        if isinstance(obj, dict) and "error" in obj:
            captured_bodies.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy_dumps
    try:
        response = await src.server.getToolPostInvokeResponse(sample_tool_result_body)
    finally:
        json.dumps = original_dumps

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    assert isinstance(payload, ToolPostInvokePayload)
    assert payload.result == sample_tool_result_body["result"]
    assert response is not None
    assert len(captured_bodies) > 0
    error_body = captured_bodies[0]
    assert error_body["error"]["code"] == -32000
    assert "Sensitive content detected" in error_body["error"]["message"]
    assert "Tool response contains forbidden content" in error_body["error"]["message"]


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_modified_payload(mock_envoy_modules, mock_manager, sample_tool_result_body):
    """Plugin modifies the payload — modified result is serialised into the response."""
    import src.server

    modified_result = {"content": [{"type": "text", "text": "Modified tool result"}]}
    modified_payload = ToolPostInvokePayload(name="test_tool", result=modified_result)
    mock_result = ToolPostInvokeResult(continue_processing=True, modified_payload=modified_payload)
    mock_manager.invoke_hook.return_value = (mock_result, None)
    src.server.manager = mock_manager

    original_dumps = json.dumps
    captured_body = None

    def spy_dumps(obj, **kwargs):
        nonlocal captured_body
        if isinstance(obj, dict) and "result" in obj and "jsonrpc" in obj:
            captured_body = obj
        return original_dumps(obj, **kwargs)

    json.dumps = spy_dumps
    try:
        response = await src.server.getToolPostInvokeResponse(sample_tool_result_body)
    finally:
        json.dumps = original_dumps

    assert mock_manager.invoke_hook.called
    assert response is not None
    assert captured_body is not None, "json.dumps should have been called with the modified body"
    assert captured_body["result"] == modified_result
    assert captured_body["result"]["content"][0]["text"] == "Modified tool result"
    assert captured_body["jsonrpc"] == sample_tool_result_body["jsonrpc"]
    assert captured_body["id"] == sample_tool_result_body["id"]


@pytest.mark.asyncio
async def test_getToolPostInvokeResponse_multiple_content_items(mock_envoy_modules, mock_manager):
    """Payload passed to hook carries all content items intact."""
    mock_envoy_modules["ep"].ProcessingResponse.return_value = MagicMock()

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
    src.server.manager = mock_manager

    _ = await src.server.getToolPostInvokeResponse(body)

    payload = mock_manager.invoke_hook.call_args[0][1]
    assert len(payload.result["content"]) == 3
    assert payload.result["content"][0]["text"] == "First item"
    assert payload.result["content"][1]["text"] == "Second item"
    assert payload.result["content"][2]["url"] == "http://example.com/img.png"


# ============================================================================
# Response Body Buffer Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_response_body_buffer_with_tool_result(mock_envoy_modules, mock_manager):
    """Plain JSON-RPC tool result triggers the post-invoke hook."""
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
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_with_sse_format(mock_envoy_modules, mock_manager):
    """SSE-wrapped tool result is parsed and triggers the post-invoke hook."""
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
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_with_sse_id_prefix(mock_envoy_modules, mock_manager):
    """SSE stream starting with 'id:' field is detected and parsed correctly."""
    setup_response_mocks(mock_envoy_modules)
    import src.server

    setup_manager_with_result(mock_manager)
    src.server.manager = mock_manager

    tool_result = {
        "jsonrpc": "2.0",
        "id": 10,
        "result": {"content": [{"type": "text", "text": "Echo: my password is secret"}]},
    }
    # SSE streams may begin with 'id:' before 'event:' or 'data:' lines
    sse_body = f"id: sse-event-001\ndata: \n\nevent: message\nid: sse-event-002\ndata: {json.dumps(tool_result)}\n\n"
    buffer = bytearray(sse_body.encode("utf-8"))
    response = await src.server.process_response_body_buffer(buffer)

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    verify_payload_content(payload, tool_result["result"], "Echo: my password is secret")
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_multiple_chunks_scenario(mock_envoy_modules, mock_manager):
    """Multi-chunk buffer is assembled and processed as one unit."""
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

    buffer = bytearray()
    buffer.extend(body_bytes[:25])
    buffer.extend(body_bytes[25:])
    buffer.extend(b"")

    response = await src.server.process_response_body_buffer(buffer)

    assert mock_manager.invoke_hook.called
    payload = mock_manager.invoke_hook.call_args[0][1]
    verify_payload_content(payload, tool_result["result"], "Multi chunk data")
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_empty(mock_envoy_modules, mock_manager):
    """Empty buffer returns a response without invoking the hook."""
    setup_response_mocks(mock_envoy_modules)
    import src.server

    src.server.manager = mock_manager
    response = await src.server.process_response_body_buffer(bytearray())

    assert not mock_manager.invoke_hook.called, "Tool post-invoke hook should not be called for empty buffer"
    assert response is not None


@pytest.mark.asyncio
async def test_process_response_body_buffer_non_tool_result(mock_envoy_modules, mock_manager):
    """Error responses pass through without invoking the hook."""
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

    assert not mock_manager.invoke_hook.called, "Tool post-invoke hook should not be called for error responses"
    assert response is not None
