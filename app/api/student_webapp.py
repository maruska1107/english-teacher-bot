from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: var(--tg-theme-bg-color, #f7f8fb);
  color: var(--tg-theme-text-color, #111827);
}
.page { max-width: 680px; margin: 0 auto; padding: 18px 14px 34px; }
h1 { margin: 4px 0 8px; font-size: 24px; }
.lead { margin: 0 0 16px; color: var(--tg-theme-hint-color, #6b7280); }
.status { margin: 12px 0; color: var(--tg-theme-hint-color, #6b7280); }
.card {
  margin: 14px 0;
  padding: 20px;
  border: 1px solid var(--tg-theme-section_separator_color, #e5e7eb);
  border-radius: 20px;
  background: var(--tg-theme-secondary-bg-color, #ffffff);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}
.term { margin: 0 0 10px; font-size: 28px; font-weight: 800; }
.translation { margin: 0 0 12px; font-size: 22px; color: #2563eb; }
.example { margin: 0 0 14px; color: var(--tg-theme-hint-color, #4b5563); }
.badge { display: inline-block; padding: 4px 8px; border-radius: 999px; background: #eef2ff; color: #3730a3; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
button {
  border: 0;
  border-radius: 12px;
  padding: 11px 13px;
  font-weight: 800;
  cursor: pointer;
}
.learning { background: #fef3c7; color: #92400e; }
.known { background: var(--tg-theme-button-color, #16a34a); color: var(--tg-theme-button-text-color, #ffffff); }
.empty { padding: 20px; border-radius: 14px; background: #ecfdf5; color: #065f46; }
.error { padding: 14px; border-radius: 14px; background: #fef2f2; color: #991b1b; }
"""

SCRIPT = """
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}
const initData = tg?.initData || "";
const statusEl = document.getElementById("status");
const cardsEl = document.getElementById("cards");

function setStatus(text) {
  statusEl.textContent = text;
}

function headers() {
  return {
    "content-type": "application/json",
    "x-telegram-init-data": initData,
  };
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status}: ${text}`);
  }
  return response.json();
}

function cardTemplate(card) {
  return `
    <article class="card" data-card-id="${card.id}">
      <p class="term">${escapeHtml(card.term)}</p>
      <p class="translation">${escapeHtml(card.translation_ru)}</p>
      ${card.example_sentence ? `<p class="example">${escapeHtml(card.example_sentence)}</p>` : ""}
      <span class="badge" data-status>${escapeHtml(card.status)}</span>
      <div class="actions">
        <button class="learning" data-progress="learning">Учу</button>
        <button class="known" data-progress="known">Знаю</button>
      </div>
    </article>`;
}

async function loadCards() {
  if (!initData) {
    cardsEl.innerHTML = '<div class="error">Откройте эту страницу внутри Telegram WebApp.</div>';
    setStatus("Нет Telegram initData");
    return;
  }
  setStatus("Загружаю карточки...");
  try {
    const data = await api("/api/student/cards");
    if (!data.cards.length) {
      cardsEl.innerHTML = '<div class="empty">Опубликованных карточек пока нет.</div>';
    } else {
      cardsEl.innerHTML = data.cards.map(cardTemplate).join("");
    }
    setStatus(`Карточек: ${data.cards.length}`);
  } catch (error) {
    cardsEl.innerHTML = `<div class="error">Ошибка загрузки: ${escapeHtml(error.message)}</div>`;
    setStatus("Ошибка");
  }
}

cardsEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-progress]");
  if (!button) return;
  const cardEl = button.closest("[data-card-id]");
  const cardId = cardEl.dataset.cardId;
  const progress = button.dataset.progress;
  button.disabled = true;
  try {
    const result = await api(`/api/student/cards/${cardId}/progress`, {
      method: "POST",
      body: JSON.stringify({ status: progress }),
    });
    cardEl.querySelector("[data-status]").textContent = result.status;
    setStatus(progress === "known" ? "Отмечено как известно" : "Отмечено как изучается");
  } catch (error) {
    setStatus(`Ошибка: ${error.message}`);
  } finally {
    button.disabled = false;
  }
});

loadCards();
"""


def _page() -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>English Tutor AI — мои карточки</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>{STYLE}</style>
</head>
<body>
  <main class="page">
    <h1>Мои карточки</h1>
    <p class="lead">Повторяйте слова после уроков и отмечайте прогресс.</p>
    <div id="status" class="status">Загрузка...</div>
    <section id="cards"></section>
  </main>
  <script>{SCRIPT}</script>
</body>
</html>"""


@router.head("/student/cards", response_class=HTMLResponse)
def student_cards_webapp_head() -> str:
    return ""


@router.get("/student/cards", response_class=HTMLResponse)
def student_cards_webapp() -> str:
    return _page()
