(function exposeStudentCardUi(root, factory) {
  const ui = factory();
  if (typeof module === "object" && module.exports) module.exports = ui;
  if (root) Object.assign(root, ui);
}(typeof globalThis !== "undefined" ? globalThis : this, function createStudentCardUi() {
  "use strict";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function safeHttpsUrl(value) {
    if (typeof value !== "string" || !value.trim()) return "";
    try {
      const url = new URL(value);
      return url.protocol === "https:" ? url.href : "";
    } catch (_error) {
      return "";
    }
  }

  function attributionHtml(card) {
    const components = [];
    const creator = String(card?.image_creator ?? "").trim();
    const sourceUrl = safeHttpsUrl(card?.image_source_url);
    const license = String(card?.image_license ?? "").trim();
    const licenseUrl = safeHttpsUrl(card?.image_license_url);

    if (creator) components.push(`Фото: ${escapeHtml(creator)}`);
    if (sourceUrl) {
      components.push(
        `<a class="flashcard-image-source" href="${escapeHtml(sourceUrl)}" target="_blank"`
          + ' rel="noopener noreferrer">источник</a>',
      );
    }
    if (license) {
      const safeLicense = escapeHtml(license);
      components.push(licenseUrl
        ? `<a class="flashcard-image-license" href="${escapeHtml(licenseUrl)}" target="_blank"`
          + ` rel="noopener noreferrer">${safeLicense}</a>`
        : `<span class="flashcard-image-license">${safeLicense}</span>`);
    }

    return components.length ? components.join(" · ") : "Атрибуция недоступна.";
  }

  function imageBlock(card) {
    const imageUrl = safeHttpsUrl(card?.image_url);
    if (!imageUrl) return "";
    return `
      <div class="flashcard-image-wrapper">
        <div class="flashcard-image-region">
          <img class="flashcard-image" src="${escapeHtml(imageUrl)}" alt="" loading="lazy"
               referrerpolicy="no-referrer" onerror="handleImageError(this)">
          <div class="flashcard-image-placeholder" role="status" hidden>Изображение недоступно</div>
        </div>
        <div class="flashcard-image-attribution" data-no-flip tabindex="0"
             aria-label="Атрибуция изображения">${attributionHtml(card)}</div>
      </div>`;
  }

  function handleImageError(img) {
    const wrapper = img?.closest?.(".flashcard-image-wrapper");
    if (!wrapper) return false;
    const placeholder = wrapper.querySelector?.(".flashcard-image-placeholder");
    wrapper.classList.add("flashcard-image-failed");
    img.hidden = true;
    if (placeholder) placeholder.hidden = false;
    return true;
  }

  function handleFlashcardActivation(event, flip) {
    const card = event?.target?.closest?.("[data-flashcard]");
    if (!card) return false;
    const interactive = event.target.closest(
      'a, button, input, select, textarea, [role="button"], [data-no-flip]',
    );
    if (interactive && interactive !== card) return false;

    if (event.type === "keydown") {
      if (event.key !== "Enter" && event.key !== " ") return false;
      event.preventDefault();
    } else if (event.type !== "click") {
      return false;
    }

    const restoreKeyboardFocus = event.type === "keydown" && card.ownerDocument?.activeElement === card;
    const cardContainer = restoreKeyboardFocus ? card.parentElement : null;
    flip();
    if (restoreKeyboardFocus) cardContainer?.querySelector?.("[data-flashcard]")?.focus?.();
    return true;
  }

  return {
    attributionHtml,
    escapeHtml,
    handleFlashcardActivation,
    handleImageError,
    imageBlock,
    safeHttpsUrl,
  };
}));
