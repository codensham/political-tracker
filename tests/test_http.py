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


def test_api_key_redacted_from_http_error():
    import httpx

    from tracker.http import get_json

    client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(500, json={})),
    )
    try:
        get_json(client, "https://api.example/x", {"api_key": "SECRET123"}, sleep=lambda s: None)
    except httpx.HTTPStatusError as exc:
        assert "SECRET123" not in str(exc)
        assert "REDACTED" in str(exc) or "api_key" not in str(exc)
    else:
        raise AssertionError("expected HTTPStatusError")


def test_redact_helper():
    from tracker.http import redact

    assert redact("https://x/y?api_key=ABC&per_page=1") == "https://x/y?api_key=REDACTED&per_page=1"


def test_every_request_sends_the_project_user_agent():
    from tracker.http import USER_AGENT, get_bytes

    seen = []

    def handler(request):
        seen.append(request.headers.get("user-agent"))
        return httpx.Response(200, content=b"ok")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    get_bytes(client, "https://example.com/x", sleep=lambda s: None)
    assert seen == [USER_AGENT]
    assert USER_AGENT == "political-tracker (+https://github.com/codensham/political-tracker)"
    assert "@" not in USER_AGENT
