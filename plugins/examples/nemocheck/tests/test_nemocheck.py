"""Tests for plugin."""

# Standard
from unittest.mock import Mock, patch

# Third-Party
import pytest

# First-Party
from nemocheck.plugin import NemoCheck
from mcpgateway.plugins.framework import (
    PluginConfig,
    GlobalContext,
    PromptPrehookPayload,
    ToolPostInvokePayload,
    ToolPreInvokePayload,
)


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
    """Create a GlobalContext instance."""
    return GlobalContext(request_id="1")


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
    "status_code,response_data,expected_continue,has_violation",
    [
        (200, {"status": "success", "rails_status": {"detect senstitive data": {"status": "success"}}}, True, False),
        (200, {"status": "blocked", "rails_status": {"detect hap": {"status": "blocked"}}}, False, True),
        (503, None, False, True),
    ],
)
async def test_tool_pre_invoke_scenarios(
    plugin, context, status_code, response_data, expected_continue, has_violation
):
    """Test tool_pre_invoke with various scenarios."""
    payload = ToolPreInvokePayload(
        name="test_tool",
        args={"tool_args": '{"param": "value"}'},
    )

    with patch(
        "nemocheck.plugin.requests.post",
        return_value=mock_http_response(status_code, response_data),
    ):
        result = await plugin.tool_pre_invoke(payload, context)

    assert result.continue_processing == expected_continue
    assert (result.violation is not None) == has_violation


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,response_data,expected_continue,has_violation",
    [
        (200, {"status": "success", "rails_status": {"detect senstitive data": {"status": "success"}}}, True, False),
        (200, {"status": "blocked", "rails_status": {"detect hap": {"status": "blocked"}}}, False, True),
        (500, None, False, True),
    ],
)
async def test_tool_post_invoke_http_scenarios(
    plugin, context, status_code, response_data, expected_continue, has_violation
):
    """Test tool_post_invoke with various HTTP response scenarios."""
    payload = ToolPostInvokePayload(
        name="test_tool",
        result={"content": [{"type": "text", "text": "Test content"}]},
    )

    with patch(
        "nemocheck.plugin.requests.post",
        return_value=mock_http_response(status_code, response_data),
    ):
        result = await plugin.tool_post_invoke(payload, context)

    assert result.continue_processing == expected_continue
    assert (result.violation is not None) == has_violation


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result_data,should_continue",
    [
        ({"content": []}, True),  # Empty content
        ({"output": "value"}, True),  # No content key
    ],
)
async def test_tool_post_invoke_passthrough_content_cases(plugin, context, result_data, should_continue):
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
        "nemocheck.plugin.requests.post",
        return_value=mock_http_response(200, {"status": "success", "rails_status": {}}),
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
        "nemocheck.plugin.requests.post",
        return_value=mock_http_response(200, {"status": "success", "rails_status": {}}),
    ) as mock_post:
        result = await plugin.tool_post_invoke(payload, context)

    assert result.continue_processing
    sent_content = mock_post.call_args[1]["json"]["messages"][0]["content"]
    assert sent_content == "Text only"


@pytest.mark.asyncio
async def test_tool_post_invoke_fails_open_on_exception(plugin, context):
    """Test tool_post_invoke fails open on exceptions."""
    payload = ToolPostInvokePayload(
        name="test_tool",
        result={"content": [{"type": "text", "text": "content"}]},
    )

    with patch("nemocheck.plugin.requests.post", side_effect=Exception("Network error")):
        result = await plugin.tool_post_invoke(payload, context)

    assert result.continue_processing
    assert result.violation is None

