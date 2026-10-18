"""Turn per-frame counts into one robust reading per second."""
from dataclasses import dataclass
from statistics import median


@dataclass
class SecondResult:
    second: int          # whole epoch second the reading covers
    count: int
    confidence: float | None
    degraded: bool
    frames: int


class SecondAggregator:
    """Feed it one count per frame. It returns a SecondResult when a new second starts.

    count = median of the frame counts (one noisy frame cannot swing the reading).
    degraded = too few frames in the second, or low average detector confidence.
    """

    def __init__(self, min_frames: int = 3, min_confidence: float = 0.35):
        self.min_frames = min_frames
        self.min_confidence = min_confidence
        self._second: int | None = None
        self._counts: list[int] = []
        self._confs: list[float] = []

    def add(self, ts: float, count: int, mean_confidence: float | None = None) -> SecondResult | None:
        sec = int(ts)
        done = None
        if self._second is not None and sec != self._second:
            done = self.flush()
        self._second = sec
        self._counts.append(count)
        if mean_confidence is not None:
            self._confs.append(mean_confidence)
        return done

    def flush(self) -> SecondResult | None:
        if self._second is None or not self._counts:
            return None
        conf = sum(self._confs) / len(self._confs) if self._confs else None
        result = SecondResult(
            second=self._second,
            count=int(round(median(self._counts))),
            confidence=None if conf is None else round(conf, 3),
            degraded=len(self._counts) < self.min_frames or (conf is not None and conf < self.min_confidence),
            frames=len(self._counts),
        )
        self._second, self._counts, self._confs = None, [], []
        return result
