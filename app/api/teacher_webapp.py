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
  --primary: #746e9f;
  --primary-border: #625d8b;
  --primary-soft: #ece9f2;
  --primary-soft-text: #5c5870;
  --known-bg: #dcebe2;
  --known-text: #3d644e;
  --known-border: #c8ded1;
  --danger-bg: #f6e7e8;
  --danger-text: #7a4047;
  --danger-border: #ebcfd2;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  background: var(--page-bg);
  color: var(--text);
}
.page { max-width: 860px; margin: 0 auto; padding: 18px 14px 34px; }
h1 { margin: 4px 0 8px; font-size: 24px; }
h2 { margin: 0 0 10px; font-size: 20px; }
h3 { margin: 0 0 8px; font-size: 17px; }
.lead { margin: 0 0 16px; color: var(--muted); }
.status { margin: 12px 0; color: var(--muted); }
.hidden { display: none; }
.profile-card,
.card,
.panel {
  margin: 12px 0;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: 0 8px 20px rgba(57, 52, 74, 0.06);
}
.profile-card { width: 100%; text-align: left; display: block; color: var(--text); }
.profile-card:hover { border-color: #cfc8df; background: #fdfcff; }
.profile-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 8px; }
.badge {
  display: inline-block;
  padding: 4px 9px;
  border: 1px solid var(--border);
  border-radius: 999px;
  font-weight: 800;
}
.badge-new { background: var(--known-bg); color: var(--known-text); border-color: var(--known-border); }
.badge-muted { background: var(--primary-soft); color: var(--primary-soft-text); border-color: #d8d2e5; }
.tabs { display: flex; gap: 8px; margin: 12px 0; }
.tab-active { background: var(--primary); color: #ffffff; border-color: var(--primary-border); }
label { display: block; margin: 10px 0 4px; font-size: 13px; color: var(--muted); }
input, textarea {
  width: 100%;
  padding: 10px 11px;
  border: 1px solid var(--border);
  border-radius: 10px;
  font: inherit;
  background: var(--surface);
  color: var(--text);
  outline: none;
}
input:focus, textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(116, 110, 159, 0.14);
}
textarea { min-height: 68px; resize: vertical; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
button {
  border: 1px solid var(--border);
  border-radius: 11px;
  padding: 10px 12px;
  font-weight: 700;
  cursor: pointer;
}
button:disabled { opacity: 0.48; cursor: not-allowed; }
.primary { background: var(--primary); color: #ffffff; border-color: var(--primary-border); }
.secondary { background: var(--primary-soft); color: var(--primary-soft-text); border-color: #d8d2e5; }
.danger { background: var(--danger-bg); color: var(--danger-text); border-color: var(--danger-border); }
.ghost { background: #f3f1f6; color: #625d70; border-color: var(--border); }
.empty { padding: 20px; border-radius: 14px; background: var(--known-bg); color: var(--known-text); }
.error { padding: 14px; border-radius: 14px; background: var(--danger-bg); color: var(--danger-text); }
.readonly-line { margin: 6px 0; color: var(--muted); }
.card-image-area {
  min-height: 180px;
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: #f3f1f6;
}
.card-thumbnail { width: 100%; height: 146px; display: block; object-fit: cover; background: #ebe8f0; }
.image-placeholder { min-height: 146px; display: grid; place-items: center; color: var(--muted); }
.image-attribution { min-height: 34px; padding: 8px 10px; font-size: 12px; color: var(--muted); }
.image-attribution a { color: var(--primary-soft-text); }
.image-options { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
.image-option { min-width: 0; padding: 6px; background: #fdfcff; border-color: #d8d2e5; text-align: left; }
.image-option img { width: 100%; height: 82px; object-fit: cover; border-radius: 7px; background: #ebe8f0; }
.image-option-meta {
  margin-top: 5px; overflow: hidden; font-size: 11px; color: var(--muted); text-overflow: ellipsis; white-space: nowrap;
}
.image-state {
  margin-top: 9px; padding: 10px; border-radius: 10px; background: var(--primary-soft); color: var(--primary-soft-text);
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
const profilesEl = document.getElementById("profiles");
const detailEl = document.getElementById("profile-detail");

let profiles = [];
let selectedProfile = null;
let currentTab = "draft";
let draftCards = [];
let publishedCards = [];
let addFormOpen = false;
const imageOptionsState = new Map();
let imageOptionsRequestGeneration = 0;

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

function safeHttpsUrl(value) {
  try {
    const parsed = new URL(String(value || ""));
    return parsed.protocol === "https:" ? parsed.href : "";
  } catch (_) {
    return "";
  }
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
  cancelAllImageOptionsRequests();
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
  cancelAllImageOptionsRequests();
  renderSelectedProfile();
  setStatus(`Новых карточек: ${draftCards.length}`);
}

function imageAttributionTemplate(card) {
  const sourceUrl = safeHttpsUrl(card.image_source_url);
  const licenseUrl = safeHttpsUrl(card.image_license_url);
  const creator = card.image_creator ? `${escapeHtml(card.image_creator)} · ` : "";
  const source = sourceUrl
    ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">источник</a>`
    : "источник";
  const licenseText = escapeHtml(card.image_license || "лицензия");
  const license = licenseUrl
    ? `<a href="${escapeHtml(licenseUrl)}" target="_blank" rel="noopener noreferrer">${licenseText}</a>`
    : licenseText;
  return `<div class="image-attribution">Фото: ${creator}${source} · ${license}</div>`;
}

function cardImageTemplate(card) {
  const imageUrl = safeHttpsUrl(card.image_url);
  if (!imageUrl) {
    return '<div class="card-image-area"><div class="image-placeholder">Картинка не выбрана</div></div>';
  }
  return `<div class="card-image-area">
    <img class="card-thumbnail" data-safe-image src="${escapeHtml(imageUrl)}" alt="">
    ${imageAttributionTemplate(card)}
  </div>`;
}

function hideBrokenImageRegion(image) {
  image.removeAttribute("src");
  const area = image.closest(".card-image-area");
  if (area) area.hidden = true;
}

function imageOptionsTemplate(card) {
  const state = imageOptionsState.get(card.id);
  if (!state?.open) return "";
  if (state.loading && !state.options.length) return '<div class="image-state">Загружаю варианты...</div>';
  if (state.error) return `<div class="error">${escapeHtml(state.error)}</div>`;
  if (state.empty) return '<div class="image-state">Подходящих картинок не найдено.</div>';
  const options = state.options.map((option) => {
    const imageUrl = safeHttpsUrl(option.image_url);
    if (!imageUrl) return "";
    const creator = option.creator ? escapeHtml(option.creator) : "Без автора";
    return `<button type="button" class="image-option" data-action="select-image"
      ${state.loading ? "disabled" : ""} data-image-id="${escapeHtml(option.image_id)}">
      <img data-safe-image src="${escapeHtml(imageUrl)}" alt="">
      <div class="image-option-meta">${creator} · ${escapeHtml(option.license)}</div>
    </button>`;
  }).join("");
  const moreButton = state.hasMore
    ? `<button type="button" class="secondary" data-action="more-images" ${state.loading ? "disabled" : ""}>
        Показать ещё
      </button>`
    : "";
  return `<div class="image-options">${options}</div><div class="actions">${moreButton}</div>`;
}

function editableCardTemplate(card) {
  const imageState = imageOptionsState.get(card.id);
  const imageBusy = Boolean(imageState?.loading);
  return `
    <article class="card" data-card-id="${card.id}">
      ${cardImageTemplate(card)}
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
        <button type="button" class="secondary" data-action="toggle-images" ${imageBusy ? "disabled" : ""}>
          ${imageState?.open ? "Скрыть варианты" : "Заменить картинку"}
        </button>
        <button type="button" class="ghost" data-action="remove-image"
          ${card.image_url && !imageBusy ? "" : "disabled"}>
          Убрать картинку
        </button>
        <button type="button" class="danger" data-action="delete-card">Удалить</button>
      </div>
      ${imageOptionsTemplate(card)}
    </article>`;
}

function publishedCardTemplate(card) {
  return `
    <article class="card">
      ${cardImageTemplate(card)}
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
      <label>Слово / фраза *</label>
      <input name="new_term" placeholder="journey" data-required-manual-card>
      <label>Перевод *</label>
      <input name="new_translation_ru" placeholder="путешествие" data-required-manual-card>
      <label>Пример (необязательно)</label>
      <textarea name="new_example_sentence"></textarea>
      <div class="actions">
        <button type="button" class="secondary" data-action="create-card" disabled>Добавить в список</button>
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
    definition_en: "",
    example_sentence: detailEl.querySelector('[name="new_example_sentence"]').value,
    source_phrase: "",
    level: "",
  };
}

function updateCreateCardButton() {
  const button = detailEl.querySelector('button[data-action="create-card"]');
  if (!button) return;
  const term = detailEl.querySelector('[name="new_term"]')?.value.trim() || "";
  const translation = detailEl.querySelector('[name="new_translation_ru"]')?.value.trim() || "";
  button.disabled = !term || !translation;
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

function syncDraftEditsFromDom() {
  for (const cardEl of detailEl.querySelectorAll("[data-card-id]")) {
    const cardId = Number(cardEl.dataset.cardId);
    const index = draftCards.findIndex((card) => card.id === cardId);
    if (index >= 0) draftCards[index] = { ...draftCards[index], ...payloadFromCard(cardEl) };
  }
}

function replaceDraftCard(updatedCard) {
  syncDraftEditsFromDom();
  const current = draftCards.find((card) => card.id === updatedCard.id);
  const editableFields = ["term", "translation_ru", "definition_en", "example_sentence", "source_phrase", "level"];
  const edits = current ? Object.fromEntries(editableFields.map((field) => [field, current[field]])) : {};
  draftCards = draftCards.map((card) => card.id === updatedCard.id ? { ...updatedCard, ...edits } : card);
  renderSelectedProfile();
}

function imageOptionsRequestOffset(state, nextPage) {
  if (!nextPage) return 0;
  const offset = Number(state?.nextOffset);
  return Number.isFinite(offset) && offset <= 300 ? offset : null;
}

function imageOptionsPage(previous, data, offset) {
  const options = Array.isArray(data.options) ? data.options.slice(0, 3) : [];
  const nextOffset = Number(data.next_offset || offset + 3);
  return {
    ...previous,
    options,
    nextOffset,
    hasMore: options.length === 3 && nextOffset <= 300,
    empty: options.length === 0,
  };
}

function imageOptionsLoadingState(previous) {
  return {
    ...previous,
    open: true,
    loading: true,
    error: "",
    empty: false,
  };
}

function beginImageOptionsRequest(cardId) {
  const previous = imageOptionsState.get(cardId) || {};
  if (previous.controller) previous.controller.abort();
  const request = { token: ++imageOptionsRequestGeneration, controller: new AbortController() };
  imageOptionsState.set(cardId, { ...previous, requestToken: request.token, controller: request.controller });
  return request;
}

function isCurrentImageOptionsRequest(cardId, token) {
  return imageOptionsState.get(cardId)?.requestToken === token;
}

function cancelImageOptionsRequest(cardId) {
  const state = imageOptionsState.get(cardId);
  if (state?.controller) state.controller.abort();
  imageOptionsRequestGeneration += 1;
  imageOptionsState.delete(cardId);
}

function cancelAllImageOptionsRequests() {
  for (const cardId of imageOptionsState.keys()) cancelImageOptionsRequest(cardId);
  imageOptionsState.clear();
}

async function loadImageOptions(cardId, nextPage = false) {
  const previous = imageOptionsState.get(cardId) || { open: true, options: [], nextOffset: 0 };
  const offset = imageOptionsRequestOffset(previous, nextPage);
  if (offset === null) return;
  syncDraftEditsFromDom();
  const request = beginImageOptionsRequest(cardId);
  const state = imageOptionsLoadingState({
    ...previous,
    requestToken: request.token,
    controller: request.controller,
  });
  imageOptionsState.set(cardId, state);
  renderSelectedProfile();
  try {
    const data = await api(`/api/teacher/cards/${cardId}/image-options?offset=${offset}`, {
      signal: request.controller.signal,
    });
    if (!isCurrentImageOptionsRequest(cardId, request.token)) return;
    Object.assign(state, imageOptionsPage(state, data, offset));
  } catch (_) {
    if (!isCurrentImageOptionsRequest(cardId, request.token)) return;
    state.error = "Не удалось загрузить картинки. Попробуйте ещё раз.";
  } finally {
    if (!isCurrentImageOptionsRequest(cardId, request.token)) return;
    syncDraftEditsFromDom();
    state.loading = false;
    delete state.controller;
    imageOptionsState.set(cardId, state);
    renderSelectedProfile();
  }
}

async function toggleImageOptions(cardId) {
  syncDraftEditsFromDom();
  const state = imageOptionsState.get(cardId);
  if (state?.open) {
    if (state.controller) state.controller.abort();
    imageOptionsRequestGeneration += 1;
    state.open = false;
    state.loading = false;
    delete state.controller;
    delete state.requestToken;
    renderSelectedProfile();
    return;
  }
  if (state?.options.length) {
    state.open = true;
    imageOptionsState.set(cardId, state);
    renderSelectedProfile();
    return;
  }
  await loadImageOptions(cardId);
}

async function selectCardImage(cardId, imageId) {
  const state = imageOptionsState.get(cardId);
  const option = state?.options.find((candidate) => candidate.image_id === imageId);
  if (!option) return;
  cancelImageOptionsRequest(cardId);
  const busyState = imageOptionsLoadingState({ ...state, controller: null, requestToken: null });
  imageOptionsState.set(cardId, busyState);
  renderSelectedProfile();
  try {
    const updatedCard = await api(`/api/teacher/cards/${cardId}/image`, {
      method: "PUT",
      body: JSON.stringify({ image_id: option.image_id }),
    });
    imageOptionsState.delete(cardId);
    replaceDraftCard(updatedCard);
    setStatus("Картинка выбрана");
  } catch (error) {
    busyState.loading = false;
    busyState.error = "Не удалось выбрать картинку. Попробуйте ещё раз.";
    imageOptionsState.set(cardId, busyState);
    renderSelectedProfile();
    setStatus(`Ошибка: ${error.message}`);
  }
}

async function removeCardImage(cardId) {
  const previous = imageOptionsState.get(cardId) || { open: false, options: [] };
  cancelImageOptionsRequest(cardId);
  const busyState = imageOptionsLoadingState({ ...previous, open: previous.open || false });
  imageOptionsState.set(cardId, busyState);
  renderSelectedProfile();
  try {
    const updatedCard = await api(`/api/teacher/cards/${cardId}/image`, { method: "DELETE" });
    imageOptionsState.delete(cardId);
    replaceDraftCard(updatedCard);
    setStatus("Картинка убрана");
  } catch (error) {
    busyState.loading = false;
    busyState.open = previous.open || false;
    imageOptionsState.set(cardId, busyState);
    renderSelectedProfile();
    setStatus(`Ошибка: ${error.message}`);
  }
}

profilesEl.addEventListener("click", async (event) => {
  event.preventDefault();
  const profileButton = event.target.closest("[data-profile-id]");
  if (!profileButton) return;
  await openProfile(profileButton.dataset.profileId);
});

detailEl.addEventListener("input", (event) => {
  if (event.target.matches("[data-required-manual-card]")) {
    updateCreateCardButton();
  }
});

detailEl.addEventListener("error", (event) => {
  if (!event.target.matches("img[data-safe-image]")) return;
  if (event.target.classList.contains("card-thumbnail")) hideBrokenImageRegion(event.target);
  else {
    event.target.removeAttribute("src");
    event.target.hidden = true;
  }
}, true);

detailEl.addEventListener("click", async (event) => {
  event.preventDefault();
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  try {
    if (button.dataset.action === "back-to-profiles") {
      cancelAllImageOptionsRequests();
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
    if (button.dataset.action === "toggle-images") {
      await toggleImageOptions(Number(button.closest("[data-card-id]").dataset.cardId));
    }
    if (button.dataset.action === "more-images") {
      await loadImageOptions(Number(button.closest("[data-card-id]").dataset.cardId), true);
    }
    if (button.dataset.action === "select-image") {
      await selectCardImage(
        Number(button.closest("[data-card-id]").dataset.cardId),
        button.dataset.imageId,
      );
    }
    if (button.dataset.action === "remove-image") {
      await removeCardImage(Number(button.closest("[data-card-id]").dataset.cardId));
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
