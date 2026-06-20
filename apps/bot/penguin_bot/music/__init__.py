"""Music infrastructure shared by later playback features."""

from .commands import nowplaying, pause, play, queue, resume, skip, stop
from .lavalink import LavalinkConnectionManager, LavalinkStatus, music_status
from .playback import PlaybackCoordinator
from .presentation import build_queue_embed, build_track_embed, format_duration, source_label
from .queue import GuildQueue, GuildQueueStore, TrackRequest

__all__ = (
    "GuildQueue",
    "GuildQueueStore",
    "LavalinkConnectionManager",
    "LavalinkStatus",
    "PlaybackCoordinator",
    "TrackRequest",
    "build_queue_embed",
    "build_track_embed",
    "format_duration",
    "music_status",
    "nowplaying",
    "pause",
    "play",
    "queue",
    "resume",
    "skip",
    "source_label",
    "stop",
)
