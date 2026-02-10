"""Nemo Check Adapter.

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: julianstephen

This module loads configurations for plugins.
"""

# First-Party
from mcpgateway.plugins.framework import (
    Plugin,
    PluginConfig,
    PluginContext,
    PromptPosthookPayload,
    PromptPosthookResult,
    PromptPrehookPayload,
    PromptPrehookResult,
    ToolPostInvokePayload,
    ToolPostInvokeResult,
    ToolPreInvokePayload,
    ToolPreInvokeResult,
)

import logging
import os

# Initialize logging service first
logger = logging.getLogger(__name__)
log_level = os.getenv("LOGLEVEL", "INFO").upper()
logger.setLevel(log_level)

MODEL_NAME = os.getenv("NEMO_MODEL", "meta-llama/llama-3-3-70b-instruct")  # Currently only for logging.
CHECK_ENDPOINT = os.getenv("CHECK_ENDPOINT", "http://nemo-guardrails-service:8000")

class NemoCheckv2(Plugin):
    """Nemo Check Adapter."""

    def __init__(self, config: PluginConfig):
        """Entry init block for plugin.

        Args:
          logger: logger that the skill can make use of
          config: the skill configuration
        """
        super().__init__(config)

    async def prompt_pre_fetch(self, payload: PromptPrehookPayload, context: PluginContext) -> PromptPrehookResult:
        """The plugin hook run before a prompt is retrieved and rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
        """
        return PromptPrehookResult(continue_processing=True)

    async def prompt_post_fetch(self, payload: PromptPosthookPayload, context: PluginContext) -> PromptPosthookResult:
        """Plugin hook run after a prompt is rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
        """
        return PromptPosthookResult(continue_processing=True)

    async def tool_pre_invoke(self, payload: ToolPreInvokePayload, context: PluginContext) -> ToolPreInvokeResult:
        """Plugin hook run before a tool is invoked.

        Args:
            payload: The tool payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the tool can proceed.
        """
        logger.info("tool_pre_invoke....")
        logger.info(payload)
        tool_name = payload.name  # ("tool_name", None)
        check_nemo_payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_plug_adap_nem_check_123",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": payload.args.get("tool_args", None),
                            },
                        }
                    ],
                }
            ],
        }
        violation = None
        response = requests.post(CHECK_ENDPOINT, headers=headers, json=check_nemo_payload)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "blocked")
            logger.debug(f"rails reply:{data}")
            if status == "success":
                metadata = data.get("rails_status")
                result = ToolPreInvokeResult(continue_processing=True, metadata=metadata)
            else:
                metadata = data.get("rails_status")
                violation = PluginViolation(
                    reason=f"Tool Check status:{status}", description="Rails check blocked request", code=f"checkserver_http_status_code:{response.status_code}", details=metadata
                )
                result = ToolPreInvokeResult(continue_processing=False, violation=violation, metadata=metadata)

        else:
            violation = PluginViolation(
                reason="Tool Check Unavailable", description="Tool arguments check server returned error:", code=f"checkserver_http_status_code:{response.status_code}", details={}
            )
            result = ToolPreInvokeResult(continue_processing=False, violation=violation)
        logger.info(response)
        
        return ToolPreInvokeResult(continue_processing=True)

    async def tool_post_invoke(self, payload: ToolPostInvokePayload, context: PluginContext) -> ToolPostInvokeResult:
        """Plugin hook run after a tool is invoked.

        Args:
            payload: The tool result payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the tool result should proceed.
        """
        return ToolPostInvokeResult(continue_processing=True)
