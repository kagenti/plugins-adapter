# -*- coding: utf-8 -*-
"""Tests for registered plugins."""

# Standard
import asyncio

# Third-Party
import pytest
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field

# First-Party
# from mcpgateway.common.models import Message, PromptResult, Role, TextContent
from cpex.framework import (
    GlobalContext,
    PluginManager,
    PromptHookType,
    PromptPosthookPayload,
    PromptPrehookPayload,
    ToolHookType,
    ToolPostInvokePayload,
)


##----- Temporary classes from contextforge-plugins-framework/tests/unit/cpex/fixtures/common/models.py ##
## Available at https://github.com/contextforge-org/contextforge-plugins-framework/blob/5769b1bbced23cdc7448bf001aecdbe6a44f22d5/tests/unit/cpex/fixtures/common/models.py
class Role(str, Enum):
    """Message role in conversations."""

    ASSISTANT = "assistant"
    USER = "user"


# Base content types
class TextContent(BaseModel):
    """Text content for messages (MCP spec-compliant)."""

    type: Literal["text"]
    text: str
    annotations: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")


class ResourceContents(BaseModel):
    """Base class for resource contents (MCP spec-compliant)."""

    uri: str
    mime_type: Optional[str] = Field(None, alias="mimeType")
    meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")


# Legacy ResourceContent for backwards compatibility
class ResourceContent(BaseModel):
    """Resource content that can be embedded (LEGACY - use TextResourceContents or BlobResourceContents)."""

    type: Literal["resource"]
    id: str
    uri: str
    mime_type: Optional[str] = None
    text: Optional[str] = None
    blob: Optional[bytes] = None


ContentType = Union[TextContent, ResourceContent]


# Message types
class Message(BaseModel):
    """A message in a conversation.

    Attributes:
        role (Role): The role of the message sender.
        content (ContentType): The content of the message.
    """

    role: Role
    content: ContentType


class PromptMessage(BaseModel):
    """Message in a prompt (MCP spec-compliant)."""

    role: Role
    content: "ContentBlock"  # Uses ContentBlock union (includes ResourceLink and EmbeddedResource)


class PromptResult(BaseModel):
    """Result of rendering a prompt template.

    Attributes:
        messages (List[Message]): The list of messages produced by rendering the prompt.
        description (Optional[str]): An optional description of the rendered result.
    """

    messages: List[Message]
    description: Optional[str] = None


# MCP spec-compliant ContentBlock union for prompts and tool results
# Per spec: ContentBlock can include ResourceLink and EmbeddedResource
ContentBlock = Union[TextContent]


@pytest.fixture(scope="module", autouse=True)
def plugin_manager():
    """Initialize plugin manager."""
    plugin_manager = PluginManager("./resources/plugins/config.yaml")
    asyncio.run(plugin_manager.initialize())
    yield plugin_manager
    asyncio.run(plugin_manager.shutdown())


@pytest.mark.asyncio
async def test_prompt_pre_hook(plugin_manager: PluginManager):
    """Test prompt pre hook across all registered plugins."""
    # Customize payload for testing
    payload = PromptPrehookPayload(
        prompt_id="test_prompt", args={"arg0": "This is an argument"}
    )
    global_context = GlobalContext(request_id="1")
    result, _ = await plugin_manager.invoke_hook(
        PromptHookType.PROMPT_PRE_FETCH, payload, global_context
    )
    # Assert expected behaviors
    assert result.continue_processing


@pytest.mark.asyncio
async def test_prompt_post_hook(plugin_manager: PluginManager):
    """Test prompt post hook across all registered plugins."""
    # Customize payload for testing
    message = Message(
        content=TextContent(type="text", text="prompt", _meta={}),
        role=Role.USER,
    )
    prompt_result = PromptResult(messages=[message])
    payload = PromptPosthookPayload(
        prompt_id="test_prompt", result=prompt_result
    )
    global_context = GlobalContext(request_id="1")
    result, _ = await plugin_manager.invoke_hook(
        PromptHookType.PROMPT_POST_FETCH, payload, global_context
    )
    # Assert expected behaviors
    assert result.continue_processing


@pytest.mark.asyncio
async def test_tool_post_hook(plugin_manager: PluginManager):
    """Test tool post hook across all registered plugins."""
    # Customize payload for testing
    payload = ToolPostInvokePayload(
        name="test_tool", result={"output0": "output value"}
    )
    global_context = GlobalContext(request_id="1")
    result, _ = await plugin_manager.invoke_hook(
        ToolHookType.TOOL_POST_INVOKE, payload, global_context
    )
    # Assert expected behaviors
    assert result.continue_processing
