"""Phase 2B sanitized read-only status snapshot (bot side).

The bot owns the only source of truth for live music state. To keep the API a
read-only consumer without coupling it to the bot process, the bot writes a
sanitized JSON snapshot to a shared runtime path; the API reads and serves it.

Hard rules enforced here:

* Primary-guild selection happens bot-side at write time. The snapshot payload
  is already single-context: ``voice`` / ``nowPlaying`` / ``queue`` describe one
  primary guild only, while ``health.activePlayers`` and ``services`` may carry
  global summary state.
* Only display-safe, serialisable fields are emitted. No raw runtime track
  objects, no tokens/passwords, no guild/channel/user IDs.
* Source labels reuse :func:`presentation.source_label`; host parsing is never
  re-implemented here.
* Writing is best-effort and atomic; a failure must never affect playback.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable, Sequence
from pathlib import Path

from .presentation import source_label, track_title
from .queue import TrackRequest

logger = logging.getLogger(__name__)

SNAPSHOT_SCHEMA_VERSION = "phase2b.musicStatus.snapshot.v1"

# Static, descriptive source support. Plugin names are public, not secrets.
_SOURCES: tuple[dict[str, object], ...] = (
    {"id": "youtube", "label": "YouTube", "enabled": True, "note": "官方 youtube-source plugin"},
    {"id": "bilibili", "label": "Bilibili", "enabled": True, "note": "lavabili-plugin"},
)
_PLUGINS: tuple[str, ...] = ("youtube-source", "lavabili-plugin")


def select_primary_guild(
    configured_guild_id: int | None,
    current_guild_ids: Iterable[int],
    queued_guild_ids: Iterable[int],
) -> int | None:
    """Deterministically choose the single guild the snapshot represents.

    1. configured ``DISCORD_GUILD_ID`` wins when present;
    2. else the active guild with the smallest numeric id;
    3. else the queued guild with the smallest numeric id;
    4. else ``None`` (idle).
    """

    if configured_guild_id is not None:
        return configured_guild_id
    current = sorted(current_guild_ids)
    if current:
        return current[0]
    queued = sorted(queued_guild_ids)
    if queued:
        return queued[0]
    return None


def build_now_playing(
    request: TrackRequest | None,
    *,
    state: str,
    position_ms: int | None,
) -> dict[str, object | None]:
    """Build the single-context now-playing object for the primary guild."""

    if request is None or state == "idle":
        return {
            "state": "idle",
            "title": None,
            "author": None,
            "source": None,
            "requester": None,
            "durationMs": None,
            "positionMs": None,
            "uri": None,
        }
    return {
        "state": state,
        "title": track_title(request),
        "author": request.author,
        "source": source_label(request),
        # Phase 2B has no display-name source; never expose the raw Discord
        # snowflake (TrackRequest.requester_id) as a display string.
        "requester": None,
        "durationMs": request.duration_ms,
        "positionMs": position_ms,
        "uri": request.uri,
    }


def build_queue(pending: Sequence[TrackRequest]) -> list[dict[str, object | None]]:
    """Build the FIFO queue preview for the primary guild."""

    return [
        {
            "id": f"queue-{index}",
            "title": track_title(request),
            "author": request.author,
            "source": source_label(request),
            # No display name available; never expose the raw Discord user ID.
            "requester": None,
            "durationMs": request.duration_ms,
        }
        for index, request in enumerate(pending)
    ]


def build_voice(
    *,
    state: str,
    guild: str | None,
    channel: str | None,
    listeners: int,
) -> dict[str, object | None]:
    """Build the primary-guild voice object without exposing raw IDs."""

    return {"state": state, "guild": guild, "channel": channel, "listeners": listeners}


def build_service(
    service_id: str,
    name: str,
    status: str,
    headline: str,
    detail: str,
    meta: str | None = None,
) -> dict[str, object | None]:
    return {
        "id": service_id,
        "name": name,
        "status": status,
        "headline": headline,
        "detail": detail,
        "meta": meta,
    }


def build_sources() -> list[dict[str, object]]:
    return [dict(source) for source in _SOURCES]


def build_health(
    *,
    uptime: str | None,
    active_players: int,
    lavalink_secure: bool | None,
    region: str | None,
) -> dict[str, object | None]:
    return {
        "uptime": uptime,
        "activePlayers": active_players,
        "lavalinkSecure": lavalink_secure,
        "plugins": list(_PLUGINS),
        "region": region,
    }


def build_error(scope: str, code: str, message: str) -> dict[str, str]:
    return {"scope": scope, "code": code, "message": message}


def build_payload(
    *,
    services: list[dict[str, object | None]],
    voice: dict[str, object | None],
    now_playing: dict[str, object | None],
    queue: list[dict[str, object | None]],
    sources: list[dict[str, object]],
    health: dict[str, object | None],
    errors: list[dict[str, str]],
) -> dict[str, object]:
    """Assemble the sanitized snapshot payload (bot knowledge, sans api service)."""

    return {
        "services": services,
        "voice": voice,
        "nowPlaying": now_playing,
        "queue": queue,
        "sources": sources,
        "health": health,
        "errors": errors,
    }


def wrap_snapshot(payload: dict[str, object], *, written_at_iso: str) -> dict[str, object]:
    """Wrap a payload with the snapshot envelope the API expects."""

    return {
        "schemaVersion": SNAPSHOT_SCHEMA_VERSION,
        "snapshotWrittenAt": written_at_iso,
        "payload": payload,
    }


class MusicStatusSnapshotWriter:
    """Atomically writes the sanitized snapshot. All failures are non-fatal."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, snapshot: dict[str, object]) -> bool:
        """Write the snapshot atomically. Returns ``True`` only on success.

        Best-effort by contract: a missing directory is created, the write goes
        to a sibling ``.tmp`` file and is then ``os.replace``-d into place so a
        partial read is not possible. Any failure is logged safely and swallowed
        so playback is never affected.
        """

        tmp_path = self._path.with_name(self._path.name + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
            try:
                os.chmod(tmp_path, 0o644)
            except OSError:
                # Permission tweaks are advisory; world-readability helps the API
                # container but is not required for correctness on every host.
                pass
            os.replace(tmp_path, self._path)
            return True
        except Exception:
            logger.warning("Could not write the music status snapshot (non-fatal).", exc_info=True)
            self._cleanup_temp(tmp_path)
            return False

    @staticmethod
    def _cleanup_temp(tmp_path: Path) -> None:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
