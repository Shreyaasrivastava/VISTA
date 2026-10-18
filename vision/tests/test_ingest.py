import json

import httpx
import pytest

from vista_vision.ingest import Ingestor, IngestRejected


def make(handler):
    return Ingestor("http://api.test", "KEY123", transport=httpx.MockTransport(handler))


def test_sends_payload_and_key():
    seen = []

    def handler(req):
        seen.append((req.headers["x-camera-key"], json.loads(req.content)))
        return httpx.Response(201, json={})

    ing = make(handler)
    ing.send(1_760_000_000, 12, 0.7, False)
    key, body = seen[0]
    assert key == "KEY123"
    assert body == {"people_count": 12, "confidence": 0.7, "degraded": False, "ts": "2025-10-09T08:53:20Z"}
    assert ing.pending == 0


def test_buffers_when_the_network_is_down_then_sends_in_order():
    state = {"up": False}
    got = []

    def handler(req):
        if not state["up"]:
            raise httpx.ConnectError("down")
        got.append(json.loads(req.content)["people_count"])
        return httpx.Response(201, json={})

    ing = make(handler)
    ing.send(100, 1, None, False)
    ing.send(101, 2, None, False)
    assert ing.pending == 2 and got == []
    state["up"] = True
    ing.send(102, 3, None, False)
    assert got == [1, 2, 3] and ing.pending == 0


def test_server_error_keeps_the_reading():
    ing = make(lambda req: httpx.Response(503))
    ing.send(100, 1, None, False)
    assert ing.pending == 1


@pytest.mark.parametrize("status", [401, 409, 422])
def test_permanent_rejection_raises_and_drops(status):
    ing = make(lambda req: httpx.Response(status, text="no"))
    with pytest.raises(IngestRejected):
        ing.send(100, 1, None, False)
    assert ing.pending == 0


def test_buffer_is_bounded():
    ing = Ingestor("http://api.test", "K", max_buffer=3, transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    for i in range(10):
        ing.send(100 + i, i, None, False)
    assert ing.pending == 3
