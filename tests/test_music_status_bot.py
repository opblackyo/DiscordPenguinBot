"""Phase 2B hardening — bot-side snapshot assembly integration tests.

These exercise PenguinBot._build_status_snapshot() / refresh_status_snapshot()
without connecting to Discord: fake guild / player / lavalink only, no token.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from apps.bot.penguin_bot.bot import PenguinBot, create_bot
from apps.bot.penguin_bot.config import Settings
from apps.bot.penguin_bot.music.queue import TrackRequest
from apps.bot.penguin_bot.music.status_snapshot import SNAPSHOT_SCHEMA_VERSION


class FakePlayer:
    async def play(self, _track: object, **_: object) -> None:
        return None


class FakeLavalink:
    def __init__(self, *, reachable: bool) -> None:
        self._reachable = reachable

    def status(self) -> SimpleNamespace:
        return SimpleNamespace(reachable=self._reachable)


def _bot_with_active_track(*, reachable: bool, guild_id: int = 100, snapshot_path: str | None = None) -> PenguinBot:
    env = {"DISCORD_GUILD_ID": str(guild_id)}
    if snapshot_path is not None:
        env["MUSIC_STATUS_SNAPSHOT_PATH"] = snapshot_path
    bot = create_bot(Settings.from_environment(env))
    bot.lavalink = FakeLavalink(reachable=reachable)
    request = TrackRequest(query="x", requester_id=42, title="夜に駆ける", author="YOASOBI", uri="https://youtu.be/x", duration_ms=261000)
    bot.playback.enqueue(guild_id, request, object())
    asyncio.run(bot.playback.start_if_idle(guild_id, FakePlayer()))
    return bot


def test_build_status_snapshot_assembles_valid_single_context_envelope() -> None:
    bot = _bot_with_active_track(reachable=True)

    snapshot = bot._build_status_snapshot()

    assert snapshot["schemaVersion"] == SNAPSHOT_SCHEMA_VERSION
    assert isinstance(snapshot["snapshotWrittenAt"], str)
    payload = snapshot["payload"]
    assert [s["id"] for s in payload["services"]] == ["bot", "lavalink", "music"]  # api added on the API side
    assert payload["nowPlaying"]["state"] == "playing"
    assert payload["nowPlaying"]["source"] == "YouTube"
    assert payload["nowPlaying"]["requester"] is None  # never the raw snowflake
    assert payload["health"]["activePlayers"] == 1
    json.dumps(snapshot)  # fully serialisable
    assert "42" not in json.dumps(payload["nowPlaying"])


def test_build_status_snapshot_is_idle_without_any_guild() -> None:
    bot = create_bot(Settings.from_environment())  # no DISCORD_GUILD_ID, nothing playing
    bot.lavalink = FakeLavalink(reachable=True)

    payload = bot._build_status_snapshot()["payload"]

    assert payload["nowPlaying"]["state"] == "idle"
    assert payload["nowPlaying"]["title"] is None
    assert payload["queue"] == []
    assert payload["voice"]["state"] == "disconnected"
    assert payload["health"]["activePlayers"] == 0


def test_build_status_snapshot_reports_lavalink_unreachable() -> None:
    bot = _bot_with_active_track(reachable=False)

    payload = bot._build_status_snapshot()["payload"]

    lavalink = next(s for s in payload["services"] if s["id"] == "lavalink")
    music = next(s for s in payload["services"] if s["id"] == "music")
    assert lavalink["status"] == "offline"
    assert music["status"] == "degraded"
    assert "LAVALINK_UNREACHABLE" in {error["code"] for error in payload["errors"]}


def test_refresh_status_snapshot_writes_a_valid_file(tmp_path: Path) -> None:
    target = tmp_path / "runtime" / "status.json"
    bot = _bot_with_active_track(reachable=True, snapshot_path=str(target))

    bot.refresh_status_snapshot()

    assert target.exists()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded["schemaVersion"] == SNAPSHOT_SCHEMA_VERSION
    assert "42" not in target.read_text(encoding="utf-8")


def test_refresh_status_snapshot_is_noop_without_configured_path() -> None:
    bot = create_bot(Settings.from_environment())  # no MUSIC_STATUS_SNAPSHOT_PATH
    bot.lavalink = FakeLavalink(reachable=True)

    # Must not raise even though no writer is configured.
    bot.refresh_status_snapshot()


def test_voice_and_playback_facts_use_duck_typing() -> None:
    assert PenguinBot._voice_facts(None) == ("disconnected", None, None, 0)
    assert PenguinBot._player_playback_facts(None) == (None, False)

    channel = SimpleNamespace(
        name="音樂頻道",
        members=[SimpleNamespace(bot=False), SimpleNamespace(bot=True), SimpleNamespace(bot=False)],
    )
    player = SimpleNamespace(guild=SimpleNamespace(name="企鵝的私人小窩"), channel=channel, position=1234.7, paused=True)

    assert PenguinBot._voice_facts(player) == ("connected", "企鵝的私人小窩", "音樂頻道", 2)
    assert PenguinBot._player_playback_facts(player) == (1234, True)
