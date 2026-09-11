import pytest

from app.zoom import transcripts
from app.zoom.transcripts import TranscriptDownloadError, ZoomTranscriptClient, _with_download_token


def test_with_download_token_adds_access_token_query_parameter():
    url = _with_download_token("https://zoom.example/rec/webhook_download/path?foo=bar", "download-token")

    assert url == "https://zoom.example/rec/webhook_download/path?foo=bar&access_token=download-token"


def test_with_download_token_replaces_existing_access_token_parameter():
    url = _with_download_token("https://zoom.example/rec/webhook_download/path?access_token=old", "new-token")

    assert url == "https://zoom.example/rec/webhook_download/path?access_token=new-token"


class FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text

    @property
    def is_error(self) -> bool:
        return self.status_code >= 400


class FakeAsyncClient:
    calls: list[tuple[str, dict[str, str] | None]] = []
    responses: list[FakeResponse] = []

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str, headers: dict[str, str] | None = None) -> FakeResponse:
        self.calls.append((url, headers))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_download_transcript_falls_back_to_bearer_download_token(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [FakeResponse(401), FakeResponse(200, "WEBVTT transcript")]
    monkeypatch.setattr(transcripts.httpx, "AsyncClient", FakeAsyncClient)

    text = await ZoomTranscriptClient().download_transcript(
        "https://zoom.example/rec/webhook_download/path",
        access_token="oauth-token",
        download_token="download-token",
    )

    assert text == "WEBVTT transcript"
    assert FakeAsyncClient.calls == [
        ("https://zoom.example/rec/webhook_download/path?access_token=download-token", None),
        ("https://zoom.example/rec/webhook_download/path", {"Authorization": "Bearer download-token"}),
    ]


@pytest.mark.asyncio
async def test_download_transcript_raises_redacted_error_after_failed_fallbacks(monkeypatch):
    FakeAsyncClient.calls = []
    FakeAsyncClient.responses = [FakeResponse(401), FakeResponse(401), FakeResponse(401)]
    monkeypatch.setattr(transcripts.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(TranscriptDownloadError) as exc:
        await ZoomTranscriptClient().download_transcript(
            "https://zoom.example/rec/webhook_download/secret-path",
            access_token="oauth-token",
            download_token="download-token",
        )

    assert str(exc.value) == "Zoom transcript download failed with HTTP 401"
    assert "secret-path" not in str(exc.value)
    assert "download-token" not in str(exc.value)
