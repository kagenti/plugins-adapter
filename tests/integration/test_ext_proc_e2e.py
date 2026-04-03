"""End-to-end integration tests for the ext-proc gRPC server.

These tests start a real gRPC server with a passthrough test plugin
and exercise the full request/response flow.
"""

import json

import pytest
from envoy.config.core.v3 import base_pb2 as core
from envoy.service.ext_proc.v3 import external_processor_pb2 as ep

from tests.integration.passthrough_plugin.plugin import PassthroughPlugin

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper: send a single request over bidi stream and read the first response
# ---------------------------------------------------------------------------


async def send_one(stub, request):
    """Open a bidi stream, write one request, signal done, read one response."""
    call = stub.Process()
    await call.write(request)
    await call.done_writing()
    response = await call.read()
    return response


# ---------------------------------------------------------------------------
# Request Headers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_headers_adds_custom_header(grpc_stub):
    """Sending request_headers should return a header mutation with x-ext-proc-header."""
    request = ep.ProcessingRequest(
        request_headers=ep.HttpHeaders(
            headers=core.HeaderMap(headers=[]),
        )
    )
    response = await send_one(grpc_stub, request)

    assert response.HasField("request_headers")
    mutations = response.request_headers.response.header_mutation.set_headers
    header_keys = [h.header.key for h in mutations]
    assert "x-ext-proc-header" in header_keys


# ---------------------------------------------------------------------------
# Response Headers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_headers_adds_custom_header(grpc_stub):
    """Sending response_headers should return x-ext-proc-response-header."""
    request = ep.ProcessingRequest(
        response_headers=ep.HttpHeaders(
            headers=core.HeaderMap(headers=[]),
        )
    )
    response = await send_one(grpc_stub, request)

    assert response.HasField("response_headers")
    mutations = response.response_headers.response.header_mutation.set_headers
    header_keys = [h.header.key for h in mutations]
    assert "x-ext-proc-response-header" in header_keys


# ---------------------------------------------------------------------------
# Request Body — tools/call passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tools_call_passthrough(grpc_stub):
    """A tools/call request with passthrough plugin should return request_body (not immediate_response)."""
    PassthroughPlugin.reset()

    body = {
        "jsonrpc": "2.0",
        "id": "int-test-1",
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"msg": "hello"}},
    }
    request = ep.ProcessingRequest(
        request_body=ep.HttpBody(
            body=json.dumps(body).encode("utf-8"),
            end_of_stream=True,
        )
    )
    response = await send_one(grpc_stub, request)

    assert response.HasField("request_body"), f"Expected request_body, got: {response}"
    assert not response.HasField("immediate_response")


# ---------------------------------------------------------------------------
# Request Body — tools/call blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tools_call_blocked(grpc_stub):
    """When the plugin blocks, the server returns an immediate_response with an MCP error."""
    PassthroughPlugin.block_pre_invoke = True
    try:
        body = {
            "jsonrpc": "2.0",
            "id": "int-test-2",
            "method": "tools/call",
            "params": {"name": "dangerous_tool", "arguments": {"x": 1}},
        }
        request = ep.ProcessingRequest(
            request_body=ep.HttpBody(
                body=json.dumps(body).encode("utf-8"),
                end_of_stream=True,
            )
        )
        response = await send_one(grpc_stub, request)

        assert response.HasField("immediate_response"), f"Expected immediate_response, got: {response}"
        error_body = json.loads(response.immediate_response.body)
        assert "error" in error_body
        assert error_body["error"]["code"] == -32602
        assert "Blocked by test" in error_body["error"]["message"]
    finally:
        PassthroughPlugin.reset()


# ---------------------------------------------------------------------------
# Request Body — non-tool method passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_tool_request_body_passthrough(grpc_stub):
    """A non-tools/call request body should pass through without plugin invocation."""
    body = {
        "jsonrpc": "2.0",
        "id": "int-test-3",
        "method": "resources/list",
        "params": {},
    }
    request = ep.ProcessingRequest(
        request_body=ep.HttpBody(
            body=json.dumps(body).encode("utf-8"),
            end_of_stream=True,
        )
    )
    response = await send_one(grpc_stub, request)

    assert response.HasField("request_body")
    assert not response.HasField("immediate_response")


# ---------------------------------------------------------------------------
# Response Body — tool result passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_body_tool_result_passthrough(grpc_stub):
    """A tool result in the response body should pass through the post-invoke hook."""
    PassthroughPlugin.reset()

    tool_result = {
        "jsonrpc": "2.0",
        "id": "int-test-4",
        "result": {"content": [{"type": "text", "text": "Tool output data"}]},
    }
    request = ep.ProcessingRequest(
        response_body=ep.HttpBody(
            body=json.dumps(tool_result).encode("utf-8"),
            end_of_stream=True,
        )
    )
    response = await send_one(grpc_stub, request)

    assert response.HasField("response_body")
    assert not response.HasField("immediate_response")


# ---------------------------------------------------------------------------
# Response Body — tool result blocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_body_tool_result_blocked(grpc_stub):
    """When post-invoke blocks, the server returns an immediate_response error."""
    PassthroughPlugin.block_post_invoke = True
    try:
        tool_result = {
            "jsonrpc": "2.0",
            "id": "int-test-5",
            "result": {"content": [{"type": "text", "text": "Sensitive output"}]},
        }
        request = ep.ProcessingRequest(
            response_body=ep.HttpBody(
                body=json.dumps(tool_result).encode("utf-8"),
                end_of_stream=True,
            )
        )
        response = await send_one(grpc_stub, request)

        assert response.HasField("immediate_response"), f"Expected immediate_response, got: {response}"
        error_body = json.loads(response.immediate_response.body)
        assert "error" in error_body
        assert error_body["error"]["code"] == -32603
        assert "Blocked by test" in error_body["error"]["message"]
    finally:
        PassthroughPlugin.reset()
