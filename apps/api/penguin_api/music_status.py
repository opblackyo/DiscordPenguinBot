"""Phase 2B read-only music status endpoint (API side).

The API is a pure consumer of the bot-written sanitized snapshot. It never
imports the bot, never enumerates guilds, never receives or uses Lavalink
credentials, and exposes only ``GET /music/status``. Missing, stale, or invalid
snapshots all return ``200`` with a degraded envelope so the Dashboard can always
render something safe.

Every field served is reconstructed explicitly from the snapshot (allow-list,
type-checked) rather than passed through, so an unexpected snapshot field can
never leak into the response.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESPONSE_SCHEMA_VERSION = "phase2b.musicStatus.v1"
SNAPSHOT_SCHEMA_VERSION = "phase2b.musicStatus.snapshot.v1"

DEFAULT_SNAPSHOT_PATH = "/runtime/music-status/status.json"
DEFAULT_STALE_AFTER_MS = 15_000

_SERVICE_STATUSES = {"online", "playing", "paused", "idle", "degraded", "offline"}
_VOICE_STATES = {"connected", "idle", "disconnected"}
_NOW_STATES = {"playing", "paused", "idle"}
_SOURCE_LABELS = {"YouTube", "Bilibili", "Unknown"}
_DEGRADED_SERVICE_STATUSES = {"degraded", "offline"}

_SERVICE_ORDER = ("bot", "api", "lavalink", "music")

_DEFAULT_SOURCES: tuple[dict[str, Any], ...] = (
    {"id": "youtube", "label": "YouTube", "enabled": True, "note": "youtube-source plugin"},
    {"id": "bilibili", "label": "Bilibili", "enabled": True, "note": "lavabili-plugin"},
)


# --------------------------------------------------------------------------- #
# Environment helpers
# --------------------------------------------------------------------------- #
def snapshot_path() -> Path:
    return Path(os.environ.get("MUSIC_STATUS_SNAPSHOT_PATH", DEFAULT_SNAPSHOT_PATH))


def stale_after_ms() -> int:
    raw = os.environ.get("MUSIC_STATUS_STALE_AFTER_MS")
    if raw is None:
        return DEFAULT_STALE_AFTER_MS
    try:
        return int(raw)
    except ValueError:
        return DEFAULT_STALE_AFTER_MS


# --------------------------------------------------------------------------- #
# Snapshot reading
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SnapshotRead:
    """Result of attempting to read the bot snapshot file."""

    state: str  # "ok" | "missing" | "invalid"
    written_at: str | None = None
    payload: dict[str, Any] | None = None


def read_snapshot(path: Path) -> SnapshotRead:
    if not path.exists():
        return SnapshotRead(state="missing")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return SnapshotRead(state="invalid")
    if not isinstance(obj, dict):
        return SnapshotRead(state="invalid")
    if obj.get("schemaVersion") != SNAPSHOT_SCHEMA_VERSION:
        return SnapshotRead(state="invalid")
    payload = obj.get("payload")
    written_at = obj.get("snapshotWrittenAt")
    if not isinstance(payload, dict) or not isinstance(written_at, str):
        return SnapshotRead(state="invalid")
    return SnapshotRead(state="ok", written_at=written_at, payload=payload)


# --------------------------------------------------------------------------- #
# Field sanitisers (allow-list, type-checked)
# --------------------------------------------------------------------------- #
def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _bool_or_none(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _enum_or(value: Any, allowed: set[str], default: str) -> str:
    return value if isinstance(value, str) and value in allowed else default


def _service(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "id": _str_or_none(raw.get("id")),
        "name": _str_or_none(raw.get("name")) or "",
        "status": _enum_or(raw.get("status"), _SERVICE_STATUSES, "degraded"),
        "headline": _str_or_none(raw.get("headline")) or "未知",
        "detail": _str_or_none(raw.get("detail")) or "",
        "meta": _str_or_none(raw.get("meta")),
    }


def _degraded_service(service_id: str, name: str, status: str, headline: str, detail: str) -> dict[str, Any]:
    return {"id": service_id, "name": name, "status": status, "headline": headline, "detail": detail, "meta": None}


def _api_service() -> dict[str, Any]:
    return _degraded_service("api", "API", "online", "正常", "API 正常回應")


def _voice(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "state": _enum_or(raw.get("state"), _VOICE_STATES, "disconnected"),
        "guild": _str_or_none(raw.get("guild")),
        "channel": _str_or_none(raw.get("channel")),
        "listeners": _int_or_none(raw.get("listeners")) or 0,
    }


def _idle_now_playing() -> dict[str, Any]:
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


def _now_playing(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    state = _enum_or(raw.get("state"), _NOW_STATES, "idle")
    if state == "idle":
        return _idle_now_playing()
    source = raw.get("source")
    return {
        "state": state,
        "title": _str_or_none(raw.get("title")),
        "author": _str_or_none(raw.get("author")),
        "source": source if source in _SOURCE_LABELS else None,
        "requester": _str_or_none(raw.get("requester")),
        "durationMs": _int_or_none(raw.get("durationMs")),
        "positionMs": _int_or_none(raw.get("positionMs")),
        "uri": _str_or_none(raw.get("uri")),
    }


def _queue(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for index, entry in enumerate(raw):
        entry = entry if isinstance(entry, dict) else {}
        items.append(
            {
                "id": _str_or_none(entry.get("id")) or f"queue-{index}",
                "title": _str_or_none(entry.get("title")) or "",
                "author": _str_or_none(entry.get("author")),
                "source": _enum_or(entry.get("source"), _SOURCE_LABELS, "Unknown"),
                "requester": _str_or_none(entry.get("requester")),
                "durationMs": _int_or_none(entry.get("durationMs")),
            }
        )
    return items


def _sources(raw: Any) -> list[dict[str, Any]]:
    sanitised: dict[str, dict[str, Any]] = {}
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            source_id = _str_or_none(entry.get("id"))
            if source_id is None:
                continue
            sanitised[source_id] = {
                "id": source_id,
                "label": _str_or_none(entry.get("label")) or source_id,
                "enabled": bool(entry.get("enabled")),
                "note": _str_or_none(entry.get("note")),
            }
    # Guarantee youtube + bilibili are always present (cardinality rule).
    for default in _DEFAULT_SOURCES:
        sanitised.setdefault(default["id"], dict(default))
    ordered_ids = ["youtube", "bilibili", *[sid for sid in sanitised if sid not in {"youtube", "bilibili"}]]
    return [sanitised[sid] for sid in ordered_ids if sid in sanitised]


def _health(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    plugins_raw = raw.get("plugins")
    plugins = [p for p in plugins_raw if isinstance(p, str)] if isinstance(plugins_raw, list) else []
    return {
        "uptime": _str_or_none(raw.get("uptime")),
        "activePlayers": _int_or_none(raw.get("activePlayers")) or 0,
        "lavalinkSecure": _bool_or_none(raw.get("lavalinkSecure")),
        "plugins": plugins,
        "region": _str_or_none(raw.get("region")),
    }


def _error(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None
    scope = _str_or_none(raw.get("scope"))
    code = _str_or_none(raw.get("code"))
    message = _str_or_none(raw.get("message"))
    if scope is None or code is None or message is None:
        return None
    return {"scope": scope, "code": code, "message": message}


def _services(raw: Any) -> list[dict[str, Any]]:
    """Always return exactly bot/api/lavalink/music in order; api synthesised."""

    by_id: dict[str, dict[str, Any]] = {}
    if isinstance(raw, list):
        for entry in raw:
            service = _service(entry)
            if service["id"] in {"bot", "lavalink", "music"}:
                by_id[service["id"]] = service
    bot = by_id.get("bot") or _degraded_service("bot", "Discord Bot", "offline", "離線", "Bot 狀態暫時無法取得")
    lavalink = by_id.get("lavalink") or _degraded_service(
        "lavalink", "Lavalink", "degraded", "未知", "Lavalink 狀態暫時無法取得"
    )
    music = by_id.get("music") or _degraded_service("music", "Music", "degraded", "異常", "音樂狀態暫時無法取得")
    return [bot, _api_service(), lavalink, music]


# --------------------------------------------------------------------------- #
# Envelope assembly
# --------------------------------------------------------------------------- #
def _parse_age_ms(written_at: str | None, now: datetime) -> int | None:
    if written_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(written_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    delta_ms = int((now - parsed).total_seconds() * 1000)
    return max(0, delta_ms)  # clamp negative drift to 0


def build_response(read: SnapshotRead, *, now: datetime, stale_after: int) -> dict[str, Any]:
    payload = read.payload if read.state == "ok" and read.payload is not None else {}

    services = _services(payload.get("services"))
    errors: list[dict[str, str]] = []

    if read.state == "missing":
        snapshot_age_ms: int | None = None
        written_at: str | None = None
        errors.append({"scope": "snapshot", "code": "SNAPSHOT_MISSING", "message": "Bot status snapshot is not available yet."})
        errors.append({"scope": "bot", "code": "BOT_STATUS_UNAVAILABLE", "message": "Bot status is currently unavailable."})
    elif read.state == "invalid":
        snapshot_age_ms = None
        written_at = None
        errors.append({"scope": "snapshot", "code": "SNAPSHOT_INVALID", "message": "Bot status snapshot could not be read."})
        errors.append({"scope": "bot", "code": "BOT_STATUS_UNAVAILABLE", "message": "Bot status is currently unavailable."})
    else:
        written_at = read.written_at
        snapshot_age_ms = _parse_age_ms(written_at, now)
        for raw_error in payload.get("errors", []) if isinstance(payload.get("errors"), list) else []:
            sanitised = _error(raw_error)
            if sanitised is not None:
                errors.append(sanitised)

    stale = snapshot_age_ms is None or snapshot_age_ms > stale_after
    if stale and read.state == "ok":
        errors.append({"scope": "snapshot", "code": "SNAPSHOT_STALE", "message": "Bot status snapshot is stale."})

    any_service_degraded = any(service["status"] in _DEGRADED_SERVICE_STATUSES for service in services)
    status = "degraded" if (stale or errors or any_service_degraded) else "ok"

    return {
        "schemaVersion": RESPONSE_SCHEMA_VERSION,
        "generatedAt": now.isoformat(),
        "snapshotWrittenAt": written_at,
        "status": status,
        "stale": stale,
        "snapshotAgeMs": snapshot_age_ms,
        "services": services,
        "voice": _voice(payload.get("voice")),
        "nowPlaying": _now_playing(payload.get("nowPlaying")) if read.state == "ok" else _idle_now_playing(),
        "queue": _queue(payload.get("queue")),
        "sources": _sources(payload.get("sources")),
        "health": _health(payload.get("health")),
        "errors": errors,
    }


def get_music_status(
    *,
    path: Path | None = None,
    stale_after: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """High-level read + assemble, using env defaults when not overridden."""

    resolved_path = path if path is not None else snapshot_path()
    resolved_stale = stale_after if stale_after is not None else stale_after_ms()
    resolved_now = now if now is not None else datetime.now(UTC)
    return build_response(read_snapshot(resolved_path), now=resolved_now, stale_after=resolved_stale)
