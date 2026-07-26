from server.matchmaking import Matchmaker, QueueEntry


def test_matchmaker_pairs_within_elo_range():
    matchmaker = Matchmaker(elo_range=100, timeout_seconds=60)
    first = QueueEntry('Alice', 1200, 'c1', enqueued_at=0)
    second = QueueEntry('Bob', 1280, 'c2', enqueued_at=1)

    assert matchmaker.enqueue(first) is None
    matched = matchmaker.enqueue(second)

    assert matched is not None
    white, black = matched
    assert white.username == 'Alice'
    assert black.username == 'Bob'
    assert matchmaker.is_queued('c1') is False


def test_matchmaker_ignores_outside_elo_range():
    matchmaker = Matchmaker(elo_range=100, timeout_seconds=60)
    first = QueueEntry('Alice', 1200, 'c1', enqueued_at=0)
    second = QueueEntry('Bob', 1400, 'c2', enqueued_at=1)

    assert matchmaker.enqueue(first) is None
    assert matchmaker.enqueue(second) is None
    assert matchmaker.is_queued('c1') is True
    assert matchmaker.is_queued('c2') is True


def test_matchmaker_expires_after_timeout():
    matchmaker = Matchmaker(elo_range=100, timeout_seconds=60)
    entry = QueueEntry('Alice', 1200, 'c1', enqueued_at=0)
    matchmaker.enqueue(entry)

    expired = matchmaker.pop_expired(now=61)
    assert len(expired) == 1
    assert expired[0].username == 'Alice'
    assert matchmaker.is_queued('c1') is False
