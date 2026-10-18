"""Send readings to the backend. Keeps a small buffer if the network or server is down."""
from collections import deque
from datetime import datetime, timezone

import httpx


class IngestRejected(Exception):
    """The server said no for a reason retrying will not fix (bad key, uncalibrated camera, bad data)."""


class Ingestor:
    def __init__(self, base_url: str, camera_key: str, timeout: float = 3.0, max_buffer: int = 600, transport=None):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, headers={"X-Camera-Key": camera_key}, transport=transport
        )
        self._buffer: deque[dict] = deque(maxlen=max_buffer)  # oldest readings drop first if full

    @property
    def pending(self) -> int:
        return len(self._buffer)

    def send(self, second: int, count: int, confidence: float | None, degraded: bool) -> None:
        ts = datetime.fromtimestamp(second, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._buffer.append({"people_count": count, "confidence": confidence, "degraded": degraded, "ts": ts})
        self._drain()

    def _drain(self) -> None:
        while self._buffer:
            try:
                r = self._client.post("/density-events", json=self._buffer[0])
            except httpx.HTTPError:
                return  # network problem: keep everything, try again on the next reading
            if r.status_code >= 500:
                return
            item = self._buffer.popleft()
            if r.status_code in (401, 409, 422):
                raise IngestRejected(f"{r.status_code}: {r.text} (reading {item['ts']} dropped)")
            r.raise_for_status()
