"""Discord application-command registration for Phase 0."""

from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from .config import Settings
from .music import (
    LavalinkConnectionManager,
    PlaybackCoordinator,
    music_status,
    nowplaying,
    play,
    queue,
    skip,
    stop,
)

logger = logging.getLogger(__name__)


@app_commands.command(name="ping", description="Check whether DiscordPenguinBot is responding.")
async def ping(interaction: discord.Interaction) -> None:
    """Respond to the Phase 0 health-check command."""

    await interaction.response.send_message("Pong! 🐧", ephemeral=True)


class PenguinBot(commands.Bot):
    """Discord bot with a minimal, syncable slash-command tree."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.settings = settings
        self.lavalink = LavalinkConnectionManager(settings)
        self.playback = PlaybackCoordinator()
        self._lavalink_task: asyncio.Task[object] | None = None
        self.tree.add_command(ping)
        self.tree.add_command(music_status)
        self.tree.add_command(play)
        self.tree.add_command(queue)
        self.tree.add_command(skip)
        self.tree.add_command(stop)
        self.tree.add_command(nowplaying)

    async def setup_hook(self) -> None:
        if self.settings.discord_guild_id is None:
            synced = await self.tree.sync()
            logger.info("Synced %s global application commands.", len(synced))
            return

        guild = discord.Object(id=self.settings.discord_guild_id)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info("Synced %s application commands to development guild %s.", len(synced), guild.id)

    async def on_ready(self) -> None:
        """Start the non-fatal Lavalink connection attempt after Discord is ready."""

        if self._lavalink_task is None:
            self._lavalink_task = asyncio.create_task(
                self.lavalink.initialize(self),
                name="lavalink-initialization",
            )

    async def on_wavelink_track_end(self, payload: object) -> None:
        """Continue FIFO playback after Wavelink reports a track has ended."""

        player = getattr(payload, "player", None)
        guild = getattr(player, "guild", None)
        guild_id = getattr(guild, "id", None)
        if not isinstance(guild_id, int) or player is None:
            logger.warning("Ignoring a Wavelink track-end event without a guild player.")
            return
        started = await self.playback.advance(guild_id, player)
        if started is None:
            logger.info("Queue completed for guild %s.", guild_id)


def create_bot(settings: Settings) -> PenguinBot:
    """Create a bot without opening a Discord connection; useful for smoke tests."""

    return PenguinBot(settings)
