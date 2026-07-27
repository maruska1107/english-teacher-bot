from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STYLE = """
:root { color-scheme: light; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: #f7f8fb;
  color: #111827;
  line-height: 1.6;
}
.page { max-width: 820px; margin: 0 auto; padding: 48px 20px; }
.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
}
h1 { margin: 0 0 12px; font-size: 34px; line-height: 1.15; }
h2 { margin-top: 30px; font-size: 20px; }
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
code { padding: 2px 6px; border-radius: 6px; background: #f3f4f6; }
a { color: #2563eb; }
"""


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>{STYLE}</style>
</head>
<body>
  <main class="page">
    <section class="card">
      {body}
    </section>
  </main>
</body>
</html>"""


def _head_response() -> str:
    return ""


@router.head("/zoom", response_class=HTMLResponse)
def zoom_landing_page_head() -> str:
    return _head_response()


@router.get("/zoom", response_class=HTMLResponse)
def zoom_landing_page() -> str:
    return _page(
        "English Tutor AI — Zoom connection",
        """
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

      <a class="button" href="https://t.me/EnglishTutorHelperAIBot" rel="noopener noreferrer">
        Open Telegram Bot
      </a>

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
        """,
    )


@router.head("/privacy", response_class=HTMLResponse)
def privacy_policy_head() -> str:
    return _head_response()


@router.get("/privacy", response_class=HTMLResponse)
def privacy_policy() -> str:
    return _page(
        "English Tutor AI — Privacy Policy",
        """
      <h1>Privacy Policy</h1>
      <p class="lead">Last updated: July 27, 2026</p>
      <p>
        English Tutor AI helps English tutors analyze their own Zoom lessons and prepare lesson reports.
        This Privacy Policy explains what information the app collects, uses, shares, retains, and deletes.
      </p>

      <h2>Information we collect</h2>
      <ul>
        <li>Telegram user ID for access control and report delivery.</li>
        <li>Zoom OAuth authorization data needed to access the connected tutor's Zoom lesson data.</li>
        <li>Zoom meeting identifiers for meetings explicitly added by the tutor.</li>
        <li>Lesson source data made available by Zoom, such as cloud recording transcript data.</li>
        <li>Generated lesson reports and structured analysis results.</li>
      </ul>

      <h2>How we use information</h2>
      <ul>
        <li>To connect a tutor's Zoom account after the tutor authorizes the app.</li>
        <li>To process only the Zoom meetings that the tutor explicitly adds in Telegram.</li>
        <li>To generate and send lesson reports to the tutor.</li>
        <li>To operate, secure, debug, and improve the service.</li>
      </ul>

      <h2>Data retention</h2>
      <p>
        The app does not store video recordings. Source lesson data is deleted after processing.
        The app stores the generated report, structured analysis result, meeting identifiers,
        and service records needed to operate the app.
      </p>

      <h2>Sharing</h2>
      <p>
        We do not sell personal information. Data may be processed by infrastructure and service providers
        needed to run the app, including Telegram, Zoom, hosting providers, and the configured AI provider.
      </p>

      <h2>Your data subject rights</h2>
      <p>
        Depending on your location, you may have data subject rights, including the right to request access,
        correction, deletion, restriction, portability, or objection to processing of your personal information.
        To exercise these rights, contact support through the Telegram bot:
        <a href="https://t.me/EnglishTutorHelperAIBot">https://t.me/EnglishTutorHelperAIBot</a>.
      </p>

      <h2>Removing access</h2>
      <p>
        A tutor can disconnect Zoom by sending <code>/disconnect_zoom</code> to the Telegram bot.
        You can also remove the app from your Zoom account in Zoom Marketplace settings.
      </p>
        """,
    )


@router.head("/terms", response_class=HTMLResponse)
def terms_of_use_head() -> str:
    return _head_response()


@router.get("/terms", response_class=HTMLResponse)
def terms_of_use() -> str:
    return _page(
        "English Tutor AI — Terms of Use",
        """
      <h1>Terms of Use</h1>
      <p class="lead">Last updated: July 27, 2026</p>
      <p>
        These Terms of Use govern access to English Tutor AI, a Telegram-based assistant that connects
        to Zoom with tutor authorization and generates practical English lesson reports.
      </p>

      <h2>Use of the service</h2>
      <ul>
        <li>You must only connect Zoom accounts and meetings that you are authorized to use.</li>
        <li>You are responsible for notifying students and participants when lesson data is analyzed.</li>
        <li>You must comply with Zoom, Telegram, and applicable laws when using the service.</li>
      </ul>

      <h2>Reports</h2>
      <p>
        Reports are generated to assist tutors and may contain automated analysis. You should review reports
        before sending them to students or relying on them for educational decisions.
      </p>

      <h2>Availability</h2>
      <p>
        The service is provided for tutor workflow support. We may update, pause, or change functionality
        as needed for security, maintenance, or product improvements.
      </p>

      <h2>Support</h2>
      <p>
        For help, open the Telegram bot:
        <a href="https://t.me/EnglishTutorHelperAIBot">https://t.me/EnglishTutorHelperAIBot</a>.
      </p>
        """,
    )


@router.head("/support", response_class=HTMLResponse)
def support_head() -> str:
    return _head_response()


@router.get("/support", response_class=HTMLResponse)
def support() -> str:
    return _page(
        "English Tutor AI — Support",
        """
      <h1>Support</h1>
      <p class="lead">Need help with English Tutor AI?</p>
      <p>
        Support is provided through the Telegram bot. Open the bot and send your question or issue details.
      </p>
      <a class="button" href="https://t.me/EnglishTutorHelperAIBot" rel="noopener noreferrer">
        Open EnglishTutorHelperAIBot in Telegram
      </a>

      <h2>Useful commands</h2>
      <ul>
        <li><code>/start</code> — show onboarding information.</li>
        <li><code>/connect_zoom</code> — connect your Zoom account.</li>
        <li><code>/disconnect_zoom</code> — remove the Zoom connection.</li>
        <li><code>/status</code> — check connection status.</li>
        <li><code>/add_zoom_meeting &lt;link&gt;</code> — add a Zoom meeting for analysis.</li>
      </ul>
        """,
    )


@router.head("/documentation", response_class=HTMLResponse)
def documentation_head() -> str:
    return _head_response()


@router.get("/documentation", response_class=HTMLResponse)
def documentation() -> str:
    return _page(
        "English Tutor AI — Zoom App Documentation",
        """
      <h1>Zoom App Documentation</h1>
      <p class="lead">
        This guide explains how to add, use, configure, and remove the English Tutor AI Zoom integration.
      </p>

      <h2>Add the app</h2>
      <ol>
        <li>Open the Telegram bot: <a href="https://t.me/EnglishTutorHelperAIBot">EnglishTutorHelperAIBot</a>.</li>
        <li>Send <code>/connect_zoom</code>.</li>
        <li>Open the generated Zoom authorization link.</li>
        <li>Approve the requested Zoom permissions.</li>
      </ol>

      <h2>Configure lesson processing</h2>
      <ol>
        <li>In Zoom Web Portal, open Settings → Recording.</li>
        <li>Enable cloud recording.</li>
        <li>Enable audio transcription / create audio transcript.</li>
        <li>In Telegram, send <code>/add_zoom_meeting &lt;Zoom meeting link&gt;</code>.</li>
      </ol>

      <h2>Use the app</h2>
      <p>
        After an added Zoom meeting is completed and Zoom prepares the lesson data, the app receives a
        Zoom webhook and creates a lesson report for the tutor.
      </p>

      <h2>Remove the app</h2>
      <ul>
        <li>Send <code>/disconnect_zoom</code> in Telegram to remove the Zoom connection from the app.</li>
        <li>You can also remove the app from your Zoom account in Zoom Marketplace settings.</li>
      </ul>

      <h2>Data handling</h2>
      <p>
        The app only processes meetings explicitly added by the tutor, does not store video recordings,
        and deletes source lesson data after processing.
      </p>
        """,
    )
