"""Chinese Discord embed rendering for the Phase 1D music commands."""

from __future__ import annotations

import discord
from urllib.parse import urlparse

from .queue import TrackRequest

_EMBED_COLOUR = discord.Colour.from_rgb(52, 152, 219)


def format_duration(duration_ms: int | None) -> str:
    """Render a duration as a compact human-readable clock value."""

    if duration_ms is None:
        return "未知"
    total_seconds = duration_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


def track_title(request: TrackRequest) -> str:
    """Return the safest available human-facing title for a queued request."""

    return request.title or request.query


def track_link(request: TrackRequest) -> str:
    """Render a title as a Discord link only when the source supplied a URL."""

    title = track_title(request)
    return f"[{title}]({request.uri})" if request.uri else title


def source_label(request: TrackRequest) -> str:
    """Infer a safe, display-only source label without external lookups."""

    candidate = request.uri or request.query
    host = urlparse(candidate).netloc.lower().removeprefix("www.")
    if host in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}:
        return "YouTube"
    if host == "bilibili.com" or host.endswith(".bilibili.com") or host == "b23.tv":
        return "Bilibili"
    return "Unknown"


def build_track_embed(
    request: TrackRequest,
    *,
    heading: str,
    queue_position: int | None = None,
) -> discord.Embed:
    """Build the shared Chinese detail card for a selected track."""

    embed = discord.Embed(title=heading, description=track_link(request), colour=_EMBED_COLOUR)
    embed.add_field(name="作者", value=request.author or "未知", inline=True)
    embed.add_field(name="長度", value=format_duration(request.duration_ms), inline=True)
    embed.add_field(name="來源", value=source_label(request), inline=True)
    embed.add_field(name="點歌者", value=f"<@{request.requester_id}>", inline=True)
    if queue_position is not None:
        embed.add_field(name="佇列位置", value=str(queue_position), inline=True)
    return embed


def build_queue_embed(
    current: TrackRequest | None,
    pending: tuple[TrackRequest, ...],
) -> discord.Embed:
    """Build a Chinese queue overview with at most ten pending tracks."""

    current_value = track_link(current) if current is not None else "目前沒有播放中的歌曲。"
    embed = discord.Embed(title="🎶 播放佇列", colour=_EMBED_COLOUR)
    embed.add_field(name="目前播放", value=current_value, inline=False)

    if not pending:
        embed.add_field(name="下一首", value="佇列目前是空的。", inline=False)
        return embed

    visible = pending[:10]
    lines = [f"`{index}` {track_link(request)}" for index, request in enumerate(visible, start=1)]
    if len(pending) > len(visible):
        lines.append(f"…還有 {len(pending) - len(visible)} 首歌曲。")
    embed.add_field(name=f"下一首（{len(pending)}）", value="\n".join(lines), inline=False)
    return embed
