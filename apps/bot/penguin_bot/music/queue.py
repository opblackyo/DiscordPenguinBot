"""Pure queue domain models for the future music playback workflow."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackRequest:
    """A user-requested track, independent of Discord and Lavalink client types."""

    query: str
    requester_id: int
    title: str | None = None
    author: str | None = None
    uri: str | None = None
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query must not be empty.")
        if self.requester_id <= 0:
            raise ValueError("requester_id must be a positive Discord snowflake.")
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValueError("duration_ms cannot be negative.")


class GuildQueue:
    """A FIFO queue for one Discord guild's future playback requests."""

    def __init__(self, items: Iterable[TrackRequest] = ()) -> None:
        self._items: deque[TrackRequest] = deque(items)

    def enqueue(self, request: TrackRequest) -> int:
        """Append a request and return its zero-based position in the queue."""

        position = len(self._items)
        self._items.append(request)
        return position

    def peek(self) -> TrackRequest | None:
        """Return the next request without removing it."""

        return self._items[0] if self._items else None

    def dequeue(self) -> TrackRequest | None:
        """Return and remove the next request, if one exists."""

        return self._items.popleft() if self._items else None

    def clear(self) -> tuple[TrackRequest, ...]:
        """Remove and return all queued requests in FIFO order."""

        removed = self.snapshot()
        self._items.clear()
        return removed

    def snapshot(self) -> tuple[TrackRequest, ...]:
        """Return an immutable FIFO-ordered view of the queue."""

        return tuple(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @property
    def is_empty(self) -> bool:
        return not self._items


class GuildQueueStore:
    """In-memory queue ownership keyed by guild ID for Phase 1B."""

    def __init__(self) -> None:
        self._queues: dict[int, GuildQueue] = {}

    def for_guild(self, guild_id: int) -> GuildQueue:
        """Return the guild's queue, creating it on first use."""

        self._validate_guild_id(guild_id)
        return self._queues.setdefault(guild_id, GuildQueue())

    def discard(self, guild_id: int) -> GuildQueue | None:
        """Remove a guild queue when it is no longer needed."""

        self._validate_guild_id(guild_id)
        return self._queues.pop(guild_id, None)

    def active_guild_ids(self) -> tuple[int, ...]:
        """Return the IDs that currently own a queue."""

        return tuple(self._queues)

    @staticmethod
    def _validate_guild_id(guild_id: int) -> None:
        if guild_id <= 0:
            raise ValueError("guild_id must be a positive Discord snowflake.")
