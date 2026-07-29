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
.mode-button, .tab-active {
  background: var(--tg-theme-button-color, #2563eb);
  color: var(--tg-theme-button-text-color, #ffffff);
}
.secondary-button { background: #e5e7eb; color: #111827; }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 0; }
.summary-card, .section-card {
  padding: 14px;
  border-radius: 18px;
  background: var(--tg-theme-secondary-bg-color, #ffffff);
  border: 1px solid var(--tg-theme-section_separator_color, #e5e7eb);
}
.summary-card h2, .section-card h2 { margin: 0 0 8px; font-size: 17px; }
.summary-line { margin: 4px 0; color: var(--tg-theme-hint-color, #4b5563); }
.summary-value { font-weight: 900; color: var(--tg-theme-text-color, #111827); }
@media (max-width: 460px) { .summary-grid { grid-template-columns: 1fr; } }
.study-area { margin-top: 12px; }
.study-progress { margin: 8px 0 14px; color: var(--tg-theme-hint-color, #6b7280); font-weight: 700; }
.flashcard {
  min-height: 340px;
  max-height: 340px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  overflow-y: auto;
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
const unlearnedEl = document.getElementById("unlearned");
const statsEl = document.getElementById("stats");
const listEl = document.getElementById("cards");
const navButtons = Array.from(document.querySelectorAll("button[data-section]"));

let allCards = [];
let studyCards = [];
let currentIndex = 0;
let isFlipped = false;
let currentSection = "study";

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

function cardsByStatus(status) {
  return allCards.filter((card) => card.status === status);
}

function currentCard() {
  return studyCards[currentIndex];
}

function countByStatus(status) {
  return cardsByStatus(status).length;
}

function hideSections() {
  studyEl.classList.add("hidden");
  unlearnedEl.classList.add("hidden");
  statsEl.classList.add("hidden");
  listEl.classList.add("hidden");
}

function setActiveSection(section) {
  currentSection = section;
  navButtons.forEach((button) => {
    const isActive = button.dataset.section === section;
    button.className = isActive ? "tab-active" : "secondary-button";
  });
}

function renderStats() {
  hideSections();
  setActiveSection("stats");
  statsEl.classList.remove("hidden");

  const total = allCards.length;
  const known = countByStatus("known");
  const learning = countByStatus("learning");
  const newCount = countByStatus("new");
  const leftToStudy = total - known;
  const knownPercent = total ? Math.round((known / total) * 100) : 0;

  statsEl.innerHTML = `
    <section class="summary-grid" aria-label="Прогресс ученика">
      <article class="summary-card">
        <h2>Мой прогресс</h2>
        <p class="summary-line">Всего: <span class="summary-value">${total}</span></p>
        <p class="summary-line">Знаю: <span class="summary-value">${known}</span></p>
        <p class="summary-line">Учу: <span class="summary-value">${learning}</span></p>
        <p class="summary-line">Новые: <span class="summary-value">${newCount}</span></p>
        <p class="summary-line">Осталось учить: <span class="summary-value">${leftToStudy}</span></p>
        <p class="summary-line">Выучено: <span class="summary-value">${knownPercent}%</span></p>
      </article>
    </section>`;
  setStatus("Статистика");
}

function renderStudyCard() {
  hideSections();
  setActiveSection("study");
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

function listCardTemplate(card, listAction = true) {
  const action = card.status === "known"
    ? '<button class="learning" data-list-progress="learning">Учить</button>'
    : '<button class="known" data-list-progress="known">Знаю</button>';
  return `
    <article class="list-card" data-card-id="${card.id}">
      <strong>${escapeHtml(card.term)}</strong>
      <div>${escapeHtml(card.translation_ru)}</div>
      ${card.example_sentence ? `<div>${escapeHtml(card.example_sentence)}</div>` : ""}
      <span class="badge">${escapeHtml(card.status)}</span>
      ${listAction ? `<div class="actions">${action}</div>` : ""}
    </article>`;
}

function renderCardGroup(title, cards) {
  const content = cards.length
    ? cards.map((card) => listCardTemplate(card, false)).join("")
    : '<div class="empty">Пока пусто.</div>';
  return `
    <section class="section-card">
      <h2>${title}</h2>
      ${content}
    </section>`;
}

function renderUnlearned() {
  hideSections();
  setActiveSection("unlearned");
  unlearnedEl.classList.remove("hidden");

  const newCards = cardsByStatus("new");
  const learningCards = cardsByStatus("learning");
  unlearnedEl.innerHTML = `
    ${renderCardGroup("Новые от преподавателя", newCards)}
    ${renderCardGroup("Уже в изучении", learningCards)}
    <div class="actions">
      <button class="mode-button" data-action="study-unlearned">Учить эти слова</button>
    </div>`;
  setStatus(`Неизученных карточек: ${newCards.length + learningCards.length}`);
}

function renderList() {
  hideSections();
  setActiveSection("all");
  listEl.classList.remove("hidden");
  if (!allCards.length) {
    listEl.innerHTML = '<div class="empty">Опубликованных карточек пока нет.</div>';
  } else {
    listEl.innerHTML = allCards.map((card) => listCardTemplate(card)).join("");
  }
  setStatus(`Карточек: ${allCards.length}`);
}

function renderCurrentSection() {
  if (currentSection === "unlearned") {
    renderUnlearned();
    return;
  }
  if (currentSection === "stats") {
    renderStats();
    return;
  }
  if (currentSection === "all") {
    renderList();
    return;
  }
  renderStudyCard();
}

async function updateProgress(cardId, progress, after = "study") {
  const result = await api(`/api/student/cards/${cardId}/progress`, {
    method: "POST",
    body: JSON.stringify({ status: progress }),
  });
  allCards = allCards.map((card) => (card.id === Number(cardId) ? { ...card, status: result.status } : card));
  if (after === "list") {
    renderList();
    setStatus(progress === "known" ? "Отмечено как известно" : "Возвращено в режим заучивания");
    return;
  }
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

listEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-list-progress]");
  if (!button) return;
  const cardEl = button.closest("[data-card-id]");
  const cardId = cardEl.dataset.cardId;
  button.disabled = true;
  try {
    await updateProgress(cardId, button.dataset.listProgress, "list");
  } catch (error) {
    setStatus(`Ошибка: ${error.message}`);
    button.disabled = false;
  }
});

unlearnedEl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action='study-unlearned']");
  if (!button) return;
  currentIndex = 0;
  isFlipped = false;
  renderStudyCard();
});

navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentIndex = 0;
    isFlipped = false;
    currentSection = button.dataset.section;
    renderCurrentSection();
  });
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
    <p class="lead">Повторяйте слова после уроков: английское слово, переворот и ответ.</p>
    <div class="toolbar" aria-label="Разделы карточек">
      <button type="button" data-section="study" class="mode-button">Учить</button>
      <button type="button" data-section="unlearned" class="secondary-button">Неизученное</button>
      <button type="button" data-section="stats" class="secondary-button">Статистика</button>
      <button type="button" data-section="all" class="secondary-button">Все карточки</button>
    </div>
    <div id="status" class="status">Загрузка...</div>
    <section id="study" class="study-area"></section>
    <section id="unlearned" class="card-list hidden"></section>
    <section id="stats" class="card-list hidden"></section>
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
