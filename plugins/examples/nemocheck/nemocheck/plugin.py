"""Adapter for Nemo-Check guardrails.

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
    PluginViolation,
)


import logging
import os
import requests

headers = {
    "Content-Type": "application/json",
}
# Initialize logging service first
logger = logging.getLogger(__name__)
log_level = os.getenv("LOGLEVEL", "INFO").upper()
logger.setLevel(log_level)

MODEL_NAME = os.getenv(
    "NEMO_MODEL", "meta-llama/llama-3-3-70b-instruct"
)  # Currently only for logging.
CHECK_ENDPOINT = os.getenv(
    "CHECK_ENDPOINT", "http://nemo-guardrails-service:8000"
)


class NemoCheck(Plugin):
    """Adapter for Nemo-Check guardrails."""

    def __init__(self, config: PluginConfig):
        """Entry init block for plugin.

        Args:
          logger: logger that the skill can make use of
          config: the skill configuration
        """
        super().__init__(config)

    async def prompt_pre_fetch(
        self, payload: PromptPrehookPayload, context: PluginContext
    ) -> PromptPrehookResult:
        """The plugin hook run before a prompt is retrieved and rendered.

        Args:
            payload: The prompt payload to be analyzed.
            context: contextual information about the hook call.

        Returns:
            The result of the plugin's analysis, including whether the prompt can proceed.
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
        logger.info("[NemoCheck] Starting tool_pre_invoke")
        logger.info(payload)
        tool_name = payload.name  # ("tool_name", None)
        check_nemo_payload = {
            "model": MODEL_NAME,  # ideally optional
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
        violation = None
        response = requests.post(
            CHECK_ENDPOINT, headers=headers, json=check_nemo_payload
        )
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "blocked")
            logger.debug(f"rails reply:{data}")
            if status == "success":
                metadata = data.get("rails_status")
                result = ToolPreInvokeResult(
                    continue_processing=True, metadata=metadata
                )
            else:
                metadata = data.get("rails_status")
                violation = PluginViolation(
                    reason=f"Tool Check status:{status}",
                    description="Rails check blocked request",
                    code=f"checkserver_http_status_code:{response.status_code}",
                    details=metadata,
                )
                result = ToolPreInvokeResult(
                    continue_processing=False,
                    violation=violation,
                    metadata=metadata,
                )

        else:
            violation = PluginViolation(
                reason="Tool Check Unavailable",
                description="Tool arguments check server returned error:",
                code=f"checkserver_http_status_code:{response.status_code}",
                details={},
            )
            result = ToolPreInvokeResult(
                continue_processing=False, violation=violation
            )
        logger.info(response)

        return result

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
        logger.info(
            f"[NemoCheck] Starting tool post invoke hook with payload {payload}"
        )

        # Extract content from payload.result
        # payload.result format: {'content': [{'type': 'text', 'text': 'Hello, bob!'}]}
        result_content = payload.result.get("content", [])
        tool_name = payload.name

        if not result_content:
            logger.warning(
                "[NemoCheck] No content in tool result, skipping check"
            )
            return ToolPostInvokeResult(continue_processing=True)

        # Extract text content from the content array
        # TODO: what to do if there's actually multiple texts?
        text_content = ""
        for item in result_content:
            if item.get("type") == "text":
                text_content += item.get("text", "")

        # Build NeMo check payload for tool response
        check_nemo_payload = {
            "model": MODEL_NAME,  # ideally optional
            "messages": [
                {"role": "tool", "content": text_content, "name": tool_name}
            ],
        }

        logger.debug(
            f"[NemoCheck] Payload for guardrail check: {check_nemo_payload}"
        )

        violation = None
        try:
            response = requests.post(
                CHECK_ENDPOINT, headers=headers, json=check_nemo_payload
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "blocked")
                logger.debug(f"[NemoCheck] Rails reply: {data}")

                if status == "success":
                    metadata = data.get("rails_status")
                    result = ToolPostInvokeResult(
                        continue_processing=True, metadata=metadata
                    )
                else:  # blocked
                    metadata = data.get("rails_status")
                    violation = PluginViolation(
                        reason=f"Tool response check status: {status}",
                        description="Rails check blocked tool response",
                        code=f"checkserver_http_status_code:{response.status_code}",
                        details=metadata,
                    )
                    result = ToolPostInvokeResult(
                        continue_processing=False,
                        violation=violation,
                        metadata=metadata,
                    )
            else:
                violation = PluginViolation(
                    reason="Tool response check unavailable",
                    description="Tool response check server returned error",
                    code=f"checkserver_http_status_code:{response.status_code}",
                    details={},
                )
                result = ToolPostInvokeResult(
                    continue_processing=False, violation=violation
                )

            logger.info(f"[NemoCheck] Tool post invoke result: {result}")
            return result

        except Exception as e:
            logger.error(f"[NemoCheck] Error checking tool response: {e}")
            return ToolPostInvokeResult(
                continue_processing=True
            )  # Fail open on error
