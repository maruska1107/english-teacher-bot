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
.page { max-width: 760px; margin: 0 auto; padding: 18px 14px 34px; }
h1 { margin: 4px 0 8px; font-size: 24px; }
.lead { margin: 0 0 16px; color: var(--tg-theme-hint-color, #6b7280); }
.status { margin: 12px 0; color: var(--tg-theme-hint-color, #6b7280); }
.card {
  margin: 12px 0;
  padding: 14px;
  border: 1px solid var(--tg-theme-section_separator_color, #e5e7eb);
  border-radius: 16px;
  background: var(--tg-theme-secondary-bg-color, #ffffff);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}
label { display: block; margin: 10px 0 4px; font-size: 13px; color: var(--tg-theme-hint-color, #6b7280); }
input, textarea {
  width: 100%;
  padding: 10px 11px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  font: inherit;
  background: #ffffff;
  color: #111827;
}
textarea { min-height: 68px; resize: vertical; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
button {
  border: 0;
  border-radius: 11px;
  padding: 10px 12px;
  font-weight: 700;
  cursor: pointer;
}
.primary { background: var(--tg-theme-button-color, #2563eb); color: var(--tg-theme-button-text-color, #ffffff); }
.secondary { background: #eef2ff; color: #3730a3; }
.danger { background: #fee2e2; color: #991b1b; }
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
      <label>Слово / фраза</label>
      <input name="term" value="${escapeHtml(card.term)}">
      <label>Перевод</label>
      <input name="translation_ru" value="${escapeHtml(card.translation_ru)}">
      <label>Определение на английском</label>
      <textarea name="definition_en">${escapeHtml(card.definition_en)}</textarea>
      <label>Пример</label>
      <textarea name="example_sentence">${escapeHtml(card.example_sentence)}</textarea>
      <label>Фраза из урока</label>
      <textarea name="source_phrase">${escapeHtml(card.source_phrase)}</textarea>
      <label>Уровень</label>
      <input name="level" value="${escapeHtml(card.level)}">
      <div class="actions">
        <button class="secondary" data-action="save">Сохранить</button>
        <button class="primary" data-action="publish">Опубликовать</button>
        <button class="danger" data-action="archive">Архивировать</button>
      </div>
    </article>`;
}

function payloadFromCard(cardEl) {
  return Object.fromEntries(
    ["term", "translation_ru", "definition_en", "example_sentence", "source_phrase", "level"].map((field) => [
      field,
      cardEl.querySelector(`[name="${field}"]`).value,
    ])
  );
}

async function loadCards() {
  if (!initData) {
    cardsEl.innerHTML = '<div class="error">Откройте эту страницу внутри Telegram WebApp.</div>';
    setStatus("Нет Telegram initData");
    return;
  }
  setStatus("Загружаю draft-карточки...");
  try {
    const data = await api("/api/teacher/cards?status=draft");
    if (!data.cards.length) {
      cardsEl.innerHTML = '<div class="empty">Draft-карточек пока нет.</div>';
    } else {
      cardsEl.innerHTML = data.cards.map(cardTemplate).join("");
    }
    setStatus(`Draft-карточек: ${data.cards.length}`);
  } catch (error) {
    cardsEl.innerHTML = `<div class="error">Ошибка загрузки: ${escapeHtml(error.message)}</div>`;
    setStatus("Ошибка");
  }
}

cardsEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const cardEl = button.closest("[data-card-id]");
  const cardId = cardEl.dataset.cardId;
  const action = button.dataset.action;
  button.disabled = true;
  try {
    if (action === "save") {
      await api(`/api/teacher/cards/${cardId}`, {
        method: "PATCH",
        body: JSON.stringify(payloadFromCard(cardEl)),
      });
      setStatus("Сохранено");
    }
    if (action === "publish") {
      await api(`/api/teacher/cards/${cardId}/publish`, { method: "POST" });
      cardEl.remove();
      setStatus("Карточка опубликована");
    }
    if (action === "archive") {
      await api(`/api/teacher/cards/${cardId}/archive`, { method: "POST" });
      cardEl.remove();
      setStatus("Карточка архивирована");
    }
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
  <title>English Tutor AI — карточки</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>{STYLE}</style>
</head>
<body>
  <main class="page">
    <h1>Карточки к урокам</h1>
    <p class="lead">Проверьте draft-карточки, исправьте текст и опубликуйте для учеников.</p>
    <div id="status" class="status">Загрузка...</div>
    <section id="cards"></section>
  </main>
  <script>{SCRIPT}</script>
</body>
</html>"""


@router.head("/teacher/cards", response_class=HTMLResponse)
def teacher_cards_webapp_head() -> str:
    return ""


@router.get("/teacher/cards", response_class=HTMLResponse)
def teacher_cards_webapp() -> str:
    return _page()
