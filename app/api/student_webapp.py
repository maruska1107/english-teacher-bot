from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STYLE = """
:root {
  color-scheme: light;
  --page-bg: #f7f5fa;
  --surface: #ffffff;
  --text: #39344a;
  --muted: #686277;
  --border: #e2deea;
  --primary: #8b86b4;
  --primary-border: #7a75a6;
  --primary-soft: #ece9f2;
  --primary-soft-text: #5c5870;
  --learning-bg: #f0dfd8;
  --learning-text: #75564b;
  --learning-border: #e4ccc2;
  --known-bg: #dcebe2;
  --known-text: #3d644e;
  --known-border: #c8ded1;
  --badge-bg: #e2f0e8;
  --badge-text: #466c56;
  --error-bg: #f6e7e8;
  --error-text: #7a4047;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: var(--page-bg);
  color: var(--text);
}
.page { max-width: 680px; margin: 0 auto; padding: 18px 14px 34px; }
h1 { margin: 4px 0 8px; font-size: 24px; }
.lead { margin: 0 0 16px; color: var(--muted); }
.status { margin: 12px 0; color: var(--muted); }
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin: 16px 0; }
.mode-button, .tab-active {
  background: var(--primary);
  color: #ffffff;
  border-color: var(--primary-border);
}
.secondary-button { background: var(--primary-soft); color: var(--primary-soft-text); border-color: var(--border); }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 14px 0; }
.summary-card, .section-card {
  padding: 14px;
  border-radius: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
}
.summary-card h2, .section-card h2 { margin: 0 0 8px; font-size: 17px; }
.summary-line { margin: 4px 0; color: var(--muted); }
.summary-value { font-weight: 900; color: var(--text); }
@media (max-width: 460px) { .summary-grid { grid-template-columns: 1fr; } }
.study-area { margin-top: 12px; }
.study-progress { margin: 8px 0 14px; color: var(--muted); font-weight: 700; }
.flashcard {
  height: 340px;
  display: grid;
  grid-template-rows: 24px 110px minmax(0, 1fr) 42px;
  align-items: stretch;
  gap: 8px;
  overflow: hidden;
  margin: 14px 0 0;
  padding: 24px 22px;
  border: 1px solid var(--border);
  border-radius: 24px;
  background: var(--surface);
  box-shadow: 0 12px 28px rgba(57, 52, 74, 0.08);
  text-align: center;
  cursor: pointer;
  user-select: none;
}
.flashcard-with-image {
  height: 460px;
  grid-template-rows: 24px 110px 156px minmax(0, 1fr) 42px;
}
.flashcard-image-wrapper {
  min-width: 0;
  overflow: hidden;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.35;
  text-align: left;
}
.flashcard-image {
  display: block;
  width: 100%;
  height: 126px;
  object-fit: cover;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--primary-soft);
}
.flashcard-image-attribution {
  min-height: 22px;
  padding: 4px 2px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.flashcard-image-attribution a { color: var(--primary-soft-text); }
.flashcard-image-wrapper.flashcard-image-failed { visibility: hidden; }
.flashcard-image-failed .flashcard-image { display: none; }
.flashcard-side {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  color: var(--muted);
  font-size: 14px;
  font-weight: 800;
}
.flashcard-main {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  overflow-y: auto;
  color: var(--text);
  font-size: 34px;
  line-height: 1.15;
  font-weight: 900;
}
.flashcard-extra {
  margin: 0;
  overflow-y: auto;
  align-self: stretch;
  font-size: 17px;
  line-height: 1.4;
  color: var(--muted);
}
.reveal-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  font-size: 14px;
  color: var(--muted);
}
.card-list { margin-top: 18px; }
.card-mode-switch { display: flex; gap: 8px; margin: 12px 0; }
.card-mode-switch button { flex: 1; padding: 10px 12px; border-radius: 999px; font-size: 14px; }
.card-mode-tab-active { background: #e7e3f0; color: #5f5980; border-color: #d8d2e5; }
.card-mode-tab { background: #f0edf4; color: #625d70; border-color: var(--border); }
.filter-switch { justify-content: flex-start; margin: 8px 0 6px; }
.filter-switch button { flex: 0 0 auto; padding: 8px 12px; border-radius: 999px; font-size: 13px; }
.filter-chip-active { background: var(--badge-bg); color: var(--badge-text); border-color: var(--known-border); }
.filter-chip { background: #f0edf4; color: #625d70; border-color: var(--border); }
.list-card {
  margin: 10px 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  color: var(--text);
}
.list-card strong { display: block; font-size: 18px; margin-bottom: 4px; }
.list-card .actions { justify-content: flex-end; }
.badge {
  display: inline-block;
  margin-left: 8px;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--badge-bg);
  color: var(--badge-text);
}
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; justify-content: center; }
.study-actions { height: 64px; min-height: 64px; margin-top: 0; align-items: center; }
button {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  font-weight: 800;
  cursor: pointer;
}
.learning { background: var(--learning-bg); color: var(--learning-text); border-color: var(--learning-border); }
.known { background: var(--known-bg); color: var(--known-text); border-color: var(--known-border); }
.empty { padding: 20px; border-radius: 14px; background: var(--badge-bg); color: var(--badge-text); }
.error { padding: 14px; border-radius: 14px; background: var(--error-bg); color: var(--error-text); }
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
const statsEl = document.getElementById("stats");
const navButtons = Array.from(document.querySelectorAll("button[data-section]"));

let allCards = [];
let studyCards = [];
let currentIndex = 0;
let isFlipped = false;
let currentSection = "cards";
let currentCardMode = "study";
let listFilter = "learning";

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
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeHttpsUrl(value) {
  if (!value) return "";
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : "";
  } catch (_error) {
    return "";
  }
}

function attributionHtml(card) {
  const creator = escapeHtml(card.image_creator);
  const sourceUrl = safeHttpsUrl(card.image_source_url);
  const licenseUrl = safeHttpsUrl(card.image_license_url);
  const license = escapeHtml(card.image_license || "лицензия");
  const sourceLink = sourceUrl
    ? `<a class="flashcard-image-source" href="${escapeHtml(sourceUrl)}" target="_blank"`
      + ' rel="noopener noreferrer">источник</a>'
    : '<span class="flashcard-image-source">источник</span>';
  const licenseLink = licenseUrl
    ? `<a class="flashcard-image-license" href="${escapeHtml(licenseUrl)}" target="_blank"`
      + ` rel="noopener noreferrer">${license}</a>`
    : `<span class="flashcard-image-license">${license}</span>`;
  return creator
    ? `Фото: ${creator} · ${sourceLink} · ${licenseLink}`
    : `Фото: ${sourceLink} · ${licenseLink}`;
}

function imageBlock(card) {
  const imageUrl = safeHttpsUrl(card.image_url);
  if (!imageUrl) return "";
  return `
    <div class="flashcard-image-wrapper">
      <img class="flashcard-image" src="${escapeHtml(imageUrl)}" alt="" loading="lazy" referrerpolicy="no-referrer"
           onerror="handleImageError(this)">
      <div class="flashcard-image-attribution">${attributionHtml(card)}</div>
    </div>`;
}

function handleImageError(img) {
  const wrapper = img?.closest(".flashcard-image-wrapper");
  if (!wrapper) return;
  wrapper.classList.add("flashcard-image-failed");
  img.hidden = true;
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
  statsEl.classList.add("hidden");
}

function setActiveSection(section) {
  currentSection = section;
  navButtons.forEach((button) => {
    const isActive = button.dataset.section === section;
    button.className = isActive ? "tab-active" : "secondary-button";
  });
}

function cardModeSwitch() {
  const studyClass = currentCardMode === "study" ? "card-mode-tab-active" : "card-mode-tab";
  const listClass = currentCardMode === "list" ? "card-mode-tab-active" : "card-mode-tab";
  return `
    <div class="card-mode-switch" aria-label="Режим карточек">
      <button type="button" class="${studyClass}" data-card-mode="study">Учить</button>
      <button type="button" class="${listClass}" data-card-mode="list">Список</button>
    </div>`;
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
  setActiveSection("cards");
  studyEl.classList.remove("hidden");
  studyCards = getStudyCards();

  if (!studyCards.length) {
    studyEl.innerHTML = `${cardModeSwitch()}<div class="empty">Все слова уже в категории “Знаю” 🎉</div>`;
    setStatus("Все слова выучены");
    return;
  }

  if (currentIndex >= studyCards.length) {
    currentIndex = 0;
  }
  const card = currentCard();
  const image = imageBlock(card);
  const flashcardClass = image ? "flashcard flashcard-with-image" : "flashcard";
  const sideLabel = isFlipped ? "Перевод" : "English";
  const mainText = isFlipped ? card.translation_ru : card.term;
  const extra = isFlipped
    ? [card.definition_en, card.example_sentence].filter(Boolean).map(escapeHtml).join("<br>")
    : "Нажмите, чтобы перевернуть";
  const actions = isFlipped
    ? `<button class="learning" data-study-progress="learning">Ещё учу</button>
       <button class="known" data-study-progress="known">Знаю</button>`
    : "";

  const revealHint = isFlipped ? "Выберите, насколько хорошо помните слово" : "Сначала вспоминаем перевод сами";
  const newCount = countByStatus("new");
  const newBadge = newCount ? `<span class="badge">Новых слов: +${newCount}</span>` : "";

  studyEl.innerHTML = `
    ${cardModeSwitch()}
    <div class="study-progress">Карточка ${currentIndex + 1} из ${studyCards.length} ${newBadge}</div>
    <article class="${flashcardClass}" data-flashcard data-card-id="${card.id}">
      <p class="flashcard-side">${sideLabel}</p>
      <p class="flashcard-main">${escapeHtml(mainText)}</p>
      ${image}
      <p class="flashcard-extra">${extra || " "}</p>
      <p class="reveal-hint">${revealHint}</p>
    </article>
    <div class="actions study-actions">${actions}</div>`;
  setStatus("");
}

function flipCard() {
  isFlipped = !isFlipped;
  renderStudyCard();
}

function listFilterSwitch() {
  const learningClass = listFilter === "learning" ? "filter-chip-active" : "filter-chip";
  const knownClass = listFilter === "known" ? "filter-chip-active" : "filter-chip";
  return `
    <div class="card-mode-switch filter-switch" aria-label="Фильтр списка">
      <button type="button" class="${learningClass}" data-list-filter="learning">Учу</button>
      <button type="button" class="${knownClass}" data-list-filter="known">Знаю</button>
    </div>`;
}

function getFilteredListCards() {
  if (listFilter === "known") {
    return allCards.filter((card) => card.status === "known");
  }
  return allCards.filter((card) => card.status !== "known");
}

function cardListTemplate(card) {
  const action = card.status === "known"
    ? '<button class="learning" data-list-progress="learning">Повторять</button>'
    : '<button class="known" data-list-progress="known">Знаю</button>';
  return `
    <article class="list-card" data-card-id="${card.id}">
      <strong>${escapeHtml(card.term)}</strong>
      <div>${escapeHtml(card.translation_ru)}</div>
      ${card.example_sentence ? `<div>${escapeHtml(card.example_sentence)}</div>` : ""}
      <div class="actions">${action}</div>
    </article>`;
}

function renderCardList() {
  hideSections();
  setActiveSection("cards");
  studyEl.classList.remove("hidden");
  const cards = getFilteredListCards();
  const listHtml = cards.length
    ? cards.map((card) => cardListTemplate(card)).join("")
    : '<div class="empty">Слов пока нет.</div>';
  studyEl.innerHTML = `
    ${cardModeSwitch()}
    ${listFilterSwitch()}
    <div class="study-progress">Слов: ${cards.length}</div>
    <div class="card-list">${listHtml}</div>`;
  setStatus("");
}

function renderCurrentSection() {
  if (currentSection === "stats") {
    renderStats();
    return;
  }
  if (currentCardMode === "list") {
    renderCardList();
    return;
  }
  renderStudyCard();
}

async function updateProgress(cardId, progress) {
  const result = await api(`/api/student/cards/${cardId}/progress`, {
    method: "POST",
    body: JSON.stringify({ status: progress }),
  });
  allCards = allCards.map((card) => (card.id === Number(cardId) ? { ...card, status: result.status } : card));
  if (currentCardMode === "list") {
    renderCardList();
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
  const modeButton = event.target.closest("button[data-card-mode]");
  if (modeButton) {
    currentCardMode = modeButton.dataset.cardMode;
    currentIndex = 0;
    isFlipped = false;
    renderCurrentSection();
    return;
  }

  const filterButton = event.target.closest("button[data-list-filter]");
  if (filterButton) {
    listFilter = filterButton.dataset.listFilter;
    renderCardList();
    return;
  }

  const listButton = event.target.closest("button[data-list-progress]");
  if (listButton) {
    const cardEl = listButton.closest("[data-card-id]");
    listButton.disabled = true;
    try {
      await updateProgress(cardEl.dataset.cardId, listButton.dataset.listProgress);
    } catch (error) {
      setStatus(`Ошибка: ${error.message}`);
      listButton.disabled = false;
    }
    return;
  }

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

navButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentIndex = 0;
    isFlipped = false;
    currentSection = button.dataset.section;
    if (currentSection === "cards") currentCardMode = "study";
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
    <div class="toolbar" aria-label="Разделы карточек">
      <button type="button" data-section="cards" class="mode-button">Карточки</button>
      <button type="button" data-section="stats" class="secondary-button">Статистика</button>
    </div>
    <div id="status" class="status">Загрузка...</div>
    <section id="study" class="study-area"></section>
    <section id="stats" class="card-list hidden"></section>
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
