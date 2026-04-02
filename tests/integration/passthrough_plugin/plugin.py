"""Passthrough test plugin for integration testing.

A minimal cpex Plugin that either passes through or blocks requests
based on a class-level toggle, allowing tests to control behavior.
"""

import logging

from cpex.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    PluginViolation,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
)

logger = logging.getLogger(__name__)


class PassthroughPlugin(Plugin):
    """Test plugin that can be toggled between passthrough and blocking mode."""

    # Class-level toggles so tests can control behavior
    block_pre_invoke = False
    block_post_invoke = False

    def __init__(self, config: PluginConfig):
        super().__init__(config)

    @classmethod
    def reset(cls):
        """Reset toggles to default passthrough mode."""
        cls.block_pre_invoke = False
        cls.block_post_invoke = False

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        if self.block_pre_invoke:
            violation = PluginViolation(
                reason="Blocked by test",
                description="Pre-invoke blocked for testing",
                code="TEST_BLOCKED",
                mcp_error_code=-32602,
            )
            return ToolPreInvokeResult(continue_processing=False, violation=violation)
        return ToolPreInvokeResult(continue_processing=True)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        if self.block_post_invoke:
            violation = PluginViolation(
                reason="Blocked by test",
                description="Post-invoke blocked for testing",
                code="TEST_BLOCKED",
                mcp_error_code=-32603,
            )
            return ToolPostInvokeResult(continue_processing=False, violation=violation)
        return ToolPostInvokeResult(continue_processing=True)
