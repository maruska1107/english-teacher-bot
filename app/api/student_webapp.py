# ruff: noqa: E501
import base64
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
CARD_UI_SCRIPT = (STATIC_DIR / "student_card_ui.js").read_text(encoding="utf-8")


def _asset_data_uri(filename: str) -> str:
    data = (STATIC_DIR / "assets" / filename).read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{encoded}"


MASCOT_AVATAR_SRC = _asset_data_uri("tutorhelper-cat-avatar.png")
MASCOT_LOUNGE_SRC = _asset_data_uri("tutorhelper-cat-lounge.png")

STYLE = """
:root {
  color-scheme: light;
  --page-bg: #fbf9fc;
  --surface: #ffffff;
  --surface-tint: #f7f1fb;
  --text: #191438;
  --muted: #7c758d;
  --border: #ebe6f0;
  --primary: #7664b7;
  --primary-dark: #5f4da2;
  --primary-soft: #f0eafd;
  --primary-soft-text: #6c5aa8;
  --learning-bg: #fff7df;
  --learning-text: #6f5a19;
  --learning-border: #f3e6bd;
  --known-bg: #eaf8f0;
  --known-text: #317753;
  --known-border: #d2eddd;
  --danger-soft: #fff0f3;
  --badge-bg: #ddf5ec;
  --badge-text: #2c8765;
  --error-bg: #fff0f3;
  --error-text: #9b4659;
  --shadow: 0 18px 44px rgba(42, 31, 83, 0.10);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background:
    radial-gradient(circle at 18% 8%, rgba(237, 229, 255, 0.75), transparent 32%),
    radial-gradient(circle at 82% 18%, rgba(255, 235, 214, 0.60), transparent 26%),
    var(--page-bg);
  color: var(--text);
}
.page {
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 26px 18px 104px;
  position: relative;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin: 2px 0 28px;
}
.brand {
  margin: 0;
  color: var(--text);
  font-size: 32px;
  line-height: 1;
  letter-spacing: -1.4px;
  font-weight: 950;
}
.cat-avatar {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border-radius: 999px;
  overflow: hidden;
  background: #d8c9fb;
  border: 1px solid #ded3f0;
  box-shadow: 0 8px 18px rgba(118, 100, 183, 0.18);
}
.cat-avatar-img { width: 100%; height: 100%; display: block; object-fit: cover; }
.ui-icon {
  width: 22px;
  height: 22px;
  display: inline-block;
  flex: 0 0 auto;
  vertical-align: -5px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.button-icon { display: block; margin: 0 auto 5px; }
.inline-icon { width: 18px; height: 18px; vertical-align: -3px; }
.section-title {
  margin: 0 0 16px;
  font-size: 28px;
  line-height: 1.05;
  letter-spacing: -0.8px;
  font-weight: 950;
}
.status {
  min-height: 20px;
  margin: 8px 0 2px;
  color: var(--muted);
  font-size: 14px;
  font-weight: 750;
}
.toolbar {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 14px;
}
.mode-button, .tab-active {
  background: linear-gradient(180deg, #806cc1, var(--primary));
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 10px 20px rgba(118, 100, 183, 0.22);
}
.secondary-button {
  background: rgba(255, 255, 255, 0.92);
  color: #625d70;
  border-color: var(--border);
}
button {
  min-height: 52px;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 15px;
  font-weight: 850;
  cursor: pointer;
  transition: transform 120ms ease, box-shadow 120ms ease, background 120ms ease;
}
button:active { transform: translateY(1px) scale(0.99); }
button:focus-visible { outline: 3px solid rgba(118, 100, 183, 0.34); outline-offset: 2px; }
.study-area, .card-list { margin-top: 8px; }
.card-mode-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  margin: 14px 0 18px;
  padding: 4px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
}
.card-mode-switch button {
  min-height: 42px;
  border-radius: 12px;
  border: 0;
  font-size: 15px;
}
.card-mode-tab-active {
  background: linear-gradient(180deg, #806cc1, var(--primary));
  color: #ffffff;
  box-shadow: 0 8px 16px rgba(118, 100, 183, 0.22);
}
.card-mode-tab { background: transparent; color: #6c6678; }
.filter-switch {
  grid-template-columns: repeat(2, max-content);
  justify-content: flex-start;
  gap: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.filter-switch button {
  min-height: 38px;
  padding: 8px 13px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 13px;
}
.filter-chip-active { background: var(--badge-bg); color: var(--badge-text); border-color: var(--known-border); }
.filter-chip { background: #ffffff; color: #625d70; }
.study-meta {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
}
.study-progress { color: #6c6678; font-size: 15px; font-weight: 850; }
.progress-track {
  height: 5px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #e8e5ed;
}
.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--primary), #b09be9);
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 11px 13px;
  border-radius: 16px;
  background: var(--badge-bg);
  color: var(--badge-text);
  font-size: 13px;
  font-weight: 900;
  white-space: nowrap;
}
.flashcard {
  min-height: 430px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 14px;
  margin: 0;
  padding: 26px 20px 18px;
  border: 2px solid #e2d7fb;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow), inset 0 0 0 1px rgba(255,255,255,0.85);
  text-align: center;
  cursor: pointer;
  user-select: none;
}
.flashcard-with-image { min-height: 522px; }
.flashcard:focus-visible { outline: 4px solid rgba(118, 100, 183, 0.30); outline-offset: 4px; }
.flashcard-head {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) 44px;
  align-items: center;
  gap: 8px;
}
.flashcard-side {
  grid-column: 2;
  margin: 0;
  color: var(--primary);
  font-size: 16px;
  font-weight: 950;
}

.flashcard-main {
  margin: 0;
  color: var(--text);
  font-size: clamp(38px, 12vw, 52px);
  line-height: 1.02;
  letter-spacing: -1.2px;
  font-weight: 950;
  overflow-wrap: anywhere;
}
.flashcard-image-wrapper {
  display: grid;
  grid-template-rows: 210px auto;
  min-width: 0;
  overflow: hidden;
  color: var(--muted);
  font-size: 10px;
  line-height: 1.35;
  text-align: left;
}
.flashcard-image-region { position: relative; height: 210px; }
.flashcard-image {
  display: block;
  width: 100%;
  height: 210px;
  object-fit: cover;
  border: 0;
  border-radius: 16px;
  background: var(--primary-soft);
  box-shadow: inset 0 0 0 1px rgba(42,31,83,0.05);
}
.flashcard-image-attribution {
  max-height: 42px;
  padding: 6px 2px 0;
  overflow-x: hidden;
  overflow-y: auto;
  overflow-wrap: anywhere;
  white-space: normal;
  user-select: text;
  color: #8f879d;
}
.flashcard-image-attribution a { color: var(--primary-soft-text); }
.flashcard-image-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: var(--primary-soft);
  color: var(--primary-soft-text);
  font-size: 14px;
  font-weight: 850;
  text-align: center;
}
.flashcard-image-placeholder[hidden], .flashcard-image-failed .flashcard-image { display: none; }
.flashcard-extra {
  margin: 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.45;
  font-weight: 650;
}
.flashcard-sentence {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: auto;
  color: var(--text);
  font-size: 20px;
  line-height: 1.28;
  font-weight: 850;
}
.flip-hint { margin-top: -6px; color: #aaa3b5; font-size: 14px; font-weight: 750; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; justify-content: center; }
.study-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  min-height: 82px;
  align-items: stretch;
}
.study-actions button {
  min-height: 72px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  border-radius: 16px;
  line-height: 1.12;
}
.study-actions small { display: block; color: rgba(80,72,95,0.70); font-size: 12px; font-weight: 750; }
.learning { background: var(--learning-bg); color: var(--learning-text); border-color: var(--learning-border); }
.known { background: var(--known-bg); color: var(--known-text); border-color: var(--known-border); }
.cat-note {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  align-items: end;
  gap: 10px;
  margin: 12px 0 2px;
}
.cat-mascot {
  width: 98px;
  height: 66px;
  align-self: end;
  filter: drop-shadow(0 9px 12px rgba(118, 100, 183, 0.18));
}
.cat-mascot-img { width: 100%; height: 100%; display: block; object-fit: contain; }
.cat-bubble {
  align-self: center;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgba(42,31,83,0.06);
}
.cat-bubble strong { display: block; margin-bottom: 4px; font-size: 15px; }
.cat-bubble span { color: var(--muted); font-size: 13px; font-weight: 650; }
.card-list { margin-top: 18px; }
.list-card, .homework-card, .summary-card, .section-card {
  margin: 10px 0;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: rgba(255,255,255,0.94);
  box-shadow: 0 8px 24px rgba(42,31,83,0.05);
  color: var(--text);
}
.list-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}
.list-card strong { display: block; margin-bottom: 5px; font-size: 19px; letter-spacing: -0.2px; }
.list-card p { margin: 3px 0 0; color: var(--muted); line-height: 1.35; }
.list-card .actions { margin: 0; justify-content: flex-end; }
.list-card button { min-height: 42px; padding: 9px 12px; border-radius: 12px; font-size: 13px; }
.summary-grid { display: grid; grid-template-columns: 1fr; gap: 10px; margin: 14px 0; }
.summary-card h2, .section-card h2 { margin: 0 0 12px; font-size: 22px; letter-spacing: -0.4px; }
.summary-line { margin: 8px 0; color: var(--muted); font-weight: 750; }
.summary-value { font-size: 24px; font-weight: 950; color: var(--primary); }
.homework-card h2 { margin: 0 0 8px; font-size: 22px; letter-spacing: -0.4px; }
.homework-date { margin: 0 0 14px; color: var(--muted); font-weight: 850; }
.homework-block { margin: 14px 0; }
.homework-block h3 { margin: 0 0 7px; font-size: 16px; }
.homework-block p { margin: 0; color: var(--muted); line-height: 1.48; white-space: pre-wrap; }
.homework-list { margin: 8px 0 0; padding: 0; list-style: none; }
.homework-list li { margin: 8px 0; color: var(--text); font-weight: 720; }
.homework-list li::before { content: "•"; margin-right: 8px; color: var(--primary); font-weight: 950; }
.homework-actions { justify-content: flex-start; }
.homework-previous { background: rgba(255,255,255,0.72); }
.empty {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--badge-bg);
  color: var(--badge-text);
  font-weight: 850;
}
.error { padding: 14px; border-radius: 16px; background: var(--error-bg); color: var(--error-text); }
.bottom-nav {
  position: fixed;
  left: 50%;
  bottom: 0;
  z-index: 20;
  width: min(430px, 100%);
  transform: translateX(-50%);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
  padding: 12px 18px calc(12px + env(safe-area-inset-bottom));
  border: 1px solid var(--border);
  border-bottom: 0;
  border-radius: 26px 26px 0 0;
  background: rgba(255,255,255,0.96);
  box-shadow: 0 -8px 24px rgba(42,31,83,0.08);
  backdrop-filter: blur(14px);
}
.bottom-nav button {
  min-height: 56px;
  padding: 7px 4px;
  border: 0;
  border-radius: 16px;
  background: transparent;
  color: #686277;
  box-shadow: none;
  font-size: 12px;
}
.bottom-nav .tab-active {
  background: transparent;
  color: var(--primary);
  box-shadow: none;
}
.nav-icon { display: block; margin-bottom: 3px; line-height: 1; }
.nav-icon .ui-icon { width: 25px; height: 25px; }
.hidden { display: none; }
@media (max-width: 360px) {
  .page { padding-left: 12px; padding-right: 12px; }
  .brand { font-size: 28px; }
  .section-title { font-size: 25px; }
  .toolbar button { font-size: 13px; padding: 10px 8px; }
  .flashcard { padding-left: 15px; padding-right: 15px; }
}
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
const homeworkEl = document.getElementById("homework");
const navButtons = Array.from(document.querySelectorAll("button[data-section]"));

let allCards = [];
let homeworkItems = [];
let homeworkLoaded = false;
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
  homeworkEl.classList.add("hidden");
}

function sectionClasses(button, isActive) {
  if (button.closest(".bottom-nav")) {
    return isActive ? "tab-active" : "secondary-button";
  }
  return isActive ? "tab-active" : "secondary-button";
}

function setActiveSection(section) {
  currentSection = section;
  navButtons.forEach((button) => {
    const isActive = button.dataset.section === section;
    button.className = sectionClasses(button, isActive);
  });
}

function iconSvg(name) {
  const icons = {
    cards: '<rect x="5" y="4" width="14" height="16" rx="3"></rect><path d="M9 9h6"></path><path d="M9 13h6"></path><path d="M12 17l2-2 2 2"></path>',
    homework: '<path d="M6 19h12"></path><path d="M7 15.5 16.5 6 20 9.5 10.5 19 6 20z"></path><path d="M14.5 8 18 11.5"></path>',
    stats: '<path d="M5 19V12"></path><path d="M12 19V5"></path><path d="M19 19V9"></path><path d="M4 19h16"></path>',
    learn: '<path d="M4 8 12 4l8 4-8 4z"></path><path d="M7 10.5V15c2.5 2 7.5 2 10 0v-4.5"></path><path d="M20 8v5"></path>',
    list: '<path d="M9 6h11"></path><path d="M9 12h11"></path><path d="M9 18h11"></path><path d="M4 6h.01"></path><path d="M4 12h.01"></path><path d="M4 18h.01"></path>',
    words: '<path d="M5 5h10a4 4 0 0 1 4 4v10H9a4 4 0 0 0-4 4z"></path><path d="M5 5v18"></path><path d="M9 9h6"></path><path d="M9 13h5"></path>',
    paw: '<path d="M8.5 11.5c-2.5 1.3-3.8 3.8-2.4 5.6 1.2 1.5 3.2.5 5.9.5s4.7 1 5.9-.5c1.4-1.8.1-4.3-2.4-5.6-1.4-.8-2.4.8-3.5.8s-2.1-1.6-3.5-.8z"></path><path d="M6.5 8.5c.8 0 1.4-.8 1.4-1.8S7.3 5 6.5 5 5.1 5.8 5.1 6.7s.6 1.8 1.4 1.8z"></path><path d="M11 7.2c.9 0 1.6-.9 1.6-2S11.9 3 11 3s-1.6.9-1.6 2.1.7 2.1 1.6 2.1z"></path><path d="M17.5 8.5c.8 0 1.4-.8 1.4-1.8S18.3 5 17.5 5s-1.4.8-1.4 1.7.6 1.8 1.4 1.8z"></path>',
    spark: '<path d="M12 3l1.6 5.1L19 10l-5.4 1.9L12 17l-1.6-5.1L5 10l5.4-1.9z"></path>',
  };
  return `<svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || ""}</svg>`;
}

function cardModeSwitch() {
  const studyClass = currentCardMode === "study" ? "card-mode-tab-active" : "card-mode-tab";
  const listClass = currentCardMode === "list" ? "card-mode-tab-active" : "card-mode-tab";
  return `
    <div class="card-mode-switch" aria-label="Режим карточек">
      <button type="button" class="${studyClass}" data-card-mode="study">${iconSvg("learn")} Учить</button>
      <button type="button" class="${listClass}" data-card-mode="list">${iconSvg("list")} Список</button>
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
        <h2>${iconSvg("stats")} Котостатистика ⓘ</h2>
        <p class="summary-line">${iconSvg("paw")} знаю <span class="summary-value">${known}</span></p>
        <p class="summary-line">${iconSvg("words")} повторить <span class="summary-value">${learning}</span></p>
        <p class="summary-line">${iconSvg("cards")} новые <span class="summary-value">${newCount}</span></p>
        <p class="summary-line">Всего слов: <span class="summary-value">${total}</span></p>
        <p class="summary-line">Осталось учить: <span class="summary-value">${leftToStudy}</span></p>
        <p class="summary-line">Выучено: <span class="summary-value">${knownPercent}%</span></p>
      </article>
    </section>`;
  setStatus("Прогресс");
}

function studyProgressPercent() {
  if (!studyCards.length) return 0;
  return Math.max(6, Math.round(((currentIndex + 1) / studyCards.length) * 100));
}

function renderStudyCard() {
  hideSections();
  setActiveSection("cards");
  studyEl.classList.remove("hidden");
  studyCards = getStudyCards();

  if (!studyCards.length) {
    studyEl.innerHTML = `${cardModeSwitch()}<div class="empty">Все слова уже в категории “Знаю”</div>`;
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
  const sentence = isFlipped
    ? [card.definition_en, card.example_sentence].filter(Boolean).map(escapeHtml).join("<br>")
    : (card.example_sentence ? escapeHtml(card.example_sentence) : "Нажмите, чтобы перевернуть");
  const actions = isFlipped
    ? `<button class="learning" data-study-progress="learning">${iconSvg("paw")} Ещё учу<small>Нужно повторить</small></button>
       <button class="known" data-study-progress="known">${iconSvg("paw")} Знаю<small>Отлично!</small></button>`
    : "";

  const newCount = countByStatus("new");
  const newBadge = newCount ? `<span class="badge">${iconSvg("spark")} Новых слов: +${newCount}</span>` : "";

  studyEl.innerHTML = `
    ${cardModeSwitch()}
    <div class="study-meta">
      <div class="study-progress">
        Карточка ${currentIndex + 1} из ${studyCards.length}
        <div class="progress-track" aria-hidden="true">
          <div class="progress-fill" style="width:${studyProgressPercent()}%"></div>
        </div>
      </div>
      ${newBadge}
    </div>
    <article class="${flashcardClass}" data-flashcard data-card-id="${card.id}" role="button" tabindex="0"
             aria-pressed="${isFlipped}" aria-label="Перевернуть карточку">
      <div class="flashcard-head">
        <p class="flashcard-side">${sideLabel}</p>
      </div>
      <p class="flashcard-main">${escapeHtml(mainText)}</p>
      ${image}
      <div class="flashcard-sentence">
        <p class="flashcard-extra">${sentence || " "}</p>
      </div>
      <p class="flip-hint">Нажми, чтобы перевернуть</p>
    </article>
    <div class="actions study-actions">${actions}</div>
    <aside class="cat-note" aria-label="Сообщение котика">
      <div class="cat-mascot" aria-hidden="true"><img class="cat-mascot-img" src="${MASCOT_LOUNGE_SRC}" alt=""></div>
      <div class="cat-bubble"><strong>bro is bilingual now</strong><span>Котик ждёт твой следующий ход</span></div>
    </aside>`;
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
      <button type="button" class="${learningClass}" data-list-filter="learning">${iconSvg("words")} Учу</button>
      <button type="button" class="${knownClass}" data-list-filter="known">${iconSvg("paw")} Знаю</button>
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
      <div>
        <strong>${escapeHtml(card.term)}</strong>
        <p>${escapeHtml(card.translation_ru)}</p>
        ${card.example_sentence ? `<p>${escapeHtml(card.example_sentence)}</p>` : ""}
      </div>
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

function homeworkCardTemplate(item) {
  const title = item.slot === "current" ? "Текущее ДЗ" : "Предыдущее ДЗ";
  const cardClass = item.slot === "current" ? "homework-card" : "homework-card homework-previous";
  const homeworkList = item.homework_items.length
    ? item.homework_items.map((entry) => `<li>${escapeHtml(entry)}</li>`).join("")
    : "<li>Домашка будет добавлена после проверки урока.</li>";
  const cardsButton = item.new_cards_count
    ? `<div class="actions homework-actions">
         <button type="button" class="known" data-section="cards">Учить ${item.new_cards_count} слов</button>
       </div>`
    : "";
  const summaryBlock = item.summary_text
    ? `<div class="homework-block"><h3>${iconSvg("spark")} Итоги урока</h3><p>${escapeHtml(item.summary_text)}</p></div>`
    : "";
  const winsBlock = item.wins_text
    ? `<div class="homework-block"><h3>${iconSvg("paw")} Что получилось</h3><p>${escapeHtml(item.wins_text)}</p></div>`
    : "";
  const focusBlock = item.focus_text
    ? `<div class="homework-block"><h3>${iconSvg("words")} Фокус</h3><p>${escapeHtml(item.focus_text)}</p></div>`
    : "";
  return `
    <article class="${cardClass}">
      <h2>${title}</h2>
      <p class="homework-date">${escapeHtml(item.lesson_date_label)}</p>
      ${summaryBlock}
      ${winsBlock}
      ${focusBlock}
      <div class="homework-block"><h3>${iconSvg("homework")} Домашка</h3><ul class="homework-list">${homeworkList}</ul></div>
      ${cardsButton}
    </article>`;
}

function renderHomework() {
  hideSections();
  setActiveSection("homework");
  homeworkEl.classList.remove("hidden");
  if (!homeworkLoaded) {
    homeworkEl.innerHTML = '<div class="status">Загружаю домашку...</div>';
    setStatus("Загружаю домашку...");
    loadHomework();
    return;
  }
  if (!homeworkItems.length) {
    homeworkEl.innerHTML = '<div class="empty">Пока домашки нет. После урока преподаватель отправит её сюда.</div>';
    setStatus("Домашка");
    return;
  }
  homeworkEl.innerHTML = homeworkItems.map((item) => homeworkCardTemplate(item)).join("");
  setStatus("Домашка");
}

async function loadHomework() {
  if (!initData) {
    homeworkEl.innerHTML = '<div class="error">Откройте эту страницу внутри Telegram WebApp.</div>';
    setStatus("Нет Telegram initData");
    return;
  }
  try {
    const data = await api("/api/student/homework");
    homeworkItems = data.items;
    homeworkLoaded = true;
    renderHomework();
  } catch (error) {
    homeworkEl.innerHTML = `<div class="error">Ошибка загрузки: ${escapeHtml(error.message)}</div>`;
    setStatus("Ошибка");
  }
}

function renderCurrentSection() {
  if (currentSection === "stats") {
    renderStats();
    return;
  }
  if (currentSection === "homework") {
    renderHomework();
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
  handleFlashcardActivation(event, flipCard);
});

studyEl.addEventListener("keydown", (event) => {
  handleFlashcardActivation(event, flipCard);
});

homeworkEl.addEventListener("click", (event) => {
  const sectionButton = event.target.closest("button[data-section]");
  if (!sectionButton) return;
  currentSection = sectionButton.dataset.section;
  if (currentSection === "cards") currentCardMode = "study";
  currentIndex = 0;
  isFlipped = false;
  renderCurrentSection();
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
  <title>TutorHelper — мои занятия</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>{STYLE}</style>
</head>
<body>
  <main class="page">
    <header class="app-header">
      <h1 class="brand">TutorHelper</h1>
      <div class="cat-avatar" aria-hidden="true">
        <img class="cat-avatar-img" src="{MASCOT_AVATAR_SRC}" alt="">
      </div>
    </header>
    <h2 class="section-title">Мои занятия</h2>
    <div class="toolbar" aria-label="Разделы ученика">
      <button type="button" data-section="cards" class="mode-button">
        <svg class="ui-icon button-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="4" width="14" height="16" rx="3"></rect><path d="M9 9h6"></path><path d="M9 13h6"></path><path d="M12 17l2-2 2 2"></path></svg>
        Карточки
      </button>
      <button type="button" data-section="homework" class="secondary-button">
        <svg class="ui-icon button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 19h12"></path><path d="M7 15.5 16.5 6 20 9.5 10.5 19 6 20z"></path><path d="M14.5 8 18 11.5"></path></svg>
        Домашка
      </button>
      <button type="button" data-section="stats" class="secondary-button">
        <svg class="ui-icon button-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V12"></path><path d="M12 19V5"></path><path d="M19 19V9"></path><path d="M4 19h16"></path></svg>
        Статистика
      </button>
    </div>
    <div id="status" class="status">Загрузка...</div>
    <section id="study" class="study-area"></section>
    <section id="homework" class="card-list hidden"></section>
    <section id="stats" class="card-list hidden"></section>
  </main>
  <nav class="bottom-nav" aria-label="Нижняя навигация">
    <button type="button" data-section="cards" class="tab-active">
      <span class="nav-icon">
        <svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8 12 4l8 4-8 4z"></path><path d="M7 10.5V15c2.5 2 7.5 2 10 0v-4.5"></path><path d="M20 8v5"></path></svg>
      </span>
      Учиться
    </button>
    <button type="button" data-section="homework" class="secondary-button">
      <span class="nav-icon">
        <svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5h10a4 4 0 0 1 4 4v10H9a4 4 0 0 0-4 4z"></path><path d="M5 5v18"></path><path d="M9 9h6"></path><path d="M9 13h5"></path></svg>
      </span>
      Мои слова
    </button>
    <button type="button" data-section="stats" class="secondary-button">
      <span class="nav-icon">
        <svg class="ui-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19V12"></path><path d="M12 19V5"></path><path d="M19 19V9"></path><path d="M4 19h16"></path></svg>
      </span>
      Прогресс
    </button>
  </nav>
  <script>
    const MASCOT_AVATAR_SRC = "{MASCOT_AVATAR_SRC}";
    const MASCOT_LOUNGE_SRC = "{MASCOT_LOUNGE_SRC}";
  </script>
  <script>{CARD_UI_SCRIPT}</script>
  <script>{SCRIPT}</script>
</body>
</html>"""


@router.head("/student/cards", response_class=HTMLResponse)
def student_cards_webapp_head() -> str:
    return ""


@router.get("/student/cards", response_class=HTMLResponse)
def student_cards_webapp() -> str:
    return _page()
