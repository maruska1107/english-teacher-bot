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
- Zoom OAuth and recording webhooks
- transcript download pipeline
- OpenAI JSON analysis with one retry on invalid JSON
- Telegram report/admin notifications

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
- `ZOOM_OAUTH_STATE_TTL_MINUTES` (optional, default `15`)
- `AUTO_PROCESS_ZOOM_WEBHOOK_LESSONS` (optional, default `true`)
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
`/connect_zoom` creates a Zoom OAuth authorization URL with a short-lived state token.
`/disconnect_zoom` removes the teacher's stored Zoom OAuth tokens.

## Database schema

Initial MVP tables:

- `users`
- `zoom_tokens`
- `zoom_oauth_states`
- `lessons`
- `lesson_analysis`
- `processed_webhook_events`

## Zoom integration

Configure the Zoom app as a General OAuth app:

- OAuth redirect URL: value of `ZOOM_REDIRECT_URI`, for example `https://your-domain.example/api/zoom/oauth/callback`.
- Event notification endpoint: `https://your-domain.example/api/zoom/webhook`.
- Required event for MVP: recording completed.
- The app must have access to recording transcript download URLs for the connected teacher account.

The webhook endpoint verifies Zoom signatures using `ZOOM_WEBHOOK_SECRET_TOKEN` and supports Zoom `endpoint.url_validation`.
Duplicate `recording.completed` events are ignored through `processed_webhook_events`.

## How to test the bot end-to-end

1. Create a Telegram bot with BotFather and put its token into `.env` as `TELEGRAM_BOT_TOKEN`.
2. Put your Telegram numeric user ID into `ALLOWED_TELEGRAM_TEACHER_IDS`.
3. Put the admin Telegram numeric user ID into `TELEGRAM_ADMIN_ID`.
4. Create/configure the Zoom OAuth app and fill `ZOOM_CLIENT_ID`, `ZOOM_CLIENT_SECRET`, `ZOOM_REDIRECT_URI`, and `ZOOM_WEBHOOK_SECRET_TOKEN`.
5. Fill `OPENAI_API_KEY`.
6. Start the app:

```bash
docker compose up --build
```

7. In Telegram, send `/start` to the bot.
8. Send `/connect_zoom` and open the returned Zoom OAuth link.
9. Complete Zoom authorization.
10. Run a short Zoom meeting with cloud recording and transcript enabled.
11. End the meeting and wait for Zoom to send the recording webhook.
12. The bot downloads the transcript, analyzes it, sends the teacher report to the teacher, and sends an admin copy/error notification to the admin.
13. Use `/last_report`, `/last_error`, and `/status` to inspect the latest state.

For VPS deployment with a real HTTPS domain, see [`docs/deployment-vps.md`](docs/deployment-vps.md).

Application secrets such as Zoom Client Secret, Telegram Bot Token, and OpenAI API key are loaded from environment variables and must not be stored in the database.
