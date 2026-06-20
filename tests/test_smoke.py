import asyncio

import httpx

from apps.api.penguin_api.main import create_app
from apps.bot.penguin_bot.bot import create_bot
from apps.bot.penguin_bot.config import Settings


def test_bot_package_imports_and_registers_ping() -> None:
    settings = Settings.from_environment({"DISCORD_CLIENT_ID": "123", "DISCORD_GUILD_ID": "456"})
    bot = create_bot(settings)

    assert any(command.name == "ping" for command in bot.tree.get_commands())


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
