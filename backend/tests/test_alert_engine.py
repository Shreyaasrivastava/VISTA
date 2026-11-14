from app.alerts.engine import AlertEngine

TH = (50, 75, 90)


def run(values, start=0):
    eng, out = AlertEngine(), []
    for i, v in enumerate(values):
        out += eng.update("cam1", v, start + i, TH)
    return out


def tiers(ev):
    return [e.new_tier for e in ev if e.kind == "tier_change"]


def test_short_spike_does_not_alert():
    assert run([10] * 5 + [95] * 2 + [10] * 5) == []


def test_warning_then_critical_then_recover():
    ev = run([10] * 3 + [80] * 7 + [95] * 7 + [10] * 15)
    assert tiers(ev) == [2, 3, 0]


def test_hysteresis_band_holds_tier():
    # Warning enter 75, exit 70. 72 band mein hai => Warning hi rahe.
    assert tiers(run([80] * 7 + [72] * 40)) == [2]


def test_drops_when_below_exit_band():
    assert tiers(run([80] * 7 + [60] * 15)) == [2, 1]


def test_escalation_after_warning_lasts():
    ev = run([80] * 200)
    assert [e.kind for e in ev].count("escalated") == 1


def test_cameras_are_independent():
    eng = AlertEngine()
    out = []
    for i in range(10):
        out += eng.update("a", 80, i, TH)
        out += eng.update("b", 10, i, TH)
    assert {e.key for e in out} == {"a"}


def test_out_of_order_timestamp_does_not_go_back():
    eng = AlertEngine()
    eng.update("a", 80, 100, TH)
    assert eng.update("a", 80, 50, TH) == []  # purana ts, kuch nahi hona
