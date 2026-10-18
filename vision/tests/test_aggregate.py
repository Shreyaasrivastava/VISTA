from vista_vision.aggregate import SecondAggregator


def feed(agg, ts, counts, conf=0.8):
    out = []
    for i, c in enumerate(counts):
        r = agg.add(ts + i * 0.1, c, conf)
        if r:
            out.append(r)
    return out


def test_median_resists_one_noisy_frame():
    a = SecondAggregator()
    feed(a, 100.0, [10, 10, 40, 10, 10])
    r = a.flush()
    assert r.count == 10 and r.frames == 5 and not r.degraded


def test_new_second_returns_the_finished_one():
    a = SecondAggregator()
    assert feed(a, 100.0, [5, 5, 5]) == []
    first = a.add(101.0, 7, 0.8)
    assert first.second == 100 and first.count == 5
    assert a.flush().count == 7


def test_few_frames_is_degraded():
    a = SecondAggregator(min_frames=3)
    feed(a, 100.0, [5, 5])
    assert a.flush().degraded is True


def test_low_confidence_is_degraded():
    a = SecondAggregator(min_confidence=0.35)
    feed(a, 100.0, [5, 5, 5, 5], conf=0.2)
    assert a.flush().degraded is True


def test_no_confidence_reported_is_not_degraded_by_it():
    a = SecondAggregator()
    for i in range(4):
        a.add(100 + i * 0.1, 5, None)
    r = a.flush()
    assert r.confidence is None and r.degraded is False


def test_flush_on_empty_is_none():
    assert SecondAggregator().flush() is None
