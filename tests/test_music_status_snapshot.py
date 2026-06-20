"""Phase 2B — bot-side sanitized status snapshot tests."""

from __future__ import annotations

import json
from pathlib import Path

from apps.bot.penguin_bot.music.queue import TrackRequest
from apps.bot.penguin_bot.music.status_snapshot import (
    SNAPSHOT_SCHEMA_VERSION,
    MusicStatusSnapshotWriter,
    build_now_playing,
    build_payload,
    build_queue,
    build_sources,
    select_primary_guild,
    wrap_snapshot,
)


def test_primary_guild_prefers_configured_guild() -> None:
    assert select_primary_guild(456, current_guild_ids=[100, 200], queued_guild_ids=[300]) == 456


def test_primary_guild_falls_back_to_smallest_active_then_queued() -> None:
    assert select_primary_guild(None, current_guild_ids=[300, 100, 200], queued_guild_ids=[50]) == 100
    assert select_primary_guild(None, current_guild_ids=[], queued_guild_ids=[80, 40, 60]) == 40
    assert select_primary_guild(None, current_guild_ids=[], queued_guild_ids=[]) is None


def test_now_playing_idle_is_all_null() -> None:
    idle = build_now_playing(None, state="idle", position_ms=1000)
    assert idle == {
        "state": "idle",
        "title": None,
        "author": None,
        "source": None,
        "requester": None,
        "durationMs": None,
        "positionMs": None,
        "uri": None,
    }


def test_now_playing_reuses_source_label_and_serialises_safely() -> None:
    request = TrackRequest(
        query="x",
        requester_id=42,
        title="夜に駆ける",
        author="YOASOBI",
        uri="https://youtu.be/abc",
        duration_ms=261000,
    )
    now_playing = build_now_playing(request, state="playing", position_ms=96000)

    assert now_playing["source"] == "YouTube"  # via presentation.source_label
    assert now_playing["requester"] == "42"  # display string, not raw int identity
    assert now_playing["title"] == "夜に駆ける"
    assert now_playing["positionMs"] == 96000


def test_queue_serialises_to_primitive_dicts() -> None:
    pending = (
        TrackRequest(query="a", requester_id=1, title="A", uri="https://www.bilibili.com/video/BV1"),
        TrackRequest(query="b", requester_id=2, title="B"),
    )
    items = build_queue(pending)

    assert [item["source"] for item in items] == ["Bilibili", "Unknown"]
    assert items[0]["id"] == "queue-0"
    # No raw TrackRequest / runtime objects leak: every value is JSON-native.
    json.dumps(items)


def test_snapshot_writer_creates_parent_dir_and_writes_atomically(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "runtime" / "status.json"
    writer = MusicStatusSnapshotWriter(target)
    payload = build_payload(
        services=[],
        voice={"state": "disconnected", "guild": None, "channel": None, "listeners": 0},
        now_playing=build_now_playing(None, state="idle", position_ms=None),
        queue=[],
        sources=build_sources(),
        health={"uptime": "1 分", "activePlayers": 0, "lavalinkSecure": False, "plugins": [], "region": "local"},
        errors=[],
    )
    snapshot = wrap_snapshot(payload, written_at_iso="2026-06-20T00:00:00+00:00")

    assert writer.write(snapshot) is True
    assert target.exists()
    assert not target.with_name(target.name + ".tmp").exists()

    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["schemaVersion"] == SNAPSHOT_SCHEMA_VERSION
    assert loaded["snapshotWrittenAt"] == "2026-06-20T00:00:00+00:00"
    assert "payload" in loaded


def test_snapshot_contains_no_secret_like_fields(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    writer = MusicStatusSnapshotWriter(target)
    payload = build_payload(
        services=[],
        voice={"state": "connected", "guild": "G", "channel": "C", "listeners": 1},
        now_playing=build_now_playing(
            TrackRequest(query="x", requester_id=1, title="T", uri="https://youtu.be/x"),
            state="playing",
            position_ms=1000,
        ),
        queue=[],
        sources=build_sources(),
        health={"uptime": "1 分", "activePlayers": 1, "lavalinkSecure": False, "plugins": [], "region": "local"},
        errors=[],
    )
    writer.write(wrap_snapshot(payload, written_at_iso="2026-06-20T00:00:00+00:00"))

    rendered = target.read_text(encoding="utf-8").lower()
    for forbidden in ("password", "token", "cookie", "secret"):
        assert forbidden not in rendered
