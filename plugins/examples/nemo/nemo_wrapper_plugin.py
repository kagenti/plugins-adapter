import asyncio
import logging
import os

from mcpgateway.plugins.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    ToolHookType,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
)
from nemoguardrails import LLMRails, RailsConfig

logger = logging.getLogger(__name__)

# NOTE: Ideally a plugin writer does not need to know what (MCP) primitive that the plugin has to run on
# This uses the Context Forge plugin interface to inform how much effort it would be to adapt
# nemo guardrails functionality and leverage this as a plugin server to be leveraged by the ext-proc
# plugin adapter - currently as an internal plugin. The log levels are also particularly high for development currently


class NemoWrapperPlugin(Plugin):
    def __init__(self, config: PluginConfig) -> None:
        """Initialize the plugin.

        Args:
            config: Plugin configuration
        """
        super().__init__(config)
        logger.info(
            f"[NemoWrapperPlugin] Initializing plugin with config: {config.config}"
        )
        # NOTE: very hardcoded
        nemo_config = RailsConfig.from_path(
            os.path.join(
                os.getcwd(), "plugins", "examples", "nemo", "pii_detect_config"
            )
        )
        self._rails = LLMRails(nemo_config)
        logger.info("[NemoWrapperPlugin] Plugin initialized successfully")

    async def tool_pre_invoke(
        self, payload: ToolPreInvokePayload, context: PluginContext
    ) -> ToolPreInvokeResult:
        """Plugin hook run before a tool is invoked.

        Args:
            payload: The tool payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the tool can proceed.
        """
        # Very simple PII detection - attempt to block if any PII and does not alter the payload itself
        rails_response = None
        payload_args = payload.args
        if payload_args:
            try:
                rails_response = await self._rails.generate_async(
                    messages=[{"role": "user", "content": payload_args}]
                )
            except (
                asyncio.CancelledError
            ):  # asyncio.exceptions.CancelledError is thrown by nemo, need to catch
                logging.exception("An error occurred in the nemo plugin except block:")
            finally:
                logger.warning("[NemoWrapperPlugin] Async rails executed")
                logger.warning(rails_response)
        if rails_response and "PII detected" in rails_response["content"]:
            logger.warning("[NemoWrapperPlugin] PII detected, stopping processing")
            return ToolPreInvokeResult(
                modified_payload=payload, continue_processing=False
            )
        logger.warning("[NemoWrapperPlugin] No PII detected, continuing")
        return ToolPreInvokeResult(modified_payload=payload, continue_processing=True)

    async def tool_post_invoke(
        self, payload: ToolPostInvokePayload, context: PluginContext
    ) -> ToolPostInvokeResult:
        """Plugin hook run after a tool is invoked.

        Args:
            payload: The tool result payload to be analyzed.
            context: Contextual information about the hook call.
        Returns:
            The result of the plugin's analysis, including whether the tool result should proceed.
        """
        return ToolPostInvokeResult(modified_payload=payload)

    def get_supported_hooks(self) -> list[str]:
        """Return list of supported hook types."""
        return [
            ToolHookType.TOOL_PRE_INVOKE,
            ToolHookType.TOOL_POST_INVOKE,
        ]
