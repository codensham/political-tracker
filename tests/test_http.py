import httpx
import pytest

from tracker.http import get_bytes, get_json


def client_from(responses):
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        status, body = queue.pop(0)
        if isinstance(body, bytes):
            return httpx.Response(status, content=body)
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_retry_then_success():
    client = client_from([(429, {}), (200, {"ok": True})])
    sleeps: list[float] = []
    assert get_json(client, "https://example.test/x", sleep=sleeps.append) == {"ok": True}
    assert len(sleeps) == 1


def test_retry_exhausted():
    client = client_from([(503, {})] * 4)
    sleeps: list[float] = []
    with pytest.raises(httpx.HTTPStatusError):
        get_json(client, "https://example.test/x", sleep=sleeps.append)
    assert len(sleeps) == 3


def test_non_retryable_status_raises_immediately():
    client = client_from([(404, {})])
    sleeps: list[float] = []
    with pytest.raises(httpx.HTTPStatusError):
        get_json(client, "https://example.test/x", sleep=sleeps.append)
    assert sleeps == []


def test_get_bytes_returns_content():
    client = client_from([(200, b"abc")])
    assert get_bytes(client, "https://example.test/x", sleep=lambda s: None) == b"abc"
