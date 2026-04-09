"""Tests for graceful shutdown: health check registration and SIGTERM handling."""

# Standard
import asyncio
import signal as signal_mod
from unittest.mock import AsyncMock, MagicMock, patch

# Third-Party
import pytest

# ============================================================================
# HEALTH SERVICE REGISTRATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_serve_registers_health_servicer(mock_envoy_modules, mock_manager):
    """serve() registers the gRPC health check service and marks it SERVING."""
    mock_server = MagicMock()
    mock_server.start = AsyncMock()
    mock_server.wait_for_termination = AsyncMock()
    mock_server.stop = AsyncMock()

    mock_health_servicer = MagicMock()

    with (
        patch("grpc.aio.server", return_value=mock_server),
        patch("src.server.grpc_health.HealthServicer", return_value=mock_health_servicer),
        patch("src.server.health_pb2_grpc.add_HealthServicer_to_server") as mock_add_health,
    ):
        import src.server

        src.server.manager = mock_manager
        mock_manager.initialize = AsyncMock()
        mock_manager.config = {}
        mock_manager.plugin_count = 0

        await src.server.serve()

    mock_add_health.assert_called_once_with(mock_health_servicer, mock_server)
    # Should set SERVING after start
    mock_health_servicer.set.assert_called()
    first_set = mock_health_servicer.set.call_args_list[0]
    assert first_set[0][0] == ""  # empty service name = overall health


# ============================================================================
# SIGTERM GRACEFUL SHUTDOWN TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_serve_sigterm_triggers_graceful_stop(mock_envoy_modules, mock_manager):
    """SIGTERM handler calls server.stop(grace=15) and sets health to NOT_SERVING."""
    mock_server = MagicMock()
    mock_server.start = AsyncMock()
    mock_server.stop = AsyncMock()

    termination_event = asyncio.Event()

    async def fake_wait():
        await termination_event.wait()

    mock_server.wait_for_termination = fake_wait

    mock_health_servicer = MagicMock()
    captured_handlers = {}

    def fake_add_signal_handler(sig, cb):
        captured_handlers[sig] = cb

    with (
        patch("grpc.aio.server", return_value=mock_server),
        patch("src.server.grpc_health.HealthServicer", return_value=mock_health_servicer),
        patch("src.server.health_pb2_grpc.add_HealthServicer_to_server"),
        patch("src.server.health_pb2.HealthCheckResponse") as mock_hcr,
    ):
        import src.server

        src.server.manager = mock_manager
        mock_manager.initialize = AsyncMock()
        mock_manager.shutdown = AsyncMock()
        mock_manager.config = {}
        mock_manager.plugin_count = 0

        loop = asyncio.get_event_loop()
        original_add = loop.add_signal_handler
        loop.add_signal_handler = fake_add_signal_handler

        try:
            serve_task = asyncio.ensure_future(src.server.serve())
            await asyncio.sleep(0)  # let serve() reach wait_for_termination

            assert signal_mod.SIGTERM in captured_handlers
            captured_handlers[signal_mod.SIGTERM]()

            await asyncio.sleep(0.1)  # let _shutdown() coroutine run
            termination_event.set()
            await serve_task
        finally:
            loop.add_signal_handler = original_add

    mock_server.stop.assert_called_once_with(grace=15)
    # Health should have been set to NOT_SERVING during shutdown
    set_calls = mock_health_servicer.set.call_args_list
    assert len(set_calls) >= 2, "Expected SERVING then NOT_SERVING"
    last_set = set_calls[-1]
    assert last_set[0][0] == ""  # empty service name
    assert last_set[0][1] == mock_hcr.NOT_SERVING
