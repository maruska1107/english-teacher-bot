from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx


class TranscriptDownloadError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"Zoom transcript download failed with HTTP {status_code}")
        self.status_code = status_code


class TranscriptClientProtocol(Protocol):
    async def download_transcript(
        self,
        download_url: str,
        access_token: str,
        download_token: str | None = None,
    ) -> str: ...


class ZoomTranscriptClient:
    async def download_transcript(
        self,
        download_url: str,
        access_token: str,
        download_token: str | None = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            if download_token:
                response = await client.get(_with_download_token(download_url, download_token))
                if response.status_code == 401:
                    response = await client.get(
                        download_url,
                        headers={"Authorization": f"Bearer {download_token}"},
                    )
                if response.status_code == 401:
                    response = await client.get(download_url, headers={"Authorization": f"Bearer {access_token}"})
            else:
                response = await client.get(download_url, headers={"Authorization": f"Bearer {access_token}"})
            if response.is_error:
                raise TranscriptDownloadError(response.status_code)
            return response.text


def _with_download_token(download_url: str, download_token: str) -> str:
    parts = urlsplit(download_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["access_token"] = download_token
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
