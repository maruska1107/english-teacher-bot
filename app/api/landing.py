from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.head("/zoom", response_class=HTMLResponse)
def zoom_landing_page_head() -> str:
    return ""


@router.get("/zoom", response_class=HTMLResponse)
def zoom_landing_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>English Tutor AI — Zoom connection</title>
  <style>
    :root { color-scheme: light; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #f7f8fb;
      color: #111827;
      line-height: 1.6;
    }
    .page {
      max-width: 760px;
      margin: 0 auto;
      padding: 48px 20px;
    }
    .card {
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 20px;
      padding: 32px;
      box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
    }
    h1 {
      margin: 0 0 12px;
      font-size: 34px;
      line-height: 1.15;
    }
    h2 {
      margin-top: 30px;
      font-size: 20px;
    }
    p, li { font-size: 16px; }
    .lead { color: #374151; font-size: 18px; }
    .button {
      display: inline-block;
      margin: 18px 0 8px;
      padding: 13px 18px;
      border-radius: 12px;
      background: #2563eb;
      color: #ffffff;
      text-decoration: none;
      font-weight: 700;
    }
    .note {
      margin-top: 24px;
      padding: 16px;
      border-radius: 14px;
      background: #eff6ff;
      color: #1e3a8a;
    }
    code {
      padding: 2px 6px;
      border-radius: 6px;
      background: #f3f4f6;
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="card">
      <h1>English Tutor AI</h1>
      <p class="lead">
        English Tutor AI helps English tutors generate practical lesson reports from their Zoom lessons.
      </p>

      <h2>How to connect Zoom</h2>
      <ol>
        <li>Open the Telegram bot.</li>
        <li>Send <code>/connect_zoom</code>.</li>
        <li>Authorize Zoom.</li>
        <li>Add a specific Zoom meeting link in Telegram.</li>
      </ol>

      <a class="button" href="https://t.me/EnglishTutorHelperAIBot" rel="noopener noreferrer">Open Telegram Bot</a>

      <h2>Data handling</h2>
      <ul>
        <li>The app only processes meetings explicitly added by the tutor.</li>
        <li>The app does not store video recordings.</li>
        <li>Source lesson data is deleted after processing; only the generated report is stored.</li>
      </ul>

      <div class="note">
        To connect your Zoom account, start from Telegram. This lets the app link the Zoom authorization
        to the correct tutor.
      </div>
    </section>
  </main>
</body>
</html>"""
