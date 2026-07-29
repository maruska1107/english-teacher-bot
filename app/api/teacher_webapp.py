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
.page { max-width: 860px; margin: 0 auto; padding: 18px 14px 34px; }
h1 { margin: 4px 0 8px; font-size: 24px; }
h2 { margin: 0 0 10px; font-size: 20px; }
h3 { margin: 0 0 8px; font-size: 17px; }
.lead { margin: 0 0 16px; color: var(--tg-theme-hint-color, #6b7280); }
.status { margin: 12px 0; color: var(--tg-theme-hint-color, #6b7280); }
.hidden { display: none; }
.profile-card,
.card,
.panel {
  margin: 12px 0;
  padding: 14px;
  border: 1px solid var(--tg-theme-section_separator_color, #e5e7eb);
  border-radius: 16px;
  background: var(--tg-theme-secondary-bg-color, #ffffff);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}
.profile-card { width: 100%; text-align: left; display: block; }
.profile-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 8px; }
.badge { display: inline-block; padding: 4px 9px; border-radius: 999px; font-weight: 800; }
.badge-new { background: #dcfce7; color: #166534; }
.badge-muted { background: #eef2ff; color: #3730a3; }
.tabs { display: flex; gap: 8px; margin: 12px 0; }
.tab-active { background: var(--tg-theme-button-color, #2563eb); color: var(--tg-theme-button-text-color, #ffffff); }
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
button:disabled { opacity: 0.55; cursor: wait; }
.primary { background: var(--tg-theme-button-color, #2563eb); color: var(--tg-theme-button-text-color, #ffffff); }
.secondary { background: #eef2ff; color: #3730a3; }
.danger { background: #fee2e2; color: #991b1b; }
.ghost { background: #f3f4f6; color: #374151; }
.empty { padding: 20px; border-radius: 14px; background: #ecfdf5; color: #065f46; }
.error { padding: 14px; border-radius: 14px; background: #fef2f2; color: #991b1b; }
.readonly-line { margin: 6px 0; color: var(--tg-theme-hint-color, #6b7280); }
"""

SCRIPT = """
const tg = window.Telegram && window.Telegram.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}
const initData = tg?.initData || "";
const statusEl = document.getElementById("status");
const profilesEl = document.getElementById("profiles");
const detailEl = document.getElementById("profile-detail");

let profiles = [];
let selectedProfile = null;
let currentTab = "draft";
let draftCards = [];
let publishedCards = [];
let addFormOpen = false;

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
  if (response.status === 204) return {};
  return response.json();
}

function profileTypeLabel(profile) {
  return profile.profile_type === "group" ? "группа" : "ученик";
}

function profileTemplate(profile) {
  const newCount = Number(profile.new_card_count || 0);
  const publishedCount = Number(profile.published_card_count || 0);
  return `
    <button type="button" class="profile-card" data-profile-id="${profile.id}" aria-label="Открыть карточки">
      <h2>${escapeHtml(profile.name)}</h2>
      <div class="profile-meta">
        <span class="badge badge-muted">${profileTypeLabel(profile)}</span>
        <span class="badge badge-new">+${newCount} новых слов</span>
        <span class="badge badge-muted">${publishedCount} опубликовано</span>
      </div>
    </button>`;
}

function renderProfiles() {
  detailEl.classList.add("hidden");
  profilesEl.classList.remove("hidden");
  if (!profiles.length) {
    profilesEl.innerHTML = '<div class="empty">Профилей пока нет. Добавьте ученика или группу в Telegram.</div>';
    return;
  }
  profilesEl.innerHTML = profiles.map(profileTemplate).join("");
}

async function loadProfiles() {
  if (!initData) {
    profilesEl.innerHTML = '<div class="error">Откройте эту страницу внутри Telegram WebApp.</div>';
    setStatus("Нет Telegram initData");
    return;
  }
  setStatus("Загружаю профили...");
  try {
    const data = await api("/api/teacher/card-profiles");
    profiles = data.profiles || [];
    renderProfiles();
    setStatus(`Профилей: ${profiles.length}`);
  } catch (error) {
    profilesEl.innerHTML = `<div class="error">Ошибка загрузки: ${escapeHtml(error.message)}</div>`;
    setStatus("Ошибка");
  }
}

async function openProfile(profileId) {
  selectedProfile = profiles.find((profile) => profile.id === Number(profileId));
  if (!selectedProfile) return;
  currentTab = "draft";
  profilesEl.classList.add("hidden");
  detailEl.classList.remove("hidden");
  await loadProfileCards();
}

async function loadProfileCards() {
  if (!selectedProfile) return;
  setStatus(`Загружаю карточки: ${selectedProfile.name}`);
  const query = `profile_id=${selectedProfile.id}`;
  const [draftData, publishedData] = await Promise.all([
    api(`/api/teacher/cards?${query}&status=draft`),
    api(`/api/teacher/cards?${query}&status=published`),
  ]);
  draftCards = draftData.cards || [];
  publishedCards = publishedData.cards || [];
  renderSelectedProfile();
  setStatus(`Новых карточек: ${draftCards.length}`);
}

function editableCardTemplate(card) {
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
        <button type="button" class="danger" data-action="delete-card">Удалить</button>
      </div>
    </article>`;
}

function publishedCardTemplate(card) {
  return `
    <article class="card">
      <h3>${escapeHtml(card.term)} — ${escapeHtml(card.translation_ru)}</h3>
      ${card.definition_en ? `<p class="readonly-line">${escapeHtml(card.definition_en)}</p>` : ""}
      ${card.example_sentence ? `<p class="readonly-line">${escapeHtml(card.example_sentence)}</p>` : ""}
      <span class="badge badge-muted">Опубликовано</span>
    </article>`;
}

function addWordPanel() {
  return `
    <section class="panel" id="add-word-panel">
      <h3>+ Добавить слово</h3>
      <p class="lead">Добавленное слово появится в конце списка новых карточек.</p>
      <label>Слово / фраза</label>
      <input name="new_term" placeholder="journey">
      <label>Перевод</label>
      <input name="new_translation_ru" placeholder="путешествие">
      <label>Определение на английском</label>
      <textarea name="new_definition_en"></textarea>
      <label>Пример</label>
      <textarea name="new_example_sentence"></textarea>
      <label>Фраза из урока</label>
      <textarea name="new_source_phrase"></textarea>
      <label>Уровень</label>
      <input name="new_level" placeholder="B1">
      <div class="actions">
        <button type="button" class="secondary" data-action="create-card">Добавить в список</button>
        <button type="button" class="ghost" data-action="hide-add-form">Отмена</button>
      </div>
    </section>`;
}

function addWordCollapsedButton() {
  return `
    <div class="actions">
      <button type="button" class="secondary" data-action="show-add-form">+ Добавить слово</button>
    </div>`;
}

function payloadFromCard(cardEl) {
  return Object.fromEntries(
    ["term", "translation_ru", "definition_en", "example_sentence", "source_phrase", "level"].map((field) => [
      field,
      cardEl.querySelector(`[name="${field}"]`).value,
    ])
  );
}

function manualPayload() {
  return {
    learning_profile_id: selectedProfile.id,
    term: detailEl.querySelector('[name="new_term"]').value,
    translation_ru: detailEl.querySelector('[name="new_translation_ru"]').value,
    definition_en: detailEl.querySelector('[name="new_definition_en"]').value,
    example_sentence: detailEl.querySelector('[name="new_example_sentence"]').value,
    source_phrase: detailEl.querySelector('[name="new_source_phrase"]').value,
    level: detailEl.querySelector('[name="new_level"]').value,
  };
}

function renderSelectedProfile() {
  const isNewTab = currentTab === "draft";
  const cards = isNewTab ? draftCards : publishedCards;
  const emptyText = isNewTab ? "Новых карточек пока нет." : "Опубликованных карточек пока нет.";
  const cardHtml = cards.length
    ? cards.map(isNewTab ? editableCardTemplate : publishedCardTemplate).join("")
    : `<div class="empty">${emptyText}</div>`;
  const publishDisabled = draftCards.length ? "" : "disabled";
  const publishButton = isNewTab
    ? `<button type="button" class="primary" data-action="publish-all" ${publishDisabled}>
        Опубликовать все карточки
      </button>`
    : "";
  const addWordHtml = isNewTab ? (addFormOpen ? addWordPanel() : addWordCollapsedButton()) : "";
  const draftTabClass = isNewTab ? "tab-active" : "secondary";
  const publishedTabClass = !isNewTab ? "tab-active" : "secondary";

  detailEl.innerHTML = `
    <button type="button" class="ghost" data-action="back-to-profiles">← Назад к ученикам и группам</button>
    <section class="panel">
      <h2>${escapeHtml(selectedProfile.name)}</h2>
      <p class="lead">+N новых слов — количество карточек, которые ждут проверки.</p>
      <div class="profile-meta">
        <span class="badge badge-new">+${draftCards.length} новых слов</span>
        <span class="badge badge-muted">${publishedCards.length} опубликовано</span>
      </div>
      <div class="tabs">
        <button type="button" class="${draftTabClass}" data-action="tab-draft">Новые карточки</button>
        <button type="button" class="${publishedTabClass}" data-action="tab-published">Опубликованные</button>
      </div>
      <div id="profile-cards">${cardHtml}</div>
      ${addWordHtml}
      <div class="actions">${publishButton}</div>
    </section>`;
}

async function saveAllDraftCardEdits() {
  const cardEls = Array.from(detailEl.querySelectorAll("[data-card-id]"));
  await Promise.all(
    cardEls.map((cardEl) => api(`/api/teacher/cards/${cardEl.dataset.cardId}`, {
      method: "PATCH",
      body: JSON.stringify(payloadFromCard(cardEl)),
    }))
  );
}

async function refreshProfilesAndSelectedCardCounts() {
  const data = await api("/api/teacher/card-profiles");
  profiles = data.profiles || [];
  if (selectedProfile) {
    selectedProfile = profiles.find((profile) => profile.id === selectedProfile.id) || selectedProfile;
  }
}

async function publishAllDraftCards(button) {
  if (!selectedProfile || !draftCards.length) return;
  button.disabled = true;
  try {
    await saveAllDraftCardEdits();
    const result = await api("/api/teacher/cards/publish-batch", {
      method: "POST",
      body: JSON.stringify({ learning_profile_id: selectedProfile.id }),
    });
    await refreshProfilesAndSelectedCardCounts();
    await loadProfileCards();
    setStatus(`Опубликовано: ${result.published_count}`);
  } catch (error) {
    setStatus(`Ошибка: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function deleteCard(cardId) {
  if (!confirm("Удалить эту карточку?")) return;
  await api(`/api/teacher/cards/${cardId}`, { method: "DELETE" });
  await refreshProfilesAndSelectedCardCounts();
  await loadProfileCards();
  setStatus("Карточка удалена");
}

async function createManualCard() {
  const payload = manualPayload();
  if (!payload.term.trim() || !payload.translation_ru.trim()) {
    setStatus("Заполните слово и перевод");
    return;
  }
  const createdCard = await api("/api/teacher/cards", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  await refreshProfilesAndSelectedCardCounts();
  draftCards.push(createdCard);
  addFormOpen = false;
  renderSelectedProfile();
  setStatus("Слово добавлено в новые карточки");
}

profilesEl.addEventListener("click", async (event) => {
  event.preventDefault();
  const profileButton = event.target.closest("[data-profile-id]");
  if (!profileButton) return;
  await openProfile(profileButton.dataset.profileId);
});

detailEl.addEventListener("click", async (event) => {
  event.preventDefault();
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  try {
    if (button.dataset.action === "back-to-profiles") {
      selectedProfile = null;
      renderProfiles();
    }
    if (button.dataset.action === "tab-draft") {
      currentTab = "draft";
      addFormOpen = false;
      renderSelectedProfile();
    }
    if (button.dataset.action === "tab-published") {
      currentTab = "published";
      addFormOpen = false;
      renderSelectedProfile();
    }
    if (button.dataset.action === "show-add-form") {
      addFormOpen = true;
      renderSelectedProfile();
    }
    if (button.dataset.action === "hide-add-form") {
      addFormOpen = false;
      renderSelectedProfile();
    }
    if (button.dataset.action === "create-card") {
      await createManualCard();
    }
    if (button.dataset.action === "delete-card") {
      await deleteCard(button.closest("[data-card-id]").dataset.cardId);
    }
    if (button.dataset.action === "publish-all") {
      await publishAllDraftCards(button);
    }
  } catch (error) {
    setStatus(`Ошибка: ${error.message}`);
  }
});

loadProfiles();
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
    <h1>Карточки</h1>
    <p class="lead">Сначала выберите ученика или группу, затем проверьте новые карточки.</p>
    <div id="status" class="status">Загрузка...</div>
    <section id="profiles"></section>
    <section id="profile-detail" class="hidden"></section>
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
