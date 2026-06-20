"""Phase 1C Discord slash commands for the smallest useful playback MVP."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import discord
import wavelink
from discord import app_commands

from .playback import PlaybackCoordinator
from .presentation import build_queue_embed, build_track_embed
from .queue import TrackRequest

logger = logging.getLogger(__name__)


def _make_request(query: str, requester_id: int, track: wavelink.Playable) -> TrackRequest:
    length = getattr(track, "length", None)
    return TrackRequest(
        query=query,
        requester_id=requester_id,
        title=getattr(track, "title", None),
        author=getattr(track, "author", None),
        uri=getattr(track, "uri", None),
        duration_ms=length if isinstance(length, int) else None,
    )


async def _resolve_track(query: str) -> wavelink.Playable | None:
    """Resolve exactly one playable track; playlists are deliberately out of scope."""

    results = await wavelink.Playable.search(_normalise_youtube_video_url(query))
    if not results or isinstance(results, wavelink.Playlist):
        return None
    return results[0]


def _normalise_youtube_video_url(query: str) -> str:
    """Keep a direct YouTube video request from accidentally loading a mix.

    Users commonly share URLs that include ``list=RD...`` or tracking parameters.
    Phase 1C intentionally does not support playlists, so preserve only a direct
    video ID when the URL contains one and leave all other queries unchanged.
    """

    parsed = urlparse(query.strip())
    host = parsed.netloc.lower().removeprefix("www.")
    video_id: str | None = None
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0] or None
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        video_id = parse_qs(parsed.query).get("v", [None])[0]

    return f"https://www.youtube.com/watch?v={video_id}" if video_id else query.strip()


def _coordinator(interaction: discord.Interaction) -> PlaybackCoordinator | None:
    coordinator = getattr(interaction.client, "playback", None)
    return coordinator if isinstance(coordinator, PlaybackCoordinator) else None


def _guild_id(interaction: discord.Interaction) -> int | None:
    return interaction.guild.id if interaction.guild is not None else None


def _voice_channel(interaction: discord.Interaction) -> discord.abc.Connectable | None:
    voice = getattr(interaction.user, "voice", None)
    return getattr(voice, "channel", None)


async def _get_or_connect_player(
    interaction: discord.Interaction,
) -> tuple[wavelink.Player | None, str | None]:
    guild = interaction.guild
    channel = _voice_channel(interaction)
    if guild is None:
        return None, "音樂指令只能在伺服器中使用。"
    if channel is None:
        return None, "請先加入語音頻道。"

    existing = guild.voice_client
    if existing is not None:
        if not isinstance(existing, wavelink.Player):
            return None, "Bot 正以不支援的語音連線執行中，請先使用 /stop。"
        if existing.channel != channel:
            return None, "請先加入 Bot 所在的語音頻道。"
        return existing, None

    try:
        player = await channel.connect(cls=wavelink.Player)
    except (discord.ClientException, asyncio.TimeoutError) as error:
        logger.info("Could not join a voice channel: %s", error)
        return None, "我無法加入這個語音頻道。"
    return cast(wavelink.Player, player), None


def _lavalink_is_reachable(interaction: discord.Interaction) -> bool:
    manager: Any = getattr(interaction.client, "lavalink", None)
    status = getattr(manager, "status", None)
    return bool(callable(status) and status().reachable)


def _existing_player(interaction: discord.Interaction) -> wavelink.Player | None:
    guild = interaction.guild
    voice_client = guild.voice_client if guild is not None else None
    return voice_client if isinstance(voice_client, wavelink.Player) else None


def _can_control_playback(
    member: object,
    request: TrackRequest,
    bot_channel: object | None,
) -> bool:
    """Apply the Phase 1F in-memory control policy without a database lookup."""

    permissions = getattr(member, "guild_permissions", None)
    if bool(getattr(permissions, "administrator", False)) or bool(getattr(permissions, "manage_guild", False)):
        return True
    if getattr(member, "id", None) == request.requester_id:
        return True
    member_channel = getattr(getattr(member, "voice", None), "channel", None)
    return bot_channel is not None and member_channel == bot_channel


async def _send_queue(interaction: discord.Interaction, coordinator: PlaybackCoordinator, guild_id: int) -> None:
    current = coordinator.current(guild_id)
    pending = coordinator.pending(guild_id)
    await interaction.response.send_message(embed=build_queue_embed(current, pending))


@app_commands.command(name="play", description="搜尋歌曲或網址並加入這個伺服器的播放佇列。")
@app_commands.describe(query="歌曲名稱、歌手或支援的歌曲網址")
async def play(interaction: discord.Interaction, query: str) -> None:
    """Resolve one track, join the caller, and start FIFO playback when idle."""

    guild_id = _guild_id(interaction)
    coordinator = _coordinator(interaction)
    if guild_id is None or coordinator is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return
    if not _lavalink_is_reachable(interaction):
        await interaction.response.send_message(
            "Lavalink 尚未連線，暫時無法播放。請使用 /music-status 查看狀態。",
            ephemeral=True,
        )
        return
    if not query.strip():
        await interaction.response.send_message("請提供歌曲搜尋關鍵字或網址。", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    player, error = await _get_or_connect_player(interaction)
    if error is not None or player is None:
        await interaction.followup.send(error or "無法準備音樂播放器。", ephemeral=True)
        return

    try:
        track = await _resolve_track(query)
    except Exception:
        logger.exception("Track search failed.")
        await interaction.followup.send("歌曲搜尋失敗，請稍後再試。", ephemeral=True)
        return
    if track is None:
        await interaction.followup.send("找不到可播放的單曲；目前不支援播放清單。", ephemeral=True)
        return

    request = _make_request(query, interaction.user.id, track)
    position = coordinator.enqueue(guild_id, request, track)
    started = await coordinator.start_if_idle(guild_id, player)
    if started is request:
        await interaction.followup.send(embed=build_track_embed(request, heading="🎵 正在播放"))
    else:
        await interaction.followup.send(
            embed=build_track_embed(
                request,
                heading="➕ 已加入佇列",
                queue_position=position + 1,
            )
        )


@app_commands.command(name="queue", description="顯示目前播放歌曲與下一首佇列。")
async def queue(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return
    await _send_queue(interaction, coordinator, guild_id)


@app_commands.command(name="nowplaying", description="顯示這個伺服器目前播放的歌曲。")
async def nowplaying(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return
    current = coordinator.current(guild_id)
    if current is None:
        await interaction.response.send_message("目前沒有播放中的歌曲。", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_track_embed(current, heading="🎵 正在播放"))


@app_commands.command(name="pause", description="暫停這個伺服器目前播放的歌曲。")
async def pause(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return
    if coordinator.current(guild_id) is None:
        await interaction.response.send_message("目前沒有播放中的歌曲。", ephemeral=True)
        return
    if _existing_player(interaction) is None:
        await interaction.response.send_message("Bot 目前不在語音頻道。", ephemeral=True)
        return

    player, error = await _get_or_connect_player(interaction)
    if error is not None or player is None:
        await interaction.response.send_message(error or "找不到音樂播放器。", ephemeral=True)
        return
    if player.paused:
        await interaction.response.send_message("目前歌曲已經暫停。", ephemeral=True)
        return
    try:
        await player.pause(True)
    except Exception:
        logger.exception("Could not pause the current track.")
        await interaction.response.send_message("無法暫停目前歌曲。", ephemeral=True)
        return
    await interaction.response.send_message("⏸️ 已暫停播放。")


@app_commands.command(name="resume", description="恢復這個伺服器目前暫停的歌曲。")
async def resume(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return
    if coordinator.current(guild_id) is None:
        await interaction.response.send_message("目前沒有可恢復的歌曲。", ephemeral=True)
        return
    if _existing_player(interaction) is None:
        await interaction.response.send_message("Bot 目前不在語音頻道。", ephemeral=True)
        return

    player, error = await _get_or_connect_player(interaction)
    if error is not None or player is None:
        await interaction.response.send_message(error or "找不到音樂播放器。", ephemeral=True)
        return
    if not player.paused:
        await interaction.response.send_message("目前歌曲沒有暫停。", ephemeral=True)
        return
    try:
        await player.pause(False)
    except Exception:
        logger.exception("Could not resume the current track.")
        await interaction.response.send_message("無法恢復目前歌曲。", ephemeral=True)
        return
    await interaction.response.send_message("▶️ 已恢復播放。")


@app_commands.command(name="skip", description="跳過這個伺服器目前播放的歌曲。")
async def skip(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return
    if coordinator.current(guild_id) is None:
        await interaction.response.send_message("目前沒有播放中的歌曲。", ephemeral=True)
        return

    player_before_permission_check = _existing_player(interaction)
    if player_before_permission_check is not None and not _can_control_playback(
        interaction.user,
        coordinator.current(guild_id),
        player_before_permission_check.channel,
    ):
        await interaction.response.send_message("你沒有跳過目前歌曲的權限。", ephemeral=True)
        return

    player, error = await _get_or_connect_player(interaction)
    if error is not None or player is None:
        await interaction.response.send_message(error or "找不到音樂播放器。", ephemeral=True)
        return
    try:
        await player.skip(force=True)
    except Exception:
        logger.exception("Could not skip the current track.")
        await interaction.response.send_message("無法跳過目前歌曲。", ephemeral=True)
        return
    await interaction.response.send_message("⏭️ 已跳過目前歌曲。")


@app_commands.command(name="stop", description="停止播放、清空佇列並離開語音頻道。")
async def stop(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("此處無法使用音樂播放功能。", ephemeral=True)
        return

    current = coordinator.current(guild_id)
    pending = coordinator.pending(guild_id)
    if current is None and not pending:
        await interaction.response.send_message("目前沒有進行中的播放或佇列。", ephemeral=True)
        return

    control_request = current or pending[0]
    player = _existing_player(interaction)
    if player is not None and not _can_control_playback(interaction.user, control_request, player.channel):
        await interaction.response.send_message("你沒有停止播放的權限。", ephemeral=True)
        return

    current, pending = coordinator.stop(guild_id)
    voice_client = interaction.guild.voice_client if interaction.guild is not None else None
    if isinstance(voice_client, wavelink.Player):
        try:
            await voice_client.skip(force=True)
            await voice_client.disconnect()
        except Exception:
            logger.exception("Could not fully stop or disconnect the music player.")

    await interaction.response.send_message("⏹️ 已停止播放、清空佇列並離開語音頻道。")
