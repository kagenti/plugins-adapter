# Standard
import asyncio
import logging
from typing import AsyncIterator
import json
import os
import grpc

# Third-Party
from envoy.service.ext_proc.v3 import external_processor_pb2 as ep
from envoy.service.ext_proc.v3 import external_processor_pb2_grpc as ep_grpc
from envoy.config.core.v3 import base_pb2 as core
from envoy.type.v3 import http_status_pb2 as http_status_pb2

# First-Party
from mcpgateway.plugins.framework import (
    ToolHookType,
    PromptPrehookPayload,
    ToolPostInvokePayload,
    ToolPreInvokePayload,
)
from mcpgateway.plugins.framework import PluginManager
from mcpgateway.plugins.framework.models import GlobalContext

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

log_level = os.environ.get("LOGLEVEL", "INFO").upper()

logging.basicConfig(level=log_level)
logger = logging.getLogger("ext-proc-PM")
logger.setLevel(log_level)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def set_result_in_body(body, result_args):
    """Set the result arguments in the request body."""
    body["params"]["arguments"] = result_args


# ============================================================================
# MCP HOOK HANDLERS
# ============================================================================


async def getToolPreInvokeResponse(body):
    """
    Handle tool pre-invoke hook processing.

    Invokes plugins before a tool is called, allowing for argument validation,
    modification, or blocking of the tool invocation.
    """
    logger.debug(body)
    payload_args = {
        "tool_name": body["params"]["name"],
        "tool_args": body["params"]["arguments"],
        "client_session_id": "replaceme",
    }
    payload = ToolPreInvokePayload(
        name=body["params"]["name"], args=payload_args
    )
    # TODO: hard-coded ids
    global_context = GlobalContext(request_id="1", server_id="2")
    logger.debug(f"**** Invoking Tool Pre Invoke with payload: {payload} ****")
    result, _ = await manager.invoke_hook(
        ToolHookType.TOOL_PRE_INVOKE, payload, global_context=global_context
    )
    logger.debug(f"**** Tool Pre Invoke Result: {result} ****")
    if not result.continue_processing:
        error_body = {
            "jsonrpc": body["jsonrpc"],
            "id": body["id"],
            "error": {"code": -32000, "message": "No go - Tool args forbidden"},
        }
        body_resp = ep.ProcessingResponse(
            immediate_response=ep.ImmediateResponse(
                # ok for stream, with error in body
                status=http_status_pb2.HttpStatus(code=200),
                headers=ep.HeaderMutation(
                    set_headers=[
                        core.HeaderValueOption(
                            header=core.HeaderValue(
                                key="content-type",
                                raw_value="application/json".encode("utf-8"),
                            )
                        ),
                        core.HeaderValueOption(
                            header=core.HeaderValue(
                                key="x-mcp-denied",
                                raw_value="True".encode("utf-8"),
                            )
                        ),
                    ],
                ),
                body=(json.dumps(error_body)).encode("utf-8"),
            )
        )
    else:
        logger.debug("continue_processing true")
        result_payload = result.modified_payload
        if result_payload is not None and result_payload.args is not None:
            body["params"]["arguments"] = result_payload.args["tool_args"]
            body_mutation = ep.BodyResponse(
                response=ep.CommonResponse(
                    body_mutation=ep.BodyMutation(
                        body=json.dumps(body).encode("utf-8")
                    )
                )
            )
        else:
            logger.debug("No change in tool args")
            body_mutation = ep.BodyResponse(response=ep.CommonResponse())
        body_resp = ep.ProcessingResponse(request_body=body_mutation)
    logger.info(f"****Tool Pre Invoke Return body: {body_resp}****")
    return body_resp


async def getToolPostInvokeResponse(body):
    """
    Handle tool post-invoke hook processing.

    Invokes plugins after a tool has been called, allowing for result validation,
    modification, or filtering of the tool output.
    """
    # FIXME: size of content array is expected to be 1
    # for content in body["result"]["content"]:

    logger.debug("**** Tool Post Invoke ****")
    payload = ToolPostInvokePayload(name="replaceme", result=body["result"])
    # TODO: hard-coded ids
    logger.debug(f"**** Tool Post Invoke payload: {payload} ****")
    global_context = GlobalContext(request_id="1", server_id="2")
    result, _ = await manager.invoke_hook(
        ToolHookType.TOOL_POST_INVOKE, payload, global_context=global_context
    )
    logger.info(result)
    if not result.continue_processing:
        error_body = {
            "jsonrpc": body["jsonrpc"],
            "id": body["id"],
            "error": {"code": -32000, "message": "No go - Tool args forbidden"},
        }
        body_resp = ep.ProcessingResponse(
            immediate_response=ep.ImmediateResponse(
                # ok for stream, with error in body
                status=http_status_pb2.HttpStatus(code=200),
                headers=ep.HeaderMutation(
                    set_headers=[
                        core.HeaderValueOption(
                            header=core.HeaderValue(
                                key="content-type",
                                raw_value="application/json".encode("utf-8"),
                            )
                        ),
                        core.HeaderValueOption(
                            header=core.HeaderValue(
                                key="x-mcp-denied",
                                raw_value="True".encode("utf-8"),
                            )
                        ),
                    ],
                ),
                body=(json.dumps(error_body)).encode("utf-8"),
            )
        )
    else:
        result_payload = result.modified_payload
        if result_payload is not None:
            body["result"] = result_payload.result
            body_mutation = ep.BodyResponse(
                response=ep.CommonResponse(
                    body_mutation=ep.BodyMutation(
                        body=json.dumps(body).encode("utf-8")
                    )
                )
            )
        else:
            body_mutation = ep.BodyResponse(response=ep.CommonResponse())
        body_resp = ep.ProcessingResponse(request_body=body_mutation)
    return body_resp


