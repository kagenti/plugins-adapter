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

# Initialize logging
logger = logging.getLogger(__name__)
log_level = os.getenv("LOGLEVEL", "INFO").upper()
logger.setLevel(log_level)

MODEL_NAME = os.getenv(
    "NEMO_MODEL", "meta-llama/llama-3-3-70b-instruct"
)  # Currently only for logging.
DEFAULT_GUARDRAILS_SERVER_URL = os.getenv(
    "GUARDRAILS_SERVER_URL", "http://nemo-guardrails-service:8000"
)
CHECK_PATH = "/v1/guardrail/checks"
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
        # Allow config to override the server URL
        # Handle case where config.config might be None or empty
        if config.config and isinstance(config.config, dict):
            server_url = config.config.get(
                "nemo_guardrails_url", DEFAULT_GUARDRAILS_SERVER_URL
            )
        else:
            server_url = DEFAULT_GUARDRAILS_SERVER_URL
            logger.warning(
                "Plugin config is empty or invalid, using default server URL"
            )

        # Construct full endpoint URL
        self.check_endpoint = server_url.rstrip("/") + CHECK_PATH
        logger.info(
            f"NeMo Guardrails endpoint for check plugin: {self.check_endpoint}"
        )

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
        logger.debug(
            f"[NemoCheck] Starting tool pre invoke hook with payload {payload}"
        )

        tool_name = payload.name
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
                logger.debug(f"[NemoCheck] Rails reply: {data}")
                metadata = data.get("rails_status")

                if status == "success":
                    return ToolPreInvokeResult(
                        continue_processing=True, metadata=metadata
                    )
                else:
                    logger.info(
                        f"[NemoCheck] Tool request blocked. Full NeMo response: {data}"
                    )
                    # Extract rail names from rails_status for more informative description
                    rails_run = list(metadata.keys()) if metadata else []
                    rails_info = (
                        f"Rails: {', '.join(rails_run)}"
                        if rails_run
                        else "No rails info"
                    )
                    violation = PluginViolation(
                        reason=f"Tool request check failed: {status}",
                        description=f"{rails_info}",
                        code="NEMO_RAILS_BLOCKED",
                        details=metadata,
                        mcp_error_code=-32602,  # Invalid params
                    )
                    return ToolPreInvokeResult(
                        continue_processing=False,
                        violation=violation,
                        metadata=metadata,
                    )
            else:
                violation = PluginViolation(
                    reason="Tool Check Unavailable",
                    description=f"Tool request check server returned error. Status code: {response.status_code}, Response: {response.text}",
                    code="NEMO_SERVER_ERROR",
                    details={"status_code": response.status_code},
                )
                return ToolPreInvokeResult(
                    continue_processing=False, violation=violation
                )

        except Exception as e:
            logger.error(f"[NemoCheck] Error checking tool request: {e}")
            violation = PluginViolation(
                reason="Tool Check Error",
                description=f"Failed to connect to check server: {str(e)}",
                code="NEMO_CONNECTION_ERROR",
                details={"error": str(e)},
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
        logger.debug(
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
                self.check_endpoint, headers=HEADERS, json=check_nemo_payload
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "blocked")
                logger.debug(f"[NemoCheck] Rails reply: {data}")
                metadata = data.get("rails_status")

                if status == "success":
                    result = ToolPostInvokeResult(
                        continue_processing=True, metadata=metadata
                    )
                else:  # blocked
                    logger.info(
                        f"[NemoCheck] Tool response blocked. Full NeMo response: {data}"
                    )
                    # Extract rail names from rails_status for more informative description
                    rails_run = list(metadata.keys()) if metadata else []
                    rails_info = (
                        f"Rails: {', '.join(rails_run)}"
                        if rails_run
                        else "No rails info"
                    )
                    violation = PluginViolation(
                        reason=f"Tool response check failed: {status}",
                        description=f"{rails_info}",
                        code="NEMO_RAILS_BLOCKED",
                        details=metadata,
                        mcp_error_code=-32603,  # Internal error for invalid tool response
                    )
                    result = ToolPostInvokeResult(
                        continue_processing=False,
                        violation=violation,
                        metadata=metadata,
                    )
            else:
                violation = PluginViolation(
                    reason="Tool Check Unavailable",
                    description=f"Tool response check server returned error. Status code: {response.status_code}, Response: {response.text}",
                    code="NEMO_SERVER_ERROR",
                    details={"status_code": response.status_code},
                )
                result = ToolPostInvokeResult(
                    continue_processing=False, violation=violation
                )

            logger.info(f"[NemoCheck] Tool post invoke result: {result}")
            return result

        except Exception as e:
            logger.error(f"[NemoCheck] Error checking tool response: {e}")
            violation = PluginViolation(
                reason="Tool Check Error",
                description=f"Failed to connect to check server: {str(e)}",
                code="NEMO_CONNECTION_ERROR",
                details={"error": str(e)},
            )
            return ToolPostInvokeResult(
                continue_processing=False, violation=violation
            )
