"""Safe, non-fatal Lavalink connection management for Phase 1A."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import discord
import wavelink
from discord import app_commands

from ..config import Settings

logger = logging.getLogger(__name__)

ConnectionAttempt = Callable[[discord.Client], Awaitable[bool]]


@dataclass(frozen=True)
class LavalinkStatus:
    """Public Lavalink facts that are safe to log and show to Discord users."""

    configured: bool
    reachable: bool
    host: str
    port: int
    secure: bool
    state: str
    error_summary: str | None


class LavalinkConnectionManager:
    """Attempt a Wavelink connection without allowing failures to stop the bot."""

    def __init__(
        self,
        settings: Settings,
        *,
        connector: ConnectionAttempt | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._settings = settings
        self._connector = connector or self._connect_wavelink
        self._timeout_seconds = timeout_seconds
        self._state = "not_configured" if settings.lavalink_password is None else "not_connected"
        self._reachable = False
        self._error_summary: str | None = None

    def status(self) -> LavalinkStatus:
        return LavalinkStatus(
            configured=self._settings.lavalink_password is not None,
            reachable=self._reachable,
            host=self._settings.lavalink_host,
            port=self._settings.lavalink_port,
            secure=self._settings.lavalink_secure,
            state=self._state,
            error_summary=self._error_summary,
        )

    async def initialize(self, client: discord.Client) -> LavalinkStatus:
        """Make one bounded connection attempt and always return a safe status."""

        if self._settings.lavalink_password is None:
            self._state = "not_configured"
            self._error_summary = "LAVALINK_PASSWORD is not configured."
            logger.warning("Lavalink is not configured; music features remain unavailable.")
            return self.status()

        self._state = "connecting"
        self._error_summary = None

        try:
            connected = await asyncio.wait_for(
                self._connector(client),
                timeout=self._timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:  # The bot must remain available when Lavalink is offline.
            self._state = "offline"
            self._error_summary = self._safe_error_summary(error)
            logger.warning("Lavalink connection unavailable: %s", self._error_summary)
            return self.status()

        if connected:
            self._state = "connected"
            self._reachable = True
            logger.info(
                "Connected to the configured Lavalink node at %s:%s.",
                self._settings.lavalink_host,
                self._settings.lavalink_port,
            )
        else:
            self._state = "offline"
            self._error_summary = "Lavalink node did not establish a connection."
            logger.warning("Lavalink node did not establish a connection.")

        return self.status()

    async def _connect_wavelink(self, client: discord.Client) -> bool:
        scheme = "https" if self._settings.lavalink_secure else "http"
        node = wavelink.Node(
            identifier="primary",
            uri=f"{scheme}://{self._settings.lavalink_host}:{self._settings.lavalink_port}",
            password=self._settings.lavalink_password or "",
            retries=0,
        )
        connected_nodes = await wavelink.Pool.connect(nodes=[node], client=client)
        return await _wait_for_wavelink_node(connected_nodes, node)

    def _safe_error_summary(self, error: Exception) -> str:
        message = str(error).strip() or error.__class__.__name__
        password = self._settings.lavalink_password
        if password:
            message = message.replace(password, "[redacted]")
        return f"{error.__class__.__name__}: {message[:160]}"


def _is_connected_wavelink_node(
    connected_nodes: dict[str, wavelink.Node], node: wavelink.Node
) -> bool:
    """Return true only after Wavelink has completed the node WebSocket handshake."""

    return (
        connected_nodes.get(node.identifier) is node
        and node.status is wavelink.NodeStatus.CONNECTED
    )


async def _wait_for_wavelink_node(
    connected_nodes: dict[str, wavelink.Node],
    node: wavelink.Node,
    *,
    timeout_seconds: float = 4.0,
    poll_interval_seconds: float = 0.1,
) -> bool:
    """Wait briefly for Lavalink's asynchronous ``ready`` WebSocket event.

    Wavelink adds a node to its pool as the WebSocket is being established; the
    node only becomes usable after Lavalink sends its ``ready`` event. This
    bounded wait runs inside ``initialize``'s non-fatal timeout.
    """

    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while True:
        if _is_connected_wavelink_node(connected_nodes, node):
            return True
        remaining = deadline - loop.time()
        if remaining <= 0:
            return False
        await asyncio.sleep(min(poll_interval_seconds, remaining))


def _format_status(status: LavalinkStatus) -> str:
    """Render status data without ever consulting the password-bearing settings field."""

    lines = [
        "Lavalink status",
        f"configured: {'yes' if status.configured else 'no'}",
        f"reachable: {'yes' if status.reachable else 'no'}",
        f"host: {status.host}",
        f"port: {status.port}",
        f"secure: {'yes' if status.secure else 'no'}",
        f"state: {status.state}",
        f"error summary: {status.error_summary or 'none'}",
    ]
    return "\n".join(lines)


@app_commands.command(name="music-status", description="Show safe Lavalink connection status.")
async def music_status(interaction: discord.Interaction) -> None:
    manager: Any = getattr(interaction.client, "lavalink", None)
    if not isinstance(manager, LavalinkConnectionManager):
        await interaction.response.send_message("Music status is unavailable.", ephemeral=True)
        return

    await interaction.response.send_message(f"```text\n{_format_status(manager.status())}\n```", ephemeral=True)
