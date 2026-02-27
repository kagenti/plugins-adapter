"""Tests for plugin."""

# Standard
from unittest.mock import Mock, patch

# Third-Party
import pytest

# First-Party
from mcpgateway.plugins.framework import (
    PluginConfig,
    PluginContext,
    GlobalContext,
    PromptPrehookPayload,
    ToolPostInvokePayload,
    ToolPreInvokePayload,
)

# Local
from plugin import NemoCheck


@pytest.fixture
def plugin():
    """Create a NemoCheck plugin instance."""
    config = PluginConfig(
        name="test",
        kind="nemocheck.NemoCheck",
        hooks=["prompt_pre_fetch", "tool_pre_invoke", "tool_post_invoke"],
        config={},
    )
    return NemoCheck(config)


@pytest.fixture
def context():
    """Create a PluginContext instance."""
    return PluginContext(global_context=GlobalContext(request_id="1"))


def mock_http_response(status_code, response_data=None):
    """Helper to create mock HTTP responses."""
    mock_response = Mock()
    mock_response.status_code = status_code
    if response_data:
        mock_response.json.return_value = response_data
    return mock_response


@pytest.mark.asyncio
async def test_prompt_pre_fetch(plugin, context):
    """Test plugin prompt prefetch hook."""
    payload = PromptPrehookPayload(
        prompt_id="test_prompt", args={"arg0": "This is an argument"}
    )
    result = await plugin.prompt_pre_fetch(payload, context)
    assert result.continue_processing


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,response_data,expected_continue,has_violation,expected_code,expected_mcp_code",
    [
        (
            200,
            {
                "status": "success",
                "rails_status": {
                    "detect sensitive data": {"status": "success"}
                },
            },
            True,
            False,
            None,
            None,
        ),
        (
            200,
            {
                "status": "blocked",
                "rails_status": {"detect hap": {"status": "blocked"}},
            },
            False,
            True,
            "NEMO_RAILS_BLOCKED",
            -32602,  # Invalid params for tool request
        ),
        (503, None, False, True, "NEMO_SERVER_ERROR", None),
    ],
)
async def test_tool_pre_invoke_scenarios(
    plugin,
    context,
    status_code,
    response_data,
    expected_continue,
    has_violation,
    expected_code,
    expected_mcp_code,
):
    """Test tool_pre_invoke with various scenarios including error codes and MCP error codes."""
    payload = ToolPreInvokePayload(
        name="test_tool",
        args={"tool_args": '{"param": "value"}'},
    )

    with patch(
        "plugin.requests.post",
        return_value=mock_http_response(status_code, response_data),
    ):
        result = await plugin.tool_pre_invoke(payload, context)

    assert result.continue_processing == expected_continue
    assert (result.violation is not None) == has_violation
    if has_violation:
        assert result.violation.code == expected_code
        assert result.violation.mcp_error_code == expected_mcp_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,response_data,expected_continue,has_violation,expected_code,expected_mcp_code",
    [
        (
            200,
            {
                "status": "success",
                "rails_status": {
                    "detect sensitive data": {"status": "success"}
                },
            },
            True,
            False,
            None,
            None,
        ),
        (
            200,
            {
                "status": "blocked",
                "rails_status": {"detect hap": {"status": "blocked"}},
            },
            False,
            True,
            "NEMO_RAILS_BLOCKED",
            -32603,  # Internal error for invalid tool response
        ),
        (500, None, False, True, "NEMO_SERVER_ERROR", None),
    ],
)
async def test_tool_post_invoke_http_scenarios(
    plugin,
    context,
    status_code,
    response_data,
    expected_continue,
    has_violation,
    expected_code,
    expected_mcp_code,
):
    """Test tool_post_invoke with various HTTP response scenarios including error codes and MCP error codes."""
    payload = ToolPostInvokePayload(
        name="test_tool",
        result={"content": [{"type": "text", "text": "Test content"}]},
    )

    with patch(
        "plugin.requests.post",
        return_value=mock_http_response(status_code, response_data),
    ):
        result = await plugin.tool_post_invoke(payload, context)

    assert result.continue_processing == expected_continue
    assert (result.violation is not None) == has_violation
    if has_violation:
        assert result.violation.code == expected_code
        assert result.violation.mcp_error_code == expected_mcp_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result_data,should_continue",
    [
        ({"content": []}, True),  # Empty content
        ({"output": "value"}, True),  # No content key
    ],
)
async def test_tool_post_invoke_passthrough_content_cases(
    plugin, context, result_data, should_continue
):
    """Test tool_post_invoke no/empty content cases that do not flag."""
    payload = ToolPostInvokePayload(name="test_tool", result=result_data)
    result = await plugin.tool_post_invoke(payload, context)
    assert result.continue_processing == should_continue
    assert result.violation is None


