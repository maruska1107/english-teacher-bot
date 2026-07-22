# English Teacher Bot

Production-ready MVP Telegram bot for analyzing Zoom English lessons.

## Current scope

This repository is being built as a simple monolith:

- FastAPI backend
- Telegram command layer for MVP teacher/admin commands
- PostgreSQL database
- SQLAlchemy 2.x models
- Alembic migrations
- Docker Compose with `backend`, `postgres`, and `nginx`

Hermes is used only as a development assistant and is not part of production.

## Local Docker start

1. Create environment file:

```bash
cp .env.example .env
```

2. Fill secrets in `.env`:

- `TELEGRAM_BOT_TOKEN`
- `ALLOWED_TELEGRAM_TEACHER_IDS`
- `TELEGRAM_ADMIN_ID`
- `ZOOM_CLIENT_ID`
- `ZOOM_CLIENT_SECRET`
- `ZOOM_REDIRECT_URI`
- `ZOOM_WEBHOOK_SECRET_TOKEN`
- `OPENAI_API_KEY`

3. Start services:

```bash
docker compose up --build
```

4. Check health:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

## Development tests

```bash
python -m pytest tests -q
```

## Telegram commands

Teacher commands:

- `/start`
- `/connect_zoom`
- `/disconnect_zoom`
- `/status`
- `/last_report`

Admin commands:

- `/status`
- `/last_report`
- `/last_error`

The bot only creates teacher users for Telegram IDs listed in `ALLOWED_TELEGRAM_TEACHER_IDS`.
`TELEGRAM_ADMIN_ID` can access admin status/error commands.

## Database schema

Initial MVP tables:

- `users`
- `zoom_tokens`
- `lessons`
- `lesson_analysis`
- `processed_webhook_events`

Application secrets such as Zoom Client Secret, Telegram Bot Token, and OpenAI API key are loaded from environment variables and must not be stored in the database.
