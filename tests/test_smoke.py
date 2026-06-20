import asyncio
from types import SimpleNamespace

import httpx
import wavelink

from apps.api.penguin_api.main import create_app
from apps.bot.penguin_bot.bot import create_bot
from apps.bot.penguin_bot.config import Settings
from apps.bot.penguin_bot.music.lavalink import (
    LavalinkConnectionManager,
    _format_status,
    _is_connected_wavelink_node,
    _wait_for_wavelink_node,
)


def test_bot_package_imports_and_registers_ping() -> None:
    settings = Settings.from_environment({"DISCORD_CLIENT_ID": "123", "DISCORD_GUILD_ID": "456"})
    bot = create_bot(settings)

    assert {command.name for command in bot.tree.get_commands()} == {
        "ping",
        "music-status",
        "nowplaying",
        "play",
        "queue",
        "skip",
        "stop",
    }


def test_api_health_endpoint() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_only_reports_safe_configuration_facts() -> None:
    settings = Settings.from_environment(
        {
            "DISCORD_TOKEN": "secret-token",
            "LAVALINK_PASSWORD": "secret-password",
            "AI_API_KEY": "secret-ai-key",
        }
    )

    status = settings.safe_status()
    assert status["discord_token_configured"] is True
    assert status["lavalink_password_configured"] is True
    assert "secret-token" not in str(status)
    assert "secret-password" not in str(status)
    assert "secret-ai-key" not in str(status)


def test_music_status_never_contains_lavalink_password() -> None:
    settings = Settings.from_environment(
        {
            "LAVALINK_HOST": "private-node",
            "LAVALINK_PORT": "2333",
            "LAVALINK_PASSWORD": "secret-lavalink-password",
            "LAVALINK_SECURE": "true",
        }
    )
    manager = LavalinkConnectionManager(settings)

    rendered = _format_status(manager.status())

    assert "secret-lavalink-password" not in rendered
    assert "private-node" in rendered
    assert "secure: yes" in rendered


def test_offline_lavalink_does_not_raise_or_mark_node_reachable() -> None:
    async def unavailable_connector(_: object) -> bool:
        return False

    settings = Settings.from_environment({"LAVALINK_PASSWORD": "secret-lavalink-password"})
    manager = LavalinkConnectionManager(settings, connector=unavailable_connector)

    status = asyncio.run(manager.initialize(object()))

    assert status.reachable is False
    assert status.state == "offline"
    assert "secret-lavalink-password" not in (status.error_summary or "")


def test_bot_ready_keeps_running_when_lavalink_is_offline() -> None:
    async def unavailable_connector(_: object) -> bool:
        return False

    async def initialize_bot() -> None:
        settings = Settings.from_environment({"LAVALINK_PASSWORD": "secret-lavalink-password"})
        bot = create_bot(settings)
        bot.lavalink = LavalinkConnectionManager(settings, connector=unavailable_connector)

        await bot.on_ready()
        await bot._lavalink_task

        assert bot.lavalink.status().state == "offline"
        assert any(command.name == "ping" for command in bot.tree.get_commands())

    asyncio.run(initialize_bot())


def test_lavalink_connection_error_redacts_password() -> None:
    async def failing_connector(_: object) -> bool:
        raise RuntimeError("authorization rejected secret-lavalink-password")

    settings = Settings.from_environment({"LAVALINK_PASSWORD": "secret-lavalink-password"})
    manager = LavalinkConnectionManager(settings, connector=failing_connector)

    status = asyncio.run(manager.initialize(object()))

    assert status.state == "offline"
    assert "secret-lavalink-password" not in (status.error_summary or "")
    assert "secret-lavalink-password" not in _format_status(status)


def test_connecting_wavelink_node_is_not_reported_as_reachable() -> None:
    node = SimpleNamespace(identifier="primary", status=wavelink.NodeStatus.CONNECTING)

    assert _is_connected_wavelink_node({"primary": node}, node) is False

    node.status = wavelink.NodeStatus.CONNECTED
    assert _is_connected_wavelink_node({"primary": node}, node) is True


def test_wavelink_ready_wait_handles_asynchronous_handshake() -> None:
    async def wait_for_ready() -> bool:
        node = SimpleNamespace(identifier="primary", status=wavelink.NodeStatus.CONNECTING)

        async def finish_handshake() -> None:
            await asyncio.sleep(0)
            node.status = wavelink.NodeStatus.CONNECTED

        task = asyncio.create_task(finish_handshake())
        result = await _wait_for_wavelink_node(
            {"primary": node},
            node,
            timeout_seconds=1,
            poll_interval_seconds=0.01,
        )
        await task
        return result

    assert asyncio.run(wait_for_ready()) is True
