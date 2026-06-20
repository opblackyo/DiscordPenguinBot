"""Phase 2B — API read-only music status tests."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from apps.api.penguin_api.main import create_app
from apps.api.penguin_api.music_status import (
    RESPONSE_SCHEMA_VERSION,
    build_response,
    get_music_status,
    read_snapshot,
)
from apps.bot.penguin_bot.music.queue import TrackRequest
from apps.bot.penguin_bot.music.status_snapshot import (
    MusicStatusSnapshotWriter,
    build_health,
    build_now_playing,
    build_payload,
    build_queue,
    build_service,
    build_sources,
    build_voice,
    wrap_snapshot,
)

_NOW = datetime(2026, 6, 20, 12, 0, 0, tzinfo=UTC)


def _write_snapshot(path: Path, *, written_at: datetime, **overrides: object) -> None:
    payload = build_payload(
        services=overrides.get(
            "services",
            [
                build_service("bot", "Discord Bot", "online", "在線", "已連線"),
                build_service("lavalink", "Lavalink", "online", "可連線", "ok"),
                build_service("music", "Music", "playing", "播放中", "串流中"),
            ],
        ),
        voice=overrides.get("voice", build_voice(state="connected", guild="G", channel="C", listeners=2)),
        now_playing=overrides.get(
            "now_playing",
            build_now_playing(
                TrackRequest(query="x", requester_id=1, title="T", author="A", uri="https://youtu.be/x", duration_ms=1000),
                state="playing",
                position_ms=500,
            ),
        ),
        queue=overrides.get("queue", build_queue((TrackRequest(query="y", requester_id=2, title="Y"),))),
        sources=overrides.get("sources", build_sources()),
        health=overrides.get(
            "health",
            build_health(uptime="1 分", active_players=1, lavalink_secure=False, region="local"),
        ),
        errors=overrides.get("errors", []),
    )
    snapshot = wrap_snapshot(payload, written_at_iso=written_at.isoformat())
    MusicStatusSnapshotWriter(path).write(snapshot)


def test_valid_snapshot_yields_ok_envelope(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, written_at=_NOW - timedelta(seconds=2))

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["schemaVersion"] == RESPONSE_SCHEMA_VERSION
    assert response["status"] == "ok"
    assert response["stale"] is False
    assert response["snapshotAgeMs"] == 2000
    assert [s["id"] for s in response["services"]] == ["bot", "api", "lavalink", "music"]
    assert {s["id"] for s in response["sources"]} >= {"youtube", "bilibili"}
    assert response["nowPlaying"]["source"] in {"YouTube", "Bilibili", "Unknown", None}
    assert response["errors"] == []


def test_api_service_is_always_online_and_present(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, written_at=_NOW)
    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)
    api_service = next(s for s in response["services"] if s["id"] == "api")
    assert api_service["status"] == "online"


def test_missing_snapshot_is_degraded_200_payload(tmp_path: Path) -> None:
    response = build_response(read_snapshot(tmp_path / "absent.json"), now=_NOW, stale_after=15000)

    assert response["status"] == "degraded"
    assert response["stale"] is True
    assert response["snapshotAgeMs"] is None
    assert response["snapshotWrittenAt"] is None
    assert response["nowPlaying"]["state"] == "idle"
    assert response["queue"] == []
    codes = {error["code"] for error in response["errors"]}
    assert "SNAPSHOT_MISSING" in codes
    assert "BOT_STATUS_UNAVAILABLE" in codes
    assert {s["id"] for s in response["services"]} == {"bot", "api", "lavalink", "music"}
    assert {s["id"] for s in response["sources"]} >= {"youtube", "bilibili"}


def test_stale_snapshot_is_degraded_with_stale_error(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, written_at=_NOW - timedelta(seconds=60))

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["status"] == "degraded"
    assert response["stale"] is True
    assert response["snapshotAgeMs"] == 60000
    assert "SNAPSHOT_STALE" in {error["code"] for error in response["errors"]}


def test_invalid_json_snapshot_is_degraded_invalid(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    path.write_text("{not valid json", encoding="utf-8")

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["status"] == "degraded"
    assert "SNAPSHOT_INVALID" in {error["code"] for error in response["errors"]}


def test_unrecognized_schema_version_is_invalid(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    path.write_text(
        json.dumps({"schemaVersion": "something.else", "snapshotWrittenAt": _NOW.isoformat(), "payload": {}}),
        encoding="utf-8",
    )

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["status"] == "degraded"
    assert "SNAPSHOT_INVALID" in {error["code"] for error in response["errors"]}


def test_negative_clock_drift_clamps_age_to_zero(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, written_at=_NOW + timedelta(seconds=5))  # snapshot "from the future"

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["snapshotAgeMs"] == 0


def test_response_reconstructs_fields_and_drops_unknown_snapshot_keys(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    leaky_service = build_service("bot", "Discord Bot", "online", "在線", "ok")
    leaky_service["secretLeak"] = "LAVALINK_PASSWORD=hunter2"  # must NOT survive
    _write_snapshot(
        path,
        written_at=_NOW,
        services=[leaky_service, build_service("lavalink", "Lavalink", "online", "ok", "ok"), build_service("music", "Music", "idle", "閒置", "")],
    )

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    rendered = json.dumps(response).lower()
    assert "secretleak" not in rendered
    assert "hunter2" not in rendered
    assert "password" not in rendered


def test_response_never_exposes_raw_requester_snowflake(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    snowflake = 987654321012345678
    track = TrackRequest(query="x", requester_id=snowflake, title="T", uri="https://youtu.be/x", duration_ms=1000)
    _write_snapshot(
        path,
        written_at=_NOW,
        now_playing=build_now_playing(track, state="playing", position_ms=0),
        queue=build_queue((track,)),
    )

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["nowPlaying"]["requester"] is None
    assert all(item["requester"] is None for item in response["queue"])
    assert str(snowflake) not in json.dumps(response)


def test_lavalink_unavailable_keeps_api_online_and_distinguishes_concepts(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(
        path,
        written_at=_NOW,
        services=[
            build_service("bot", "Discord Bot", "online", "在線", "ok"),
            build_service("lavalink", "Lavalink", "offline", "離線", "down"),
            build_service("music", "Music", "degraded", "異常", ""),
        ],
        errors=[{"scope": "lavalink", "code": "LAVALINK_UNREACHABLE", "message": "Lavalink is currently unreachable."}],
    )

    response = build_response(read_snapshot(path), now=_NOW, stale_after=15000)

    assert response["status"] == "degraded"
    assert next(s for s in response["services"] if s["id"] == "api")["status"] == "online"
    assert next(s for s in response["services"] if s["id"] == "lavalink")["status"] == "offline"
    assert "LAVALINK_UNREACHABLE" in {error["code"] for error in response["errors"]}


def test_endpoint_returns_json_200(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "status.json"
    _write_snapshot(path, written_at=datetime.now(UTC))
    monkeypatch.setenv("MUSIC_STATUS_SNAPSHOT_PATH", str(path))
    monkeypatch.setenv("MUSIC_STATUS_STALE_AFTER_MS", "15000")

    async def request_status() -> httpx.Response:
        transport = httpx.ASGITransport(app=create_app())
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/music/status")

    response = asyncio.run(request_status())

    assert response.status_code == 200
    body = response.json()
    assert body["schemaVersion"] == RESPONSE_SCHEMA_VERSION
    assert [s["id"] for s in body["services"]] == ["bot", "api", "lavalink", "music"]


def test_get_music_status_uses_env_defaults_without_lavalink_credentials(tmp_path: Path, monkeypatch) -> None:
    # No LAVALINK_* env is set; the API must still produce a valid envelope.
    path = tmp_path / "status.json"
    _write_snapshot(path, written_at=datetime.now(UTC))
    monkeypatch.setenv("MUSIC_STATUS_SNAPSHOT_PATH", str(path))
    monkeypatch.delenv("LAVALINK_PASSWORD", raising=False)

    response = get_music_status()
    assert response["schemaVersion"] == RESPONSE_SCHEMA_VERSION
