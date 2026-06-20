"""Runtime playback coordination built on the pure Phase 1B queue model."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol

from .queue import GuildQueueStore, TrackRequest

logger = logging.getLogger(__name__)


class Player(Protocol):
    """The small portion of a Lavalink player required by the coordinator."""

    async def play(self, track: object, /, **kwargs: Any) -> None:
        """Begin playback for a resolved track."""


class PlaybackCoordinator:
    """Own resolved tracks and playback state without leaking client types into queue.py.

    ``TrackRequest`` stays a pure, serialisable domain value. The corresponding
    Wavelink ``Playable`` is held only here, keyed by its in-memory request.
    """

    def __init__(self, queues: GuildQueueStore | None = None) -> None:
        self.queues = queues or GuildQueueStore()
        self._resolved_tracks: dict[int, object] = {}
        self._current: dict[int, TrackRequest] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def enqueue(self, guild_id: int, request: TrackRequest, track: object) -> int:
        """Append a resolved request and return its zero-based queue position."""

        position = self.queues.for_guild(guild_id).enqueue(request)
        self._resolved_tracks[id(request)] = track
        return position

    def current(self, guild_id: int) -> TrackRequest | None:
        """Return the request currently handed to the player for this guild."""

        return self._current.get(guild_id)

    def pending(self, guild_id: int) -> tuple[TrackRequest, ...]:
        """Return immutable FIFO pending requests for one guild."""

        return self.queues.for_guild(guild_id).snapshot()

    def current_guild_ids(self) -> tuple[int, ...]:
        """Return the guild IDs that currently have an active track."""

        return tuple(self._current)

    def queued_guild_ids(self) -> tuple[int, ...]:
        """Return the guild IDs that currently own a non-empty pending queue."""

        return tuple(
            guild_id
            for guild_id in self.queues.active_guild_ids()
            if not self.queues.for_guild(guild_id).is_empty
        )

    async def start_if_idle(self, guild_id: int, player: Player) -> TrackRequest | None:
        """Start the next track only if this guild has no active request."""

        async with self._lock_for(guild_id):
            if guild_id in self._current:
                return None
            return await self._start_next_locked(guild_id, player)

    async def advance(self, guild_id: int, player: Player) -> TrackRequest | None:
        """Mark the current track complete and begin the next FIFO request, if any."""

        async with self._lock_for(guild_id):
            self._current.pop(guild_id, None)
            return await self._start_next_locked(guild_id, player)

    async def advance_if_current(
        self,
        guild_id: int,
        player: Player,
        *,
        track_uri: str | None,
    ) -> TrackRequest | None:
        """Advance only when a Lavalink event belongs to the active request.

        Playback exceptions can be followed by a delayed track-end event. Matching
        the URI prevents that stale event from skipping the newly started track.
        """

        async with self._lock_for(guild_id):
            current = self._current.get(guild_id)
            if current is None:
                return None
            if track_uri and current.uri and track_uri != current.uri:
                return None
            self._current.pop(guild_id, None)
            return await self._start_next_locked(guild_id, player)

    def stop(self, guild_id: int) -> tuple[TrackRequest | None, tuple[TrackRequest, ...]]:
        """Forget the current and pending requests for a guild."""

        current = self._current.pop(guild_id, None)
        queue = self.queues.discard(guild_id)
        pending = queue.clear() if queue is not None else ()
        for request in pending:
            self._resolved_tracks.pop(id(request), None)
        if current is not None:
            self._resolved_tracks.pop(id(current), None)
        return current, pending

    def _lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    async def _start_next_locked(self, guild_id: int, player: Player) -> TrackRequest | None:
        queue = self.queues.for_guild(guild_id)
        while request := queue.dequeue():
            track = self._resolved_tracks.pop(id(request), None)
            if track is None:
                logger.warning("Skipping a queued track with no resolved playback object.")
                continue

            try:
                await player.play(track)
            except Exception:
                logger.exception("Lavalink failed to start a queued track; trying the next request.")
                continue

            self._current[guild_id] = request
            return request

        self.queues.discard(guild_id)
        return None
