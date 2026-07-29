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
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0; }
.mode-button {
  background: var(--tg-theme-button-color, #2563eb);
  color: var(--tg-theme-button-text-color, #ffffff);
}
.secondary-button { background: #e5e7eb; color: #111827; }
.study-area { margin-top: 12px; }
.study-progress { margin: 8px 0 14px; color: var(--tg-theme-hint-color, #6b7280); font-weight: 700; }
.flashcard {
  min-height: 270px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  margin: 14px 0;
  padding: 28px 22px;
  border: 1px solid var(--tg-theme-section_separator_color, #e5e7eb);
  border-radius: 24px;
  background: var(--tg-theme-secondary-bg-color, #ffffff);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.10);
  text-align: center;
  cursor: pointer;
  user-select: none;
}
.flashcard-side { margin: 0; color: var(--tg-theme-hint-color, #6b7280); font-size: 14px; font-weight: 800; }
.flashcard-main { margin: 0; font-size: 34px; line-height: 1.15; font-weight: 900; }
.flashcard-extra { margin: 0; font-size: 17px; line-height: 1.4; color: var(--tg-theme-hint-color, #4b5563); }
.reveal-hint { margin: 0; font-size: 14px; color: var(--tg-theme-hint-color, #6b7280); }
.card-list { margin-top: 18px; }
.list-card {
  margin: 10px 0;
  padding: 14px;
  border: 1px solid var(--tg-theme-section_separator_color, #e5e7eb);
  border-radius: 16px;
  background: var(--tg-theme-secondary-bg-color, #ffffff);
}
.list-card strong { display: block; font-size: 18px; margin-bottom: 4px; }
.badge {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #eef2ff;
  color: #3730a3;
}
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; justify-content: center; }
button {
  border: 0;
  border-radius: 12px;
  padding: 12px 14px;
  font-weight: 800;
  cursor: pointer;
}
.unknown { background: #fee2e2; color: #991b1b; }
.learning { background: #fef3c7; color: #92400e; }
.known { background: var(--tg-theme-button-color, #16a34a); color: var(--tg-theme-button-text-color, #ffffff); }
.empty { padding: 20px; border-radius: 14px; background: #ecfdf5; color: #065f46; }
.error { padding: 14px; border-radius: 14px; background: #fef2f2; color: #991b1b; }
.hidden { display: none; }
"""

SCRIPT = """
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}
const initData = tg?.initData || "";
const statusEl = document.getElementById("status");
const studyEl = document.getElementById("study");
const listEl = document.getElementById("cards");
const startStudyButton = document.getElementById("start-study");
const showAllButton = document.getElementById("show-all");

let allCards = [];
let studyCards = [];
let currentIndex = 0;
let isFlipped = false;

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

function getStudyCards() {
  return allCards.filter((card) => card.status !== "known");
}

function currentCard() {
  return studyCards[currentIndex];
}

function renderStudyCard() {
  listEl.classList.add("hidden");
  studyEl.classList.remove("hidden");
  studyCards = getStudyCards();

  if (!studyCards.length) {
    studyEl.innerHTML = '<div class="empty">Все карточки уже в категории “Знаю” 🎉</div>';
    setStatus("Все карточки выучены");
    return;
  }

  if (currentIndex >= studyCards.length) {
    currentIndex = 0;
  }
  const card = currentCard();
  const sideLabel = isFlipped ? "Перевод" : "English";
  const mainText = isFlipped ? card.translation_ru : card.term;
  const extra = isFlipped
    ? [card.definition_en, card.example_sentence].filter(Boolean).join("<br>")
    : "Нажмите, чтобы перевернуть";
  const actions = isFlipped
    ? `<div class="actions">
        <button class="unknown" data-study-progress="learning">Не знаю</button>
        <button class="learning" data-study-progress="learning">Ещё учу</button>
        <button class="known" data-study-progress="known">Знаю</button>
      </div>`
    : "";

  const revealHint = isFlipped ? "Выберите, насколько хорошо помните слово" : "Сначала вспоминаем перевод сами";

  studyEl.innerHTML = `
    <div class="study-progress">Карточка ${currentIndex + 1} из ${studyCards.length}</div>
    <article class="flashcard" data-flashcard data-card-id="${card.id}">
      <p class="flashcard-side">${sideLabel}</p>
      <p class="flashcard-main">${escapeHtml(mainText)}</p>
      <p class="flashcard-extra">${extra || " "}</p>
      <p class="reveal-hint">${revealHint}</p>
    </article>
    ${actions}`;
  setStatus(`К изучению: ${studyCards.length}`);
}

function flipCard() {
  isFlipped = !isFlipped;
  renderStudyCard();
}

function listCardTemplate(card) {
  return `
    <article class="list-card" data-card-id="${card.id}">
      <strong>${escapeHtml(card.term)}</strong>
      <div>${escapeHtml(card.translation_ru)}</div>
      ${card.example_sentence ? `<div>${escapeHtml(card.example_sentence)}</div>` : ""}
      <span class="badge">${escapeHtml(card.status)}</span>
    </article>`;
}

function renderList() {
  studyEl.classList.add("hidden");
  listEl.classList.remove("hidden");
  if (!allCards.length) {
    listEl.innerHTML = '<div class="empty">Опубликованных карточек пока нет.</div>';
  } else {
    listEl.innerHTML = allCards.map(listCardTemplate).join("");
  }
  setStatus(`Карточек: ${allCards.length}`);
}

async function updateProgress(cardId, progress) {
  const result = await api(`/api/student/cards/${cardId}/progress`, {
    method: "POST",
    body: JSON.stringify({ status: progress }),
  });
  allCards = allCards.map((card) => (card.id === Number(cardId) ? { ...card, status: result.status } : card));
  if (progress === "known") {
    studyCards = getStudyCards();
  } else {
    currentIndex += 1;
  }
  isFlipped = false;
  renderStudyCard();
}

async function loadCards() {
  if (!initData) {
    studyEl.innerHTML = '<div class="error">Откройте эту страницу внутри Telegram WebApp.</div>';
    setStatus("Нет Telegram initData");
    return;
  }
  setStatus("Загружаю карточки...");
  try {
    const data = await api("/api/student/cards");
    allCards = data.cards;
    currentIndex = 0;
    isFlipped = false;
    renderStudyCard();
  } catch (error) {
    studyEl.innerHTML = `<div class="error">Ошибка загрузки: ${escapeHtml(error.message)}</div>`;
    setStatus("Ошибка");
  }
}

studyEl.addEventListener("click", async (event) => {
  const progressButton = event.target.closest("button[data-study-progress]");
  if (progressButton) {
    const card = currentCard();
    if (!card) return;
    progressButton.disabled = true;
    try {
      await updateProgress(card.id, progressButton.dataset.studyProgress);
    } catch (error) {
      setStatus(`Ошибка: ${error.message}`);
      progressButton.disabled = false;
    }
    return;
  }
  if (event.target.closest("[data-flashcard]")) {
    flipCard();
  }
});

startStudyButton.addEventListener("click", () => {
  currentIndex = 0;
  isFlipped = false;
  renderStudyCard();
});

showAllButton.addEventListener("click", renderList);

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
    <p class="lead">Повторяйте слова после уроков: сначала английское слово, потом переворот и ответ.</p>
    <div class="toolbar">
      <button id="start-study" class="mode-button">Режим заучивания</button>
      <button id="show-all" class="secondary-button">Все карточки</button>
    </div>
    <div id="status" class="status">Загрузка...</div>
    <section id="study" class="study-area"></section>
    <section id="cards" class="card-list hidden"></section>
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
