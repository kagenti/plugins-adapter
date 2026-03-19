"""Unit tests for server helper functions.

Covers: set_result_in_body, get_modified_response,
        create_mcp_immediate_error_response
"""

# Standard
import json

# First-Party
from cpex.framework import PluginViolation


def test_set_result_in_body(mock_envoy_modules):
    """set_result_in_body mutates body['params']['arguments'] in place."""
    import src.server

    body = {"params": {"arguments": {"old_key": "old_value"}}}
    new_args = {"new_key": "new_value", "count": 42}

    src.server.set_result_in_body(body, new_args)

    assert body["params"]["arguments"] == new_args


def test_set_result_in_body_overwrites_existing(mock_envoy_modules):
    """set_result_in_body replaces all previous arguments."""
    import src.server

    body = {"params": {"arguments": {"a": 1, "b": 2, "c": 3}}}
    src.server.set_result_in_body(body, {"x": 99})

    assert body["params"]["arguments"] == {"x": 99}
    assert "a" not in body["params"]["arguments"]


def test_get_modified_response_returns_body_response(mock_envoy_modules):
    """get_modified_response encodes the body dict as JSON in a BodyResponse."""
    import src.server

    body = {
        "jsonrpc": "2.0",
        "id": "1",
        "result": {"content": [{"type": "text", "text": "hello"}]},
    }

    captured = []
    original_dumps = json.dumps

    def spy(obj, **kwargs):
        if isinstance(obj, dict) and "result" in obj:
            captured.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy
    try:
        response = src.server.get_modified_response(body)
    finally:
        json.dumps = original_dumps

    assert response is not None
    assert len(captured) == 1
    assert captured[0] == body
    assert captured[0]["result"]["content"][0]["text"] == "hello"


def test_create_mcp_immediate_error_response_default_code(mock_envoy_modules):
    """No violation → error code defaults to -32000 (generic server error)."""
    import src.server

    body = {"jsonrpc": "2.0", "id": "test-001"}

    captured = []
    original_dumps = json.dumps

    def spy(obj, **kwargs):
        if isinstance(obj, dict) and "error" in obj:
            captured.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy
    try:
        response = src.server.create_mcp_immediate_error_response(body, "Something went wrong")
    finally:
        json.dumps = original_dumps

    assert response is not None
    assert len(captured) == 1
    err = captured[0]
    assert err["error"]["code"] == -32000
    assert err["error"]["message"] == "Something went wrong"
    assert err["jsonrpc"] == "2.0"
    assert err["id"] == "test-001"


def test_create_mcp_immediate_error_response_with_violation_reason(mock_envoy_modules):
    """Violation reason/description override the fallback message."""
    import src.server

    body = {"jsonrpc": "2.0", "id": "test-002"}
    violation = PluginViolation(
        reason="Content policy violated",
        description="Detected restricted content in response",
        code="POLICY_VIOLATION",
    )

    captured = []
    original_dumps = json.dumps

    def spy(obj, **kwargs):
        if isinstance(obj, dict) and "error" in obj:
            captured.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy
    try:
        response = src.server.create_mcp_immediate_error_response(body, "fallback msg", violation=violation)
    finally:
        json.dumps = original_dumps

    assert response is not None
    assert len(captured) == 1
    err = captured[0]
    assert "Content policy violated" in err["error"]["message"]
    assert "Detected restricted content" in err["error"]["message"]
    # mcp_error_code not set → still uses default -32000
    assert err["error"]["code"] == -32000


def test_create_mcp_immediate_error_response_with_mcp_error_code(mock_envoy_modules):
    """Violation mcp_error_code overrides the default -32000 code."""
    import src.server

    body = {"jsonrpc": "2.0", "id": "test-003"}
    violation = PluginViolation(
        reason="Invalid params",
        description="Tool args failed validation",
        code="INVALID_ARGS",
        mcp_error_code=-32602,
    )

    captured = []
    original_dumps = json.dumps

    def spy(obj, **kwargs):
        if isinstance(obj, dict) and "error" in obj:
            captured.append(obj)
        return original_dumps(obj, **kwargs)

    json.dumps = spy
    try:
        response = src.server.create_mcp_immediate_error_response(body, "fallback", violation=violation)
    finally:
        json.dumps = original_dumps

    assert response is not None
    err = captured[0]
    assert err["error"]["code"] == -32602
