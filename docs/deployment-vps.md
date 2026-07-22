# VPS deployment guide

Target server assumptions:

- Debian 12 VPS
- repository path: `/opt/english-teacher-bot`
- public HTTPS domain is already configured: `https://englishtutorai.ru`
- Let's Encrypt certificate is already installed on the host
- host-level Nginx terminates HTTPS and proxies to this app on `127.0.0.1:8080`

## 1. Pull the project on the VPS

```bash
cd /opt/english-teacher-bot
git remote set-url origin git@github.com:maruska1107/english-teacher-bot.git
git fetch origin
git checkout feat/mvp-foundation
git pull --ff-only origin feat/mvp-foundation
```

After the PR is merged, use `main` instead of `feat/mvp-foundation`.

## 2. Create `.env`

Create `/opt/english-teacher-bot/.env` from `.env.example` and fill real values on the VPS only.
Do not commit `.env`.
Do not paste production secrets into GitHub issues, pull requests, or chat.

Required production values:

```env
APP_ENV=production
LOG_LEVEL=INFO

POSTGRES_USER=english_teacher
POSTGRES_PASSWORD=<strong database password>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=english_teacher_bot

TELEGRAM_BOT_TOKEN=<new Telegram bot token>
ALLOWED_TELEGRAM_TEACHER_IDS=<teacher numeric Telegram user id>
TELEGRAM_ADMIN_ID=<admin numeric Telegram user id>

ZOOM_CLIENT_ID=<Zoom OAuth client id>
ZOOM_CLIENT_SECRET=<Zoom OAuth client secret>
ZOOM_REDIRECT_URI=https://englishtutorai.ru/api/zoom/oauth/callback
ZOOM_WEBHOOK_SECRET_TOKEN=<Zoom webhook secret token>
ZOOM_OAUTH_STATE_TTL_MINUTES=15
AUTO_PROCESS_ZOOM_WEBHOOK_LESSONS=true

OPENAI_API_KEY=<OpenAI API key>
OPENAI_MODEL=gpt-4.1-mini
```

Important: `ZOOM_REDIRECT_URI` must start with exactly `https://`, not `https:https://`.

## 3. Host Nginx reverse proxy

If host Nginx already owns HTTPS for `englishtutorai.ru`, proxy traffic to the Docker Nginx service on localhost port 8080:

```nginx
server {
    listen 443 ssl http2;
    server_name englishtutorai.ru;

    # Existing Let's Encrypt ssl_certificate / ssl_certificate_key directives stay here.

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

Reload host Nginx after changing its config:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 4. Start the app

```bash
cd /opt/english-teacher-bot
docker compose up -d --build
```

The backend entrypoint runs Alembic migrations automatically when `RUN_MIGRATIONS=1`.

## 5. Verify deployment

```bash
curl -fsS https://englishtutorai.ru/health
curl -fsS https://englishtutorai.ru/ready
docker compose ps
docker compose logs --no-color --tail=100 backend
```

Expected health responses:

```json
{"status":"ok","service":"english-teacher-bot"}
```

```json
{"status":"ready","database":"ok"}
```

## 6. Configure Telegram

In Telegram:

1. Open the bot.
2. Send `/start`.
3. Send `/connect_zoom`.
4. Open the Zoom OAuth URL returned by the bot.
5. Complete Zoom authorization.

## 7. Configure Zoom

In the Zoom General OAuth app:

- OAuth redirect URL: `https://englishtutorai.ru/api/zoom/oauth/callback`
- Event notification endpoint: `https://englishtutorai.ru/api/zoom/webhook`
- Required event: `recording.completed`

Cloud recording and audio transcript must be enabled for the test meeting.

## 8. End-to-end test

1. Start a short Zoom meeting from the connected Zoom account.
2. Enable cloud recording.
3. Make sure audio transcript is enabled.
4. End the meeting and wait until Zoom finishes processing the recording/transcript.
5. Zoom sends `recording.completed` to the app.
6. The app downloads the transcript, analyzes it via OpenAI, sends a teacher report to Telegram, and sends an admin copy/error notification.

Useful Telegram commands after the test:

- `/status`
- `/last_report`
- `/last_error` for admin

## 9. Troubleshooting

```bash
docker compose logs --no-color --tail=200 backend
docker compose exec -T postgres psql -U english_teacher -d english_teacher_bot -c 'select id, processing_status, processing_error from lessons order by id desc limit 5;'
```

Common issues:

- Telegram command does not answer: check `TELEGRAM_BOT_TOKEN` and backend logs.
- `/connect_zoom` returns a placeholder/not-ready message: check Zoom OAuth env values.
- Zoom callback fails: verify the exact redirect URL in Zoom and `.env`.
- Webhook returns unauthorized: check `ZOOM_WEBHOOK_SECRET_TOKEN`.
- Lesson fails with empty transcript URL: enable Zoom cloud recording transcript/audio transcript.