async def getPromptPreFetchResponse(body):
    """
    Handle prompt pre-fetch hook processing.

    Invokes plugins before a prompt is fetched, allowing for argument validation,
    modification, or blocking of the prompt request.
    """
    prompt = PromptPrehookPayload(
        name=body["params"]["name"], args=body["params"]["arguments"]
    )
    # TODO: hard-coded ids
    global_context = GlobalContext(request_id="1", server_id="2")
    result, _ = await manager.invoke_hook(
        ToolHookType.PROMPT_PRE_FETCH, prompt, global_context=global_context
    )
    logger.info(result)
    if not result.continue_processing:
        body_resp = ep.ProcessingResponse(
            immediate_response=ep.ImmediateResponse(
                status=http_status_pb2.HttpStatus(
                    code=http_status_pb2.Forbidden
                ),
                details="No go",
            )
        )
    else:
        body["params"]["arguments"] = result.modified_payload.args
        body_resp = ep.ProcessingResponse(
            request_body=ep.BodyResponse(
                response=ep.CommonResponse(
                    body_mutation=ep.BodyMutation(
                        body=json.dumps(body).encode("utf-8")
                    )
                )
            )
        )
    logger.info(f"****Prompt Pre-fetch Return body: {body_resp}")
    return body_resp


# ============================================================================
# ENVOY EXTERNAL PROCESSOR SERVICER
# ============================================================================


