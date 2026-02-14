"""Nemo Check Plugin

Copyright 2025
SPDX-License-Identifier: Apache-2.0
Authors: julianstephen

This module provides the core Nemo Check guardrails plugin implementation.
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
    PluginViolation,
)

import logging
import os
import requests
import json

# Initialize logging
logger = logging.getLogger(__name__)
log_level = os.getenv("LOGLEVEL", "INFO").upper()
logger.setLevel(log_level)

MODEL_NAME = os.getenv(
    "NEMO_MODEL", "meta-llama/llama-3-3-70b-instruct"
)  # Currently only for logging.
DEFAULT_CHECK_ENDPOINT = os.getenv(
    "CHECK_ENDPOINT", "http://nemo-guardrails-service:8000/v1/guardrail/checks"
)
HEADERS = {
    "Content-Type": "application/json",
}


class NemoCheck(Plugin):
    """Nemo Check guardrails plugin."""

    def __init__(self, config: PluginConfig):
        """Initialize the plugin.

        Args:
            config: The plugin configuration
        """
        super().__init__(config)
        # Allow config to override the endpoint
        # Handle case where config.config might be None or empty
        if config.config and isinstance(config.config, dict):
            self.check_endpoint = config.config.get(
                "checkserver_url", DEFAULT_CHECK_ENDPOINT
            )
        else:
            self.check_endpoint = DEFAULT_CHECK_ENDPOINT
            logger.warning(
                "Plugin config is empty or invalid, using default endpoint"
            )
        logger.info(f"Nemo Check endpoint: {self.check_endpoint}")

    async def prompt_pre_fetch(
        self, payload: PromptPrehookPayload, context: PluginContext
    ) -> PromptPrehookResult:
        """The plugin hook run before a prompt is retrieved and rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis.
        """
        return PromptPrehookResult(continue_processing=True)

    async def prompt_post_fetch(
        self, payload: PromptPosthookPayload, context: PluginContext
    ) -> PromptPosthookResult:
        """Plugin hook run after a prompt is rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: Contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
        """
        return PromptPosthookResult(continue_processing=True)

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
                                "arguments": payload.args.get(
                                    "tool_args", None
                                ),
                            },
                        }
                    ],
                }
            ],
        }

        try:
            response = requests.post(
                self.check_endpoint, headers=HEADERS, json=check_nemo_payload
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "blocked")
                logger.debug(f"rails reply: {data}")

                if status == "success":
                    metadata = data.get("rails_status")
                    return ToolPreInvokeResult(
                        continue_processing=True, metadata=metadata
                    )
                else:
                    metadata = data.get("rails_status")
                    violation = PluginViolation(
                        reason=f"Check tool rails:{status}.",
                        description=json.dumps(data),
                        code=f"checkserver_http_status_code:{response.status_code}",
                        details=metadata,
                    )
                    return ToolPreInvokeResult(
                        continue_processing=False,
                        violation=violation,
                        metadata=metadata,
                    )
            else:
                violation = PluginViolation(
                    reason="Tool Check Unavailable",
                    description="Tool arguments check server returned error",
                    code=f"checkserver_http_status_code:{response.status_code}",
                    details={},
                )
                return ToolPreInvokeResult(
                    continue_processing=False, violation=violation
                )

        except Exception as e:
            logger.error(f"Error calling Nemo Check endpoint: {e}")
            violation = PluginViolation(
                reason="Tool Check Error",
                description=f"Failed to connect to check server: {str(e)}",
                code="checkserver_connection_error",
                details={},
            )
            return ToolPreInvokeResult(
                continue_processing=False, violation=violation
            )

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
        return ToolPostInvokeResult(continue_processing=True)
