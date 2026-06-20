"""Discord application-command registration for Phase 0."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime

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
from .music.status_snapshot import (
    MusicStatusSnapshotWriter,
    build_error,
    build_health,
    build_now_playing,
    build_payload,
    build_queue,
    build_service,
    build_sources,
    build_voice,
    select_primary_guild,
    wrap_snapshot,
)

logger = logging.getLogger(__name__)

EMPTY_VOICE_DISCONNECT_DELAY_SECONDS = 30.0
STATUS_SNAPSHOT_REFRESH_SECONDS = 5.0

_MUSIC_HEADLINES = {
    "playing": "播放中",
    "paused": "已暫停",
    "idle": "閒置",
    "degraded": "異常",
}


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
        self._started_monotonic = time.monotonic()
        self._snapshot_writer = (
            MusicStatusSnapshotWriter(settings.music_status_snapshot_path)
            if settings.music_status_snapshot_path
            else None
        )
        self._snapshot_task: asyncio.Task[None] | None = None
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
        self._start_status_snapshot_loop()
        self.refresh_status_snapshot()

    def _start_status_snapshot_loop(self) -> None:
        if self._snapshot_writer is None or self._snapshot_task is not None:
            return
        self._snapshot_task = asyncio.create_task(
            self._status_snapshot_loop(),
            name="music-status-snapshot",
        )

    async def _status_snapshot_loop(self) -> None:
        """Refresh the snapshot periodically so its freshness is bounded."""

        try:
            while True:
                await asyncio.sleep(STATUS_SNAPSHOT_REFRESH_SECONDS)
                self.refresh_status_snapshot()
        except asyncio.CancelledError:
            raise

    def refresh_status_snapshot(self) -> None:
        """Best-effort rebuild and write of the sanitized status snapshot.

        Never raises: snapshot bookkeeping must not affect playback. Commands and
        event handlers call this after mutating playback state.
        """

        if self._snapshot_writer is None:
            return
        try:
            snapshot = self._build_status_snapshot()
        except Exception:
            logger.warning("Could not build the music status snapshot (non-fatal).", exc_info=True)
            return
        self._snapshot_writer.write(snapshot)

    def _build_status_snapshot(self) -> dict[str, object]:
        settings = self.settings
        coordinator = self.playback
        lavalink_status = self.lavalink.status()

        primary_guild = select_primary_guild(
            settings.discord_guild_id,
            coordinator.current_guild_ids(),
            coordinator.queued_guild_ids(),
        )
        current = coordinator.current(primary_guild) if primary_guild is not None else None
        pending = coordinator.pending(primary_guild) if primary_guild is not None else ()

        player = self._player_for_guild(primary_guild)
        position_ms, paused = self._player_playback_facts(player)
        if current is None:
            now_state = "idle"
        elif paused:
            now_state = "paused"
        else:
            now_state = "playing"

        now_playing = build_now_playing(
            current,
            state=now_state,
            position_ms=position_ms if now_state != "idle" else None,
        )
        voice_state, guild_name, channel_name, listeners = self._voice_facts(player)
        voice = build_voice(
            state=voice_state,
            guild=guild_name,
            channel=channel_name,
            listeners=listeners,
        )

        active_players = len(coordinator.current_guild_ids())
        errors: list[dict[str, str]] = []

        bot_service = build_service(
            "bot",
            "Discord Bot",
            "online",
            "在線",
            f"已連線（{len(self.guilds)} 個伺服器）",
            meta=f"{active_players} 個作用中的 player" if active_players else None,
        )
        if lavalink_status.reachable:
            lavalink_service = build_service(
                "lavalink",
                "Lavalink",
                "online",
                "可連線",
                "私人 v4 node 已就緒",
                meta="youtube-source + lavabili",
            )
        else:
            lavalink_service = build_service(
                "lavalink",
                "Lavalink",
                "offline",
                "離線",
                "Lavalink 目前無法連線",
            )
            errors.append(
                build_error("lavalink", "LAVALINK_UNREACHABLE", "Lavalink is currently unreachable.")
            )

        music_status_value = self._music_status_value(now_state, lavalink_status.reachable)
        music_service = build_service(
            "music",
            "Music",
            music_status_value,
            _MUSIC_HEADLINES.get(music_status_value, "未知"),
            self._music_detail(voice_state, channel_name),
            meta=f"{active_players} 個作用中的 player" if active_players else "閒置",
        )

        services = [bot_service, lavalink_service, music_service]
        health = build_health(
            uptime=self._uptime_text(),
            active_players=active_players,
            lavalink_secure=settings.lavalink_secure,
            region="本機私人部署",
        )
        payload = build_payload(
            services=services,
            voice=voice,
            now_playing=now_playing,
            queue=build_queue(pending),
            sources=build_sources(),
            health=health,
            errors=errors,
        )
        return wrap_snapshot(payload, written_at_iso=datetime.now(UTC).isoformat())

    @staticmethod
    def _music_status_value(now_state: str, lavalink_reachable: bool) -> str:
        if not lavalink_reachable:
            return "degraded"
        if now_state in {"playing", "paused"}:
            return now_state
        return "idle"

    @staticmethod
    def _music_detail(voice_state: str, channel_name: str | None) -> str:
        if voice_state == "connected" and channel_name:
            return f"正在 {channel_name} 串流"
        return "目前沒有播放中的歌曲"

    def _player_for_guild(self, guild_id: int | None) -> wavelink.Player | None:
        if guild_id is None:
            return None
        guild = self.get_guild(guild_id)
        voice_client = guild.voice_client if guild is not None else None
        return voice_client if isinstance(voice_client, wavelink.Player) else None

    @staticmethod
    def _player_playback_facts(player: wavelink.Player | None) -> tuple[int | None, bool]:
        if player is None:
            return None, False
        raw_position = getattr(player, "position", None)
        position_ms = int(raw_position) if isinstance(raw_position, (int, float)) else None
        return position_ms, bool(getattr(player, "paused", False))

    @staticmethod
    def _voice_facts(
        player: wavelink.Player | None,
    ) -> tuple[str, str | None, str | None, int]:
        if player is None:
            return "disconnected", None, None, 0
        guild = getattr(player, "guild", None)
        channel = getattr(player, "channel", None)
        members = getattr(channel, "members", ())
        listeners = sum(1 for member in members if not bool(getattr(member, "bot", False)))
        return (
            "connected",
            getattr(guild, "name", None),
            getattr(channel, "name", None),
            listeners,
        )

    def _uptime_text(self) -> str:
        elapsed = max(0, int(time.monotonic() - self._started_monotonic))
        days, remainder = divmod(elapsed, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        if days:
            return f"{days} 天 {hours} 小時 {minutes} 分"
        if hours:
            return f"{hours} 小時 {minutes} 分"
        return f"{minutes} 分"

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
        self.refresh_status_snapshot()

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
            self.refresh_status_snapshot()
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
        self.refresh_status_snapshot()

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
            self.refresh_status_snapshot()
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
