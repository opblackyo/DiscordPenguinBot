import asyncio

from apps.bot.penguin_bot.music.playback import PlaybackCoordinator
from apps.bot.penguin_bot.music.commands import _normalise_youtube_video_url
from apps.bot.penguin_bot.music.presentation import build_queue_embed, build_track_embed, format_duration
from apps.bot.penguin_bot.music.queue import TrackRequest


class FakePlayer:
    def __init__(self, *, fail_tracks: set[object] | None = None) -> None:
        self.played: list[object] = []
        self.fail_tracks = fail_tracks or set()

    async def play(self, track: object, **_: object) -> None:
        if track in self.fail_tracks:
            raise RuntimeError("simulated Lavalink playback failure")
        self.played.append(track)


def request(query: str, requester_id: int = 1) -> TrackRequest:
    return TrackRequest(query=query, requester_id=requester_id)


def test_coordinator_starts_and_advances_in_fifo_order() -> None:
    async def run() -> None:
        coordinator = PlaybackCoordinator()
        player = FakePlayer()
        first, second = request("first"), request("second")
        first_track, second_track = object(), object()

        assert coordinator.enqueue(100, first, first_track) == 0
        assert coordinator.enqueue(100, second, second_track) == 1
        assert await coordinator.start_if_idle(100, player) is first
        assert coordinator.current(100) is first
        assert coordinator.pending(100) == (second,)

        assert await coordinator.advance(100, player) is second
        assert coordinator.current(100) is second
        assert coordinator.pending(100) == ()
        assert player.played == [first_track, second_track]

        assert await coordinator.advance(100, player) is None
        assert coordinator.current(100) is None

    asyncio.run(run())


def test_coordinator_keeps_guild_playback_isolated() -> None:
    async def run() -> None:
        coordinator = PlaybackCoordinator()
        player = FakePlayer()
        one, two = request("one"), request("two")
        first_track, second_track = object(), object()

        coordinator.enqueue(100, one, first_track)
        coordinator.enqueue(200, two, second_track)
        assert await coordinator.start_if_idle(100, player) is one

        assert coordinator.current(100) is one
        assert coordinator.current(200) is None
        assert coordinator.pending(200) == (two,)
        assert await coordinator.start_if_idle(200, player) is two
        assert player.played == [first_track, second_track]

    asyncio.run(run())


def test_playback_failure_skips_only_the_failed_request() -> None:
    async def run() -> None:
        coordinator = PlaybackCoordinator()
        broken, good = request("broken"), request("good")
        broken_track, good_track = object(), object()
        player = FakePlayer(fail_tracks={broken_track})

        coordinator.enqueue(100, broken, broken_track)
        coordinator.enqueue(100, good, good_track)

        assert await coordinator.start_if_idle(100, player) is good
        assert coordinator.current(100) is good
        assert player.played == [good_track]

    asyncio.run(run())


def test_stop_clears_current_and_pending_requests() -> None:
    async def run() -> None:
        coordinator = PlaybackCoordinator()
        player = FakePlayer()
        first, second = request("first"), request("second")
        coordinator.enqueue(100, first, object())
        coordinator.enqueue(100, second, object())
        await coordinator.start_if_idle(100, player)

        current, pending = coordinator.stop(100)

        assert current is first
        assert pending == (second,)
        assert coordinator.current(100) is None
        assert coordinator.pending(100) == ()

    asyncio.run(run())


def test_youtube_video_urls_are_normalised_without_adding_playlist_support() -> None:
    assert (
        _normalise_youtube_video_url("https://youtu.be/9bc1bb60DRI?si=tracking")
        == "https://www.youtube.com/watch?v=9bc1bb60DRI"
    )
    assert (
        _normalise_youtube_video_url(
            "https://www.youtube.com/watch?v=9bc1bb60DRI&list=RD9bc1bb60DRI&start_radio=1"
        )
        == "https://www.youtube.com/watch?v=9bc1bb60DRI"
    )
    assert (
        _normalise_youtube_video_url("https://www.youtube.com/playlist?list=PL123")
        == "https://www.youtube.com/playlist?list=PL123"
    )


def test_track_embed_is_secret_safe_and_omits_an_empty_url() -> None:
    track = TrackRequest(
        query="song",
        requester_id=123,
        title="中文歌名",
        author="測試作者",
        duration_ms=65_000,
    )

    embed = build_track_embed(track, heading="🎵 正在播放")
    rendered = str(embed.to_dict())

    assert embed.url is None
    assert "secret-lavalink-password" not in rendered
    assert any(field.name == "長度" and field.value == "1:05" for field in embed.fields)
    assert not any(field.name == "連結" for field in embed.fields)


def test_duration_format_supports_minutes_and_hours() -> None:
    assert format_duration(None) == "未知"
    assert format_duration(0) == "0:00"
    assert format_duration(65_000) == "1:05"
    assert format_duration(3_661_000) == "1:01:01"


def test_queue_embed_limits_visible_tracks_and_reports_the_remainder() -> None:
    current = TrackRequest(query="current", requester_id=1, title="目前歌曲")
    pending = tuple(TrackRequest(query=f"track-{index}", requester_id=index + 2) for index in range(12))

    embed = build_queue_embed(current, pending)
    upcoming = next(field for field in embed.fields if field.name.startswith("下一首"))

    assert "`10` track-9" in upcoming.value
    assert "`11`" not in upcoming.value
    assert "…還有 2 首歌曲。" in upcoming.value
