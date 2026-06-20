"""Discord application-command registration for Phase 0."""

from __future__ import annotations

import asyncio
import logging

import discord
import wavelink
from discord import app_commands
from discord.ext import commands

from .config import Settings
from .music import (
    LavalinkConnectionManager,
    PlaybackCoordinator,
    music_status,
    nowplaying,
    pause,
    play,
    queue,
    resume,
    skip,
    stop,
)

logger = logging.getLogger(__name__)

EMPTY_VOICE_DISCONNECT_DELAY_SECONDS = 30.0


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
        self._idle_disconnect_tasks: dict[int, asyncio.Task[None]] = {}
        self.tree.add_command(ping)
        self.tree.add_command(music_status)
        self.tree.add_command(play)
        self.tree.add_command(queue)
        self.tree.add_command(skip)
        self.tree.add_command(stop)
        self.tree.add_command(nowplaying)
        self.tree.add_command(pause)
        self.tree.add_command(resume)

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
        track_uri = getattr(getattr(payload, "track", None), "uri", None)
        started = await self.playback.advance_if_current(guild_id, player, track_uri=track_uri)
        if started is None:
            logger.info("Queue completed for guild %s.", guild_id)

    async def on_wavelink_track_exception(self, payload: object) -> None:
        """Safely recover from a Lavalink track exception without stopping the bot."""

        await self._recover_from_playback_failure(payload, "Lavalink playback exception")

    async def on_wavelink_track_stuck(self, payload: object) -> None:
        """Safely recover when Lavalink reports a stuck track."""

        await self._recover_from_playback_failure(payload, "Lavalink reported a stuck track")

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Clear stale state after disconnection and leave a truly empty channel."""

        guild = member.guild
        guild_id = guild.id
        if self.user is not None and member.id == self.user.id and before.channel is not None and after.channel is None:
            self._cancel_idle_disconnect(guild_id)
            self.playback.stop(guild_id)
            logger.info("Cleared playback state after the bot left voice in guild %s.", guild_id)
            return

        player = guild.voice_client
        if not isinstance(player, wavelink.Player):
            return

        channel = player.channel
        if channel not in (before.channel, after.channel):
            return
        if self._channel_has_only_bots(channel):
            self._schedule_idle_disconnect(guild_id, player)
        else:
            self._cancel_idle_disconnect(guild_id)

    async def _recover_from_playback_failure(self, payload: object, reason: str) -> None:
        player = getattr(payload, "player", None)
        guild = getattr(player, "guild", None)
        guild_id = getattr(guild, "id", None)
        if not isinstance(guild_id, int) or player is None:
            logger.warning("Ignoring %s without a guild player.", reason)
            return

        track_uri = getattr(getattr(payload, "track", None), "uri", None)
        logger.warning("%s in guild %s; attempting the next queued track.", reason, guild_id)
        started = await self.playback.advance_if_current(guild_id, player, track_uri=track_uri)
        if started is None:
            logger.info("No queued track remained after playback failure in guild %s.", guild_id)

    def _schedule_idle_disconnect(self, guild_id: int, player: wavelink.Player) -> None:
        existing = self._idle_disconnect_tasks.get(guild_id)
        if existing is not None and not existing.done():
            return
        self._idle_disconnect_tasks[guild_id] = asyncio.create_task(
            self._disconnect_if_still_empty(guild_id, player),
            name=f"idle-voice-disconnect-{guild_id}",
        )

    def _cancel_idle_disconnect(self, guild_id: int) -> None:
        task = self._idle_disconnect_tasks.pop(guild_id, None)
        if task is not None and not task.done():
            task.cancel()

    async def _disconnect_if_still_empty(self, guild_id: int, player: wavelink.Player) -> None:
        try:
            await asyncio.sleep(EMPTY_VOICE_DISCONNECT_DELAY_SECONDS)
            guild = player.guild
            if guild is None or guild.voice_client is not player or not self._channel_has_only_bots(player.channel):
                return
            self.playback.stop(guild_id)
            await player.disconnect()
            logger.info("Left an empty voice channel and cleared playback state for guild %s.", guild_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Could not leave an empty voice channel for guild %s.", guild_id)
        finally:
            current = self._idle_disconnect_tasks.get(guild_id)
            if current is asyncio.current_task():
                self._idle_disconnect_tasks.pop(guild_id, None)

    @staticmethod
    def _channel_has_only_bots(channel: object | None) -> bool:
        members = getattr(channel, "members", ())
        return bool(members) and all(bool(getattr(member, "bot", False)) for member in members)


def create_bot(settings: Settings) -> PenguinBot:
    """Create a bot without opening a Discord connection; useful for smoke tests."""

    return PenguinBot(settings)
