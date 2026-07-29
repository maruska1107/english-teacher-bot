import hashlib
import hmac
import time

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings

MAX_ZOOM_TIMESTAMP_SKEW_SECONDS = 300


def compute_zoom_signature(secret: str, timestamp: str, body: bytes) -> str:
    message = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def encrypted_url_validation_token(secret: str, plain_token: str) -> str:
    return hmac.new(secret.encode(), plain_token.encode(), hashlib.sha256).hexdigest()


async def verify_zoom_webhook_signature(
    request: Request,
    settings: Settings,
    x_zm_request_timestamp: str | None = Header(default=None),
    x_zm_signature: str | None = Header(default=None),
) -> bytes:
    if settings.zoom_webhook_secret_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zoom webhook secret is not configured",
        )
    if not x_zm_request_timestamp or not x_zm_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Zoom webhook signature")

    try:
        timestamp = int(x_zm_request_timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Zoom webhook timestamp") from exc

    if abs(int(time.time()) - timestamp) > MAX_ZOOM_TIMESTAMP_SKEW_SECONDS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale Zoom webhook timestamp")

    body = await request.body()
    expected = compute_zoom_signature(
        settings.zoom_webhook_secret_token.get_secret_value(),
        x_zm_request_timestamp,
        body,
    )
    if not hmac.compare_digest(expected, x_zm_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Zoom webhook signature")
    return body
