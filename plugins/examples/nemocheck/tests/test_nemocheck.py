"""Tests for plugin."""

# Third-Party
import pytest

# First-Party
from nemocheck.plugin import NemoCheck
from mcpgateway.plugins.framework import (
    PluginConfig,
    GlobalContext,
    PromptPrehookPayload,
)


@pytest.mark.asyncio
async def test_nemocheck():
    """Test plugin prompt prefetch hook."""
    config = PluginConfig(
        name="test",
        kind="nemocheck.NemoCheck",
        hooks=["prompt_pre_fetch"],
        config={"setting_one": "test_value"},
    )

    plugin = NemoCheck(config)

    # Test your plugin logic
    payload = PromptPrehookPayload(prompt_id="test_prompt", args={"arg0": "This is an argument"})
    context = GlobalContext(request_id="1")
    result = await plugin.prompt_pre_fetch(payload, context)
    assert result.continue_processing
