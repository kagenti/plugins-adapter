"""Unit tests for getToolPreInvokeResponse.

Tests the tool pre-invoke path: argument validation, modification, and blocking.
"""

# Standard
import json
from unittest.mock import Mock

# Third-Party
import pytest

# Local
from conftest import make_hook_result

# First-Party
from cpex.framework import PluginViolation, ToolPreInvokePayload


@pytest.fixture
def tool_call_body():
    """Sample MCP tools/call request body."""
    return {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "tools/call",
        "params": {
            "name": "test_tool",
            "arguments": {"param": "value"},
        },
    }


@pytest.mark.asyncio
async def test_getToolPreInvokeResponse_continue_no_modification(mock_envoy_modules, mock_manager, tool_call_body):
    """Plugin allows the tool call through with no argument changes."""
    import src.server

    mock_manager.invoke_hook.return_value = (make_hook_result(), None)
    src.server.manager = mock_manager

    response = await src.server.getToolPreInvokeResponse(tool_call_body)

    assert mock_manager.invoke_hook.called
    call_args = mock_manager.invoke_hook.call_args[0]
    payload = call_args[1]
    assert isinstance(payload, ToolPreInvokePayload)
    assert payload.name == "test_tool"
    assert response is not None


@pytest.mark.asyncio
async def test_getToolPreInvokeResponse_continue_with_modified_args(mock_envoy_modules, mock_manager, tool_call_body):
    """Plugin modifies tool arguments — modified args are forwarded in the response."""
    import src.server

    modified_args = {"param": "sanitized_value", "injected": False}
    modified_payload = Mock()
    modified_payload.args = {"tool_args": modified_args}

    mock_manager.invoke_hook.return_value = (make_hook_result(modified_payload=modified_payload), None)
    src.server.manager = mock_manager

    captured_bodies = []
    original_dumps = json.dumps

    def spy_dumps(obj, **kwargs):
        if isinstance(obj, dict) and "params" in obj:
            captured_bodies.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy_dumps
    try:
        response = await src.server.getToolPreInvokeResponse(tool_call_body)
    finally:
        json.dumps = original_dumps

    assert mock_manager.invoke_hook.called
    assert response is not None
    assert len(captured_bodies) > 0
    assert captured_bodies[0]["params"]["arguments"] == modified_args


@pytest.mark.asyncio
async def test_getToolPreInvokeResponse_blocked_with_violation(mock_envoy_modules, mock_manager, tool_call_body):
    """Plugin blocks the tool call — response is an MCP error with violation details."""
    import src.server

    violation = PluginViolation(
        reason="Forbidden argument detected",
        description="The tool arguments contain disallowed content",
        code="ARGS_VIOLATION",
    )
    mock_manager.invoke_hook.return_value = (make_hook_result(continue_processing=False, violation=violation), None)
    src.server.manager = mock_manager

    captured_bodies = []
    original_dumps = json.dumps

    def spy_dumps(obj, **kwargs):
        if isinstance(obj, dict) and "error" in obj:
            captured_bodies.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy_dumps
    try:
        response = await src.server.getToolPreInvokeResponse(tool_call_body)
    finally:
        json.dumps = original_dumps

    assert mock_manager.invoke_hook.called
    assert response is not None
    assert len(captured_bodies) > 0
    error_body = captured_bodies[0]
    assert "error" in error_body
    assert "Forbidden argument detected" in error_body["error"]["message"]
    assert "disallowed content" in error_body["error"]["message"]


@pytest.mark.asyncio
async def test_getToolPreInvokeResponse_payload_carries_tool_name(mock_envoy_modules, mock_manager):
    """The ToolPreInvokePayload passed to the hook reflects the tool name from the request."""
    import src.server

    body = {
        "jsonrpc": "2.0",
        "id": "x",
        "method": "tools/call",
        "params": {"name": "my_special_tool", "arguments": {}},
    }
    mock_manager.invoke_hook.return_value = (make_hook_result(), None)
    src.server.manager = mock_manager

    await src.server.getToolPreInvokeResponse(body)

    payload = mock_manager.invoke_hook.call_args[0][1]
    assert payload.name == "my_special_tool"
