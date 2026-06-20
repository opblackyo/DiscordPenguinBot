import pytest

from apps.bot.penguin_bot.music.queue import GuildQueue, GuildQueueStore, TrackRequest


def make_request(query: str, requester_id: int = 1) -> TrackRequest:
    return TrackRequest(query=query, requester_id=requester_id)


def test_track_request_requires_valid_domain_values() -> None:
    with pytest.raises(ValueError, match="query"):
        TrackRequest(query="  ", requester_id=1)
    with pytest.raises(ValueError, match="requester_id"):
        TrackRequest(query="song", requester_id=0)
    with pytest.raises(ValueError, match="duration_ms"):
        TrackRequest(query="song", requester_id=1, duration_ms=-1)


def test_guild_queue_is_fifo_and_reports_positions() -> None:
    queue = GuildQueue()
    first = make_request("first")
    second = make_request("second")

    assert queue.enqueue(first) == 0
    assert queue.enqueue(second) == 1
    assert queue.peek() == first
    assert queue.dequeue() == first
    assert queue.dequeue() == second
    assert queue.dequeue() is None
    assert queue.is_empty is True


def test_snapshot_is_immutable_and_clear_preserves_fifo_order() -> None:
    first = make_request("first")
    second = make_request("second")
    queue = GuildQueue((first, second))

    snapshot = queue.snapshot()

    assert snapshot == (first, second)
    assert queue.clear() == snapshot
    assert queue.snapshot() == ()
    assert queue.is_empty is True


def test_store_keeps_each_guild_queue_isolated() -> None:
    store = GuildQueueStore()
    first_guild = store.for_guild(100)
    second_guild = store.for_guild(200)

    first_guild.enqueue(make_request("guild one", requester_id=10))
    second_guild.enqueue(make_request("guild two", requester_id=20))

    assert first_guild.snapshot()[0].query == "guild one"
    assert second_guild.snapshot()[0].query == "guild two"
    assert store.active_guild_ids() == (100, 200)


def test_store_discards_queues_and_rejects_invalid_guild_ids() -> None:
    store = GuildQueueStore()
    queue = store.for_guild(100)

    assert store.discard(100) is queue
    assert store.discard(100) is None
    with pytest.raises(ValueError, match="guild_id"):
        store.for_guild(0)
