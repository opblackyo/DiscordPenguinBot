"""Phase 1C Discord slash commands for the smallest useful playback MVP."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

import discord
import wavelink
from discord import app_commands

from .playback import PlaybackCoordinator
from .queue import TrackRequest

logger = logging.getLogger(__name__)


def _track_label(request: TrackRequest) -> str:
    title = request.title or request.query
    return f"{title} — {request.author}" if request.author else title


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

    results = await wavelink.Playable.search(query)
    if not results or isinstance(results, wavelink.Playlist):
        return None
    return results[0]


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
        return None, "Music commands can only be used in a server."
    if channel is None:
        return None, "Join a voice channel first."

    existing = guild.voice_client
    if existing is not None:
        if not isinstance(existing, wavelink.Player):
            return None, "The bot is connected with an unsupported voice client. Use /stop first."
        if existing.channel != channel:
            return None, "Join the bot's voice channel before changing playback."
        return existing, None

    try:
        player = await channel.connect(cls=wavelink.Player)
    except (discord.ClientException, asyncio.TimeoutError) as error:
        logger.info("Could not join a voice channel: %s", error)
        return None, "I could not join that voice channel."
    return cast(wavelink.Player, player), None


def _lavalink_is_reachable(interaction: discord.Interaction) -> bool:
    manager: Any = getattr(interaction.client, "lavalink", None)
    status = getattr(manager, "status", None)
    return bool(callable(status) and status().reachable)


async def _send_queue(interaction: discord.Interaction, coordinator: PlaybackCoordinator, guild_id: int) -> None:
    current = coordinator.current(guild_id)
    pending = coordinator.pending(guild_id)
    lines = [f"Now playing: {_track_label(current) if current else 'nothing'}"]
    if pending:
        lines.append("Up next:")
        lines.extend(f"{index}. {_track_label(request)}" for index, request in enumerate(pending[:10], start=1))
        if len(pending) > 10:
            lines.append(f"…and {len(pending) - 10} more.")
    else:
        lines.append("Up next: nothing")
    await interaction.response.send_message("\n".join(lines))


@app_commands.command(name="play", description="Search for one track and add it to this server's music queue.")
@app_commands.describe(query="A song title, artist, or supported track URL")
async def play(interaction: discord.Interaction, query: str) -> None:
    """Resolve one track, join the caller, and start FIFO playback when idle."""

    guild_id = _guild_id(interaction)
    coordinator = _coordinator(interaction)
    if guild_id is None or coordinator is None:
        await interaction.response.send_message("Music playback is unavailable here.", ephemeral=True)
        return
    if not _lavalink_is_reachable(interaction):
        await interaction.response.send_message(
            "Lavalink is not connected yet, so playback is unavailable. Try /music-status.",
            ephemeral=True,
        )
        return
    if not query.strip():
        await interaction.response.send_message("Provide a track search query.", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    player, error = await _get_or_connect_player(interaction)
    if error is not None or player is None:
        await interaction.followup.send(error or "Unable to prepare a music player.", ephemeral=True)
        return

    try:
        track = await _resolve_track(query)
    except Exception:
        logger.exception("Track search failed.")
        await interaction.followup.send("Track search failed. Please try again.", ephemeral=True)
        return
    if track is None:
        await interaction.followup.send("No individual playable track was found for that query.", ephemeral=True)
        return

    request = _make_request(query, interaction.user.id, track)
    position = coordinator.enqueue(guild_id, request, track)
    started = await coordinator.start_if_idle(guild_id, player)
    if started is request:
        await interaction.followup.send(f"Now playing: {_track_label(request)}")
    else:
        await interaction.followup.send(f"Added to queue at position {position + 1}: {_track_label(request)}")


@app_commands.command(name="queue", description="Show this server's current and pending tracks.")
async def queue(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("Music playback is unavailable here.", ephemeral=True)
        return
    await _send_queue(interaction, coordinator, guild_id)


@app_commands.command(name="nowplaying", description="Show the current track for this server.")
async def nowplaying(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("Music playback is unavailable here.", ephemeral=True)
        return
    current = coordinator.current(guild_id)
    message = f"Now playing: {_track_label(current)}" if current else "Nothing is playing right now."
    await interaction.response.send_message(message)


@app_commands.command(name="skip", description="Skip the current track in this server.")
async def skip(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("Music playback is unavailable here.", ephemeral=True)
        return
    if coordinator.current(guild_id) is None:
        await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
        return

    player, error = await _get_or_connect_player(interaction)
    if error is not None or player is None:
        await interaction.response.send_message(error or "Unable to find the music player.", ephemeral=True)
        return
    try:
        await player.skip(force=True)
    except Exception:
        logger.exception("Could not skip the current track.")
        await interaction.response.send_message("I could not skip the current track.", ephemeral=True)
        return
    await interaction.response.send_message("Skipped the current track.")


@app_commands.command(name="stop", description="Stop playback, clear this server's queue, and leave voice.")
async def stop(interaction: discord.Interaction) -> None:
    coordinator = _coordinator(interaction)
    guild_id = _guild_id(interaction)
    if coordinator is None or guild_id is None:
        await interaction.response.send_message("Music playback is unavailable here.", ephemeral=True)
        return

    current, pending = coordinator.stop(guild_id)
    voice_client = interaction.guild.voice_client if interaction.guild is not None else None
    if isinstance(voice_client, wavelink.Player):
        try:
            await voice_client.skip(force=True)
            await voice_client.disconnect()
        except Exception:
            logger.exception("Could not fully stop or disconnect the music player.")

    if current is None and not pending:
        await interaction.response.send_message("There was no active music queue.", ephemeral=True)
        return
    await interaction.response.send_message("Stopped playback, cleared the queue, and left voice.")
