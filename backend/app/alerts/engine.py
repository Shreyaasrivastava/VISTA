"""Alert engine: hysteresis + escalation on top of the per-reading tier.

Pure Python, no database. Tiers match app.services.tier_for:
0 Normal, 1 Caution, 2 Warning, 3 Critical (occupancy % bands per camera).
"""
from dataclasses import dataclass
from typing import Optional

WARNING = 2
CRITICAL = 3


@dataclass
class AlertConfig:
    exit_margin_pct: float = 5.0    # tier tabhi girta hai jab enter-threshold se itna neeche aaye
    confirm_up_s: float = 5.0       # tier badhne se pehle itni der lagatar
    confirm_down_s: float = 10.0    # tier girne se pehle itni der lagatar
    escalate_after_s: float = 120.0  # Warning itni der chale to escalate


@dataclass
class Event:
    key: object
    kind: str            # "tier_change" ya "escalated"
    old_tier: int
    new_tier: int
    pct: float
    ts: float


@dataclass
class _State:
    tier: int = 0
    tier_since: float = 0.0
    candidate: Optional[int] = None
    candidate_since: float = 0.0
    escalated: bool = False
    last_ts: float = 0.0


def raw_tier(pct: float, enter: tuple[float, float, float]) -> int:
    caution, warning, critical = enter
    if pct >= critical:
        return 3
    if pct >= warning:
        return 2
    if pct >= caution:
        return 1
    return 0


class AlertEngine:
    def __init__(self, config: Optional[AlertConfig] = None):
        self.cfg = config or AlertConfig()
        self.states: dict[object, _State] = {}

    def _target(self, cur: int, pct: float, enter) -> int:
        raw = raw_tier(pct, enter)
        if raw < cur and pct >= enter[cur - 1] - self.cfg.exit_margin_pct:
            return cur  # hysteresis band: tier hold karo
        return raw

    def update(self, key, pct: float, ts: float, enter: tuple[float, float, float]) -> list[Event]:
        st = self.states.get(key)
        if st is None:
            st = self.states[key] = _State(tier_since=ts, last_ts=ts)
        ts = max(ts, st.last_ts)  # out-of-order timestamp se time peeche nahi jaata
        st.last_ts = ts
        events: list[Event] = []
        target = self._target(st.tier, pct, enter)

        if target == st.tier:
            st.candidate = None
        elif target != st.candidate:
            st.candidate, st.candidate_since = target, ts
        else:
            need = self.cfg.confirm_up_s if target > st.tier else self.cfg.confirm_down_s
            if ts - st.candidate_since >= need:
                events.append(Event(key, "tier_change", st.tier, target, pct, ts))
                st.tier, st.tier_since = target, ts
                st.candidate, st.escalated = None, False

        if st.tier == WARNING and not st.escalated and ts - st.tier_since >= self.cfg.escalate_after_s:
            st.escalated = True
            events.append(Event(key, "escalated", st.tier, st.tier, pct, ts))
        return events
