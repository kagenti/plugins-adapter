"""Unit tests for getPromptPreFetchResponse.

Tests the prompt pre-fetch path: validation, modification, and blocking.
"""

# Standard
import json
from unittest.mock import Mock

# Third-Party
import pytest

# Local
from conftest import make_hook_result

# First-Party
from cpex.framework import PluginViolation, PromptPrehookPayload


@pytest.fixture
def prompt_body():
    """Sample MCP prompts/get request body."""
    return {
        "jsonrpc": "2.0",
        "id": "test-456",
        "method": "prompts/get",
        "params": {
            "name": "test_prompt",
            "arguments": {"arg0": "some value"},
        },
    }


@pytest.mark.asyncio
async def test_getPromptPreFetchResponse_continue_no_modification(mock_envoy_modules, mock_manager, prompt_body):
    """Plugin allows the prompt fetch with no changes."""
    import src.server

    mock_manager.invoke_hook.return_value = (make_hook_result(), None)
    src.server.manager = mock_manager

    response = await src.server.getPromptPreFetchResponse(prompt_body)

    assert mock_manager.invoke_hook.called
    call_args = mock_manager.invoke_hook.call_args[0]
    payload = call_args[1]
    assert isinstance(payload, PromptPrehookPayload)
    assert payload.prompt_id == "test_prompt"
    assert response is not None


@pytest.mark.asyncio
async def test_getPromptPreFetchResponse_continue_with_modified_args(mock_envoy_modules, mock_manager, prompt_body):
    """Plugin modifies prompt arguments — modified args are forwarded."""
    import src.server

    modified_args = {"arg0": "rewritten value"}
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
        response = await src.server.getPromptPreFetchResponse(prompt_body)
    finally:
        json.dumps = original_dumps

    assert mock_manager.invoke_hook.called
    assert response is not None
    assert len(captured_bodies) > 0
    assert captured_bodies[0]["params"]["arguments"] == modified_args


@pytest.mark.asyncio
async def test_getPromptPreFetchResponse_blocked(mock_envoy_modules, mock_manager, prompt_body):
    """Plugin blocks the prompt fetch — response is an MCP error."""
    import src.server

    violation = PluginViolation(
        reason="Prompt not permitted",
        description="This prompt template is restricted",
        code="PROMPT_BLOCKED",
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
        response = await src.server.getPromptPreFetchResponse(prompt_body)
    finally:
        json.dumps = original_dumps

    assert mock_manager.invoke_hook.called
    assert response is not None
    assert len(captured_bodies) > 0
    error_body = captured_bodies[0]
    assert "error" in error_body
    assert "Prompt not permitted" in error_body["error"]["message"]
    assert error_body["id"] == "test-456"
    assert error_body["jsonrpc"] == "2.0"
