from hashlib import sha256
from secrets import token_urlsafe


def generate_invite_token() -> str:
    return token_urlsafe(24)


def hash_invite_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def build_student_invite_link(bot_username: str, raw_token: str) -> str:
    return f"https://t.me/{bot_username}?start=student_{raw_token}"