class ExtProcServicer(ep_grpc.ExternalProcessorServicer):
    """
    Envoy External Processor implementation for MCP Gateway.

    Processes HTTP requests and responses, intercepting MCP protocol messages
    to apply plugin hooks at various stages of the request/response lifecycle.
    """

    async def Process(
        self, request_iterator: AsyncIterator[ep.ProcessingRequest], context
    ) -> AsyncIterator[ep.ProcessingResponse]:
        """
        Main processing loop for handling Envoy external processor requests.

        Processes different types of requests:
        - Request headers: Add custom headers to incoming requests
        - Response headers: Add custom headers to outgoing responses
        - Request body: Process MCP tool/prompt invocations
        - Response body: Process MCP tool results
        """
        req_body_buf = bytearray()
        resp_body_buf = bytearray()

        async for request in request_iterator:
            # ----------------------------------------------------------------
            # Request Headers Processing
            # ----------------------------------------------------------------
            if request.HasField("request_headers"):
                _headers = request.request_headers.headers
                yield ep.ProcessingResponse(
                    request_headers=ep.HeadersResponse(
                        response=ep.CommonResponse(
                            header_mutation=ep.HeaderMutation(
                                set_headers=[
                                    core.HeaderValueOption(
                                        header=core.HeaderValue(
                                            key="x-ext-proc-header",
                                            raw_value="hello-from-ext-proc".encode(
                                                "utf-8"
                                            ),
                                        ),
                                        append_action=core.HeaderValueOption.APPEND_IF_EXISTS_OR_ADD,
                                    )
                                ]
                            )
                        )
                    )
                )
            # ----------------------------------------------------------------
            # Response Headers Processing
            # ----------------------------------------------------------------
            elif request.HasField("response_headers"):
                _headers = request.response_headers.headers
                yield ep.ProcessingResponse(
                    response_headers=ep.HeadersResponse(
                        response=ep.CommonResponse(
                            header_mutation=ep.HeaderMutation(
                                set_headers=[
                                    core.HeaderValueOption(
                                        header=core.HeaderValue(
                                            key="x-ext-proc-response-header",
                                            raw_value="processed-by-ext-proc".encode(
                                                "utf-8"
                                            ),
                                        ),
                                        append_action=core.HeaderValueOption.APPEND_IF_EXISTS_OR_ADD,
                                    )
                                ]
                            )
                        )
                    )
                )

            # ----------------------------------------------------------------
            # Request Body Processing (MCP Tool/Prompt Invocations)
            # ----------------------------------------------------------------
            elif request.HasField("request_body") and request.request_body.body:
                chunk = request.request_body.body
                req_body_buf.extend(chunk)

                if getattr(request.request_body, "end_of_stream", False):
                    try:
                        text = req_body_buf.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.debug("Request body not UTF-8; skipping")
                    else:
                        logger.info(json.loads(text))
                        body = json.loads(text)
                        if "method" in body and body["method"] == "tools/call":
                            body_resp = await getToolPreInvokeResponse(body)
                        elif (
                            "method" in body and body["method"] == "prompts/get"
                        ):
                            body_resp = await getPromptPreFetchResponse(body)
                        else:
                            body_resp = ep.ProcessingResponse(
                                request_body=ep.BodyResponse(
                                    response=ep.CommonResponse()
                                )
                            )
                        yield body_resp

                    req_body_buf.clear()

            # ----------------------------------------------------------------
            # Response Body Processing (MCP Tool Results)
            # ----------------------------------------------------------------
            elif (
                request.HasField("response_body") and request.response_body.body
            ):
                logger.info(f"!!!In Process for response body: {request}")
                chunk = request.response_body.body
                resp_body_buf.extend(chunk)

                if getattr(request.response_body, "end_of_stream", False):
                    try:
                        text = resp_body_buf.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.debug("Response body not UTF-8; skipping")
                    else:
                        logger.info(f"!!!Text before split: {text.split('\n')}")

                        # Handle both SSE format and plain JSON-RPC format
                        data = None

                        # Check if this is SSE format (starts with "event:" or "data:")
                        if text.strip().startswith(("event:", "data:")):
                            # Parse SSE format
                            lines = text.split("\n")
                            for line in lines:
                                line = line.strip()
                                if line.startswith("data:"):
                                    json_str = line[5:].strip()  # Remove "data:" prefix
                                    try:
                                        data = json.loads(json_str)
                                        break
                                    except json.JSONDecodeError:
                                        continue
                        else:
                            # Parse plain JSON-RPC format
                            lines = [
                                line.strip()
                                for line in text.split("\n")
                                if line.strip()
                            ]
                            if lines:
                                try:
                                    data = json.loads(lines[0])
                                except json.JSONDecodeError as e:
                                    logger.error(f"Failed to parse JSON: {e}")

                        if data:
                            logger.info(f"!!!Parsed response: {data}")

                            # Check if this is a tool result response
                            if (
                                "result" in data
                                and "content" in data["result"]
                            ):
                                body_resp = await getToolPostInvokeResponse(data)
                            else:
                                body_resp = ep.ProcessingResponse(
                                    response_body=ep.BodyResponse(
                                        response=ep.CommonResponse()
                                    )
                                )
                        else:
                            body_resp = ep.ProcessingResponse(
                                response_body=ep.BodyResponse(
                                    response=ep.CommonResponse()
                                )
                            )
                        yield body_resp
                    resp_body_buf.clear()
            # ----------------------------------------------------------------
            # Response Body Processing (No body field)
            # ----------------------------------------------------------------
            elif request.HasField("response_body"):
                logger.warning("On Response, no body.")
                logger.warning(request)
                body_resp = ep.ProcessingResponse(
                    response_body=ep.BodyResponse(response=ep.CommonResponse())
                )
                yield body_resp

            else:
                # Unhandled request types
                logger.warning("Not processed")
                logger.warning(request)


# ============================================================================
# SERVER INITIALIZATION
# ============================================================================


async def serve(host: str = "0.0.0.0", port: int = 50052):
    """
    Initialize and start the gRPC external processor server.

    Args:
        host: Host address to bind to (default: 0.0.0.0)
        port: Port number to listen on (default: 50052)
    """
    await manager.initialize()
    logger.info(f"Manager config: {manager.config}")
    logger.debug(f"Loaded {manager.plugin_count} plugins")

    server = grpc.aio.server()
    # server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ep_grpc.add_ExternalProcessorServicer_to_server(ExtProcServicer(), server)
    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)
    logger.info("Starting ext_proc MY server on %s", listen_addr)
    await server.start()
    # wait forever
    await server.wait_for_termination()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        logging.getLogger("mcpgateway.config").setLevel(logging.DEBUG)
        logging.getLogger("mcpgateway.observability").setLevel(logging.DEBUG)
        logger.info("Manager main")
        pm_config = os.environ.get(
            "PLUGIN_MANAGER_CONFIG", "./resources/config/config.yaml"
        )
        manager = PluginManager(pm_config)
        asyncio.run(serve())
        # serve()
    except KeyboardInterrupt:
        logger.info("Shutting down")
