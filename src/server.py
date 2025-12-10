# Standard
import asyncio
import logging
from typing import AsyncIterator
import json
import os
import grpc

from envoy.service.ext_proc.v3 import external_processor_pb2 as ep
from envoy.service.ext_proc.v3 import external_processor_pb2_grpc as ep_grpc
from envoy.config.core.v3 import base_pb2 as core
from envoy.type.v3 import http_status_pb2 as http_status_pb2

# plugin manager
# First-Party
# from apex.mcp.entities.models import HookType, Message, PromptResult, Role, TextContent, PromptPosthookPayload, PromptPrehookPayload
# import apex.mcp.entities.models as apex
# import mcpgateway.plugins.tools.models as apex
from mcpgateway.plugins.framework import (
    ToolHookType,
    PromptPrehookPayload,
    ToolPostInvokePayload,
    ToolPreInvokePayload,
)
from mcpgateway.plugins.framework import PluginManager
from mcpgateway.plugins.framework.models import GlobalContext
# from apex.framework.manager import PluginManager
# from apex.framework.models import GlobalContext
# from plugins.regex_filter.search_replace import SearchReplaceConfig

log_level = os.environ.get("LOGLEVEL", "INFO").upper()

logging.basicConfig(level=log_level)
logger = logging.getLogger("ext-proc-PM")
logger.setLevel(log_level)

# handler = logging.StreamHandler()
# handler.setLevel(log_level)

# # Add the handler to the logger
# logger.addHandler(handler)


async def getToolPostInvokeResponse(body):
    # FIXME: size of content array is expected to be 1
    # for content in body["result"]["content"]:

    logger.debug("**** Tool Post Invoke ****")
    payload = ToolPostInvokePayload(name="replaceme", result=body)
    # TODO: hard-coded ids
    logger.debug("**** Tool Post Invoke result ****")
    logger.deub(payload)
    global_context = GlobalContext(request_id="1", server_id="2")
    result, contexts = await manager.invoke_hook(
        ToolHookType.TOOL_POST_INVOKE, payload, global_context=global_context
    )
    logger.info(result)
    if not result.continue_processing:
        body_resp = ep.ProcessingResponse(
            immediate_response=ep.ImmediateResponse(
                # TODO: hard-coded error reason
                status=http_status_pb2.HttpStatus(code=http_status_pb2.Forbidden),
                details="No go",
            )
        )
    else:
        result_payload = result.modified_payload
        if result_payload is not None:
            body = result_payload.result
        else:
            body = None
        body_resp = ep.ProcessingResponse(
            request_body=ep.BodyResponse(
                response=ep.CommonResponse(
                    body_mutation=ep.BodyMutation(body=json.dumps(body).encode("utf-8"))
                )
            )
        )
    return body_resp


async def getToolPreInvokeResponse(body):
    logger.debug(body)
    payload_args = {
        "tool_name": body["params"]["name"],
        "tool_args": body["params"]["arguments"],
        "session_id": "replaceme",
    }
    payload = ToolPreInvokePayload(name=body["params"]["name"], args=payload_args)
    # TODO: hard-coded ids
    global_context = GlobalContext(request_id="1", server_id="2")
    logger.debug("**** Invoking Tool Pre Invoke with payload ****")
    logger.debug(payload)
    result, contexts = await manager.invoke_hook(
        ToolHookType.TOOL_PRE_INVOKE, payload, global_context=global_context
    )
    logger.debug("**** Tool Pre Invoke Result ****")
    logger.info(result)
    if not result.continue_processing:
        body_resp = ep.ProcessingResponse(
            immediate_response=ep.ImmediateResponse(
                status=http_status_pb2.HttpStatus(code=http_status_pb2.Forbidden),
                details="No go",
            )
        )
    else:
        logger.debug(result)
        print(result)
        result_payload = result.modified_payload
        if result_payload is not None and result_payload.args is not None:
            body["params"]["arguments"] = result_payload.args
        # else:
        #     body["params"]["arguments"] = None

        body_resp = ep.ProcessingResponse(
            request_body=ep.BodyResponse(
                response=ep.CommonResponse(
                    body_mutation=ep.BodyMutation(body=json.dumps(body).encode("utf-8"))
                )
            )
        )
    logger.info("****Tool Pre Invoke Return body****")
    logger.info(body_resp)
    return body_resp


async def getPromptPreFetchResponse(body):
    prompt = PromptPrehookPayload(
        name=body["params"]["name"], args=body["params"]["arguments"]
    )
    # TODO: hard-coded ids
    global_context = GlobalContext(request_id="1", server_id="2")
    result, contexts = await manager.invoke_hook(
        ToolHookType.PROMPT_PRE_FETCH, prompt, global_context=global_context
    )
    logger.info(result)
    if not result.continue_processing:
        body_resp = ep.ProcessingResponse(
            immediate_response=ep.ImmediateResponse(
                status=http_status_pb2.HttpStatus(code=http_status_pb2.Forbidden),
                details="No go",
            )
        )
    else:
        body["params"]["arguments"] = result.modified_payload.args
        body_resp = ep.ProcessingResponse(
            request_body=ep.BodyResponse(
                response=ep.CommonResponse(
                    body_mutation=ep.BodyMutation(body=json.dumps(body).encode("utf-8"))
                )
            )
        )
    logger.info("****body ")
    logger.info(body_resp)
    return body_resp


class ExtProcServicer(ep_grpc.ExternalProcessorServicer):
    async def Process(
        self, request_iterator: AsyncIterator[ep.ProcessingRequest], context
    ) -> AsyncIterator[ep.ProcessingResponse]:
        req_body_buf = bytearray()
        resp_body_buf = bytearray()

        async for request in request_iterator:
            # logger.info(request)
            if request.HasField("request_headers"):
                # Modify request headers
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
            elif request.HasField("response_headers"):
                # Modify response headers
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
                        elif "method" in body and body["method"] == "prompts/get":
                            body_resp = await getPromptPreFetchResponse(body)
                        else:
                            body_resp = ep.ProcessingResponse(
                                request_body=ep.BodyResponse(
                                    response=ep.CommonResponse()
                                )
                            )
                        yield body_resp

                    req_body_buf.clear()

            # ---- Response body chunks ----
            elif request.HasField("response_body") and request.response_body.body:
                chunk = request.response_body.body
                resp_body_buf.extend(chunk)

                if getattr(request.response_body, "end_of_stream", False):
                    try:
                        text = resp_body_buf.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.debug("Response body not UTF-8; skipping")
                    else:
                        logger.info(text.split("\n"))
                        # find data key
                        data = [d for d in text.split("\n") if d.startswith("data:")]
                        # logger.info(json.loads(data[0].strip("data:")))
                        if data:  # List can be empty
                            data = json.loads(data[0].strip("data:"))
                        # TODO: check for tool call
                        if "result" in data:
                            body_resp = await getToolPostInvokeResponse(data)
                        else:
                            body_resp = ep.ProcessingResponse(
                                response_body=ep.BodyResponse(
                                    response=ep.CommonResponse()
                                )
                            )
                        yield body_resp
                    resp_body_buf.clear()

            # Handle other message types (request_body, response_body, etc.) as needed
            else:
                logger.warn("Not processed")


async def serve(host: str = "0.0.0.0", port: int = 50052):
    await manager.initialize()
    logger.info(manager.config)

    server = grpc.aio.server()
    # server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    ep_grpc.add_ExternalProcessorServicer_to_server(ExtProcServicer(), server)
    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)
    logger.info("Starting ext_proc MY server on %s", listen_addr)
    await server.start()
    # wait forever
    await server.wait_for_termination()


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
