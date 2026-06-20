import asyncio

from apps.bot.penguin_bot.music.playback import PlaybackCoordinator
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
