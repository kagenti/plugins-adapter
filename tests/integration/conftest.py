"""Fixtures for integration tests — starts a real gRPC ext-proc server.

Uses module-scoped state so the server starts once per test module on the
first test's event loop, then reuses for subsequent tests.
"""

import os
import pathlib

import grpc
import pytest_asyncio
from cpex.framework import PluginManager
from envoy.service.ext_proc.v3 import external_processor_pb2_grpc as ep_grpc

INTEGRATION_DIR = pathlib.Path(__file__).parent
CONFIG_PATH = str(INTEGRATION_DIR / "config.yaml")


@pytest_asyncio.fixture
async def grpc_stub():
    """Start a gRPC server and yield a connected stub, then tear down."""
    import src.server as server_module

    os.environ["PLUGIN_MANAGER_CONFIG"] = CONFIG_PATH
    manager = PluginManager(CONFIG_PATH)
    await manager.initialize()
    server_module.manager = manager

    server = grpc.aio.server()
    ep_grpc.add_ExternalProcessorServicer_to_server(server_module.ExtProcServicer(), server)
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    channel = grpc.aio.insecure_channel(f"127.0.0.1:{port}")
    stub = ep_grpc.ExternalProcessorStub(channel)

    yield stub

    await channel.close()
    await server.stop(grace=1)
    await manager.shutdown()
