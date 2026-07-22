from typing import Protocol

import httpx


class TranscriptClientProtocol(Protocol):
    async def download_transcript(self, download_url: str, access_token: str) -> str: ...


class ZoomTranscriptClient:
    async def download_transcript(self, download_url: str, access_token: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(download_url, headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()
            return response.text