@pytest.mark.asyncio
async def test_tool_post_invoke_concatenates_text(plugin, context):
    """Test tool_post_invoke concatenates multiple text items."""
    payload = ToolPostInvokePayload(
        name="test_tool",
        result={
            "content": [
                {"type": "text", "text": "First. "},
                {"type": "text", "text": "Second."},
            ]
        },
    )

    with patch(
        "plugin.requests.post",
        return_value=mock_http_response(
            200, {"status": "success", "rails_status": {}}
        ),
    ) as mock_post:
        result = await plugin.tool_post_invoke(payload, context)

    assert result.continue_processing
    sent_content = mock_post.call_args[1]["json"]["messages"][0]["content"]
    assert sent_content == "First. Second."


@pytest.mark.asyncio
async def test_tool_post_invoke_filters_non_text(plugin, context):
    """Test tool_post_invoke filters non-text content."""
    payload = ToolPostInvokePayload(
        name="test_tool",
        result={
            "content": [
                {"type": "image", "url": "http://example.com/img.png"},
                {"type": "text", "text": "Text only"},
            ]
        },
    )

    with patch(
        "plugin.requests.post",
        return_value=mock_http_response(
            200, {"status": "success", "rails_status": {}}
        ),
    ) as mock_post:
        result = await plugin.tool_post_invoke(payload, context)

    assert result.continue_processing
    sent_content = mock_post.call_args[1]["json"]["messages"][0]["content"]
    assert sent_content == "Text only"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hook_name,payload_factory",
    [
        (
            "tool_pre_invoke",
            lambda: ToolPreInvokePayload(
                name="test_tool", args={"tool_args": '{"param": "value"}'}
            ),
        ),
        (
            "tool_post_invoke",
            lambda: ToolPostInvokePayload(
                name="test_tool",
                result={"content": [{"type": "text", "text": "content"}]},
            ),
        ),
    ],
)
async def test_connection_error_handling(
    plugin, context, hook_name, payload_factory
):
    """Test both hooks fail closed on connection errors with NEMO_CONNECTION_ERROR code."""
    payload = payload_factory()
    hook = getattr(plugin, hook_name)

    with patch("plugin.requests.post", side_effect=Exception("Network error")):
        result = await hook(payload, context)

    assert not result.continue_processing
    assert result.violation is not None
    assert result.violation.code == "NEMO_CONNECTION_ERROR"
    assert "Network error" in result.violation.description


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hook_name,payload_factory,expected_reason_prefix",
    [
        (
            "tool_pre_invoke",
            lambda: ToolPreInvokePayload(
                name="test_tool", args={"tool_args": '{"param": "value"}'}
            ),
            "Tool request check failed",
        ),
        (
            "tool_post_invoke",
            lambda: ToolPostInvokePayload(
                name="test_tool",
                result={"content": [{"type": "text", "text": "content"}]},
            ),
            "Tool response check failed",
        ),
    ],
)
async def test_violation_includes_rail_names(
    plugin, context, hook_name, payload_factory, expected_reason_prefix
):
    """Test that violation descriptions include the rail names from rails_status."""
    payload = payload_factory()
    hook = getattr(plugin, hook_name)

    # Mock response with multiple rails
    response_data = {
        "status": "blocked",
        "rails_status": {
            "detect hap": {"status": "blocked"},
            "detect sensitive data": {"status": "success"},
        },
    }

    with patch(
        "plugin.requests.post",
        return_value=mock_http_response(200, response_data),
    ):
        result = await hook(payload, context)

    assert not result.continue_processing
    assert result.violation is not None
    assert result.violation.code == "NEMO_RAILS_BLOCKED"

    # Verify reason includes the expected prefix
    assert result.violation.reason.startswith(expected_reason_prefix)

    # Verify description includes rail names
    assert "Rails:" in result.violation.description
    assert "detect hap" in result.violation.description
    assert "detect sensitive data" in result.violation.description

    # Verify MCP error code is set appropriately
    if hook_name == "tool_pre_invoke":
        assert result.violation.mcp_error_code == -32602
    else:
        assert result.violation.mcp_error_code == -32603
