'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {
  attributionHtml,
  handleFlashcardActivation,
  handleImageError,
  imageBlock,
  safeHttpsUrl,
} = require('../../app/static/student_card_ui.js');

const studentWebappSource = fs.readFileSync('app/api/student_webapp.py', 'utf8');

function targetInside(kind) {
  const flashcard = { dataset: { flashcard: '' } };
  return {
    closest(selector) {
      if (selector === '[data-flashcard]') return flashcard;
      if (selector.startsWith('a, button, input, select, textarea')) {
        return kind === 'interactive' ? {} : null;
      }
      return null;
    },
  };
}

test('attribution rendering escapes malicious creator text and attributes', () => {
  const creator = '"><img src=x onerror="globalThis.pwned=true">&\'';
  const html = attributionHtml({
    image_creator: creator,
    image_source_url: 'https://example.test/a?name=%22bad%22&ok=1',
    image_license: 'CC BY <script>alert(1)</script>',
    image_license_url: 'https://creativecommons.org/licenses/by/4.0/',
  });

  assert.ok(html.includes('&lt;img src=x onerror=&quot;globalThis.pwned=true&quot;&gt;&amp;&#39;'));
  assert.ok(html.includes('CC BY &lt;script&gt;alert(1)&lt;/script&gt;'));
  assert.ok(html.includes('href="https://example.test/a?name=%22bad%22&amp;ok=1"'));
  assert.equal(html.includes('<img'), false);
  assert.equal(html.includes('<script>'), false);
});

test('safeHttpsUrl accepts only absolute HTTPS URLs', () => {
  assert.equal(safeHttpsUrl('https://example.test/image.jpg'), 'https://example.test/image.jpg');
  for (const unsafe of [
    'javascript:alert(1)',
    'data:image/svg+xml,<svg/>',
    'http://example.test/image.jpg',
    '/relative/image.jpg',
    'image.jpg',
  ]) {
    assert.equal(safeHttpsUrl(unsafe), '', unsafe);
  }
});

test('incomplete attribution omits unavailable components without fake labels', () => {
  assert.equal(attributionHtml({}), 'Атрибуция недоступна.');
  assert.equal(attributionHtml({ image_creator: 'Alice' }), 'Фото: Alice');
  assert.equal(
    attributionHtml({ image_license: 'CC0' }),
    '<span class="flashcard-image-license">CC0</span>',
  );
  const sourceOnly = attributionHtml({ image_source_url: 'https://example.test/work' });
  assert.match(sourceOnly, />источник<\/a>$/);
  assert.equal(sourceOnly.includes('лицензия'), false);
});

test('long attribution is preserved in full in rendered image block', () => {
  const creator = `Creator ${'very-long-name '.repeat(60)}`.trim();
  const html = imageBlock({
    image_url: 'https://example.test/image.jpg',
    image_creator: creator,
    image_source_url: 'https://example.test/work',
    image_license: 'CC BY-SA 4.0',
    image_license_url: 'https://creativecommons.org/licenses/by-sa/4.0/',
  });

  assert.ok(html.includes(creator));
  assert.equal(html.includes('…'), false);
  assert.match(html, /class="flashcard-image-attribution" data-no-flip tabindex="0"/);
});

test('attribution link clicks preserve navigation and never flip the card', () => {
  let flips = 0;
  let prevented = false;
  const activated = handleFlashcardActivation(
    {
      type: 'click',
      target: targetInside('interactive'),
      preventDefault() { prevented = true; },
    },
    () => { flips += 1; },
  );

  assert.equal(activated, false);
  assert.equal(flips, 0);
  assert.equal(prevented, false);
});

test('click, Enter, and Space activate a card while link keys do not bubble into a flip', () => {
  for (const event of [
    { type: 'click', target: targetInside('plain') },
    { type: 'keydown', key: 'Enter', target: targetInside('plain') },
    { type: 'keydown', key: ' ', target: targetInside('plain') },
  ]) {
    let flips = 0;
    let prevented = false;
    event.preventDefault = () => { prevented = true; };
    assert.equal(handleFlashcardActivation(event, () => { flips += 1; }), true);
    assert.equal(flips, 1);
    assert.equal(prevented, event.type === 'keydown');
  }

  let linkFlips = 0;
  const linkEvent = {
    type: 'keydown',
    key: 'Enter',
    target: targetInside('interactive'),
    preventDefault() { throw new Error('link navigation must not be prevented'); },
  };
  assert.equal(handleFlashcardActivation(linkEvent, () => { linkFlips += 1; }), false);
  assert.equal(linkFlips, 0);
});

test('keyboard flips restore focus to the newly rendered card for repeated activation', () => {
  let focusedCard = null;
  let currentCard;
  const container = {
    querySelector(selector) {
      assert.equal(selector, '[data-flashcard]');
      return currentCard;
    },
  };
  const makeCard = () => ({
    dataset: { flashcard: '' },
    ownerDocument: { get activeElement() { return focusedCard; } },
    parentElement: container,
    closest(selector) {
      if (selector === '[data-flashcard]') return this;
      return null;
    },
    focus() { focusedCard = this; },
  });
  currentCard = makeCard();
  currentCard.focus();

  for (const key of ['Enter', ' ']) {
    const oldCard = currentCard;
    let prevented = false;
    const activated = handleFlashcardActivation(
      {
        type: 'keydown',
        key,
        target: oldCard,
        preventDefault() { prevented = true; },
      },
      () => { currentCard = makeCard(); },
    );

    assert.equal(activated, true);
    assert.equal(prevented, true);
    assert.notEqual(currentCard, oldCard);
    assert.equal(focusedCard, currentCard);
  }
});

test('image errors reveal a stable placeholder in the existing reserved region', () => {
  const classes = new Set();
  const placeholder = { hidden: true };
  const wrapper = {
    classList: { add(value) { classes.add(value); } },
    querySelector(selector) {
      return selector === '.flashcard-image-placeholder' ? placeholder : null;
    },
  };
  const img = {
    hidden: false,
    closest(selector) {
      return selector === '.flashcard-image-wrapper' ? wrapper : null;
    },
  };

  assert.equal(handleImageError(img), true);
  assert.equal(img.hidden, true);
  assert.equal(placeholder.hidden, false);
  assert.ok(classes.has('flashcard-image-failed'));
});

test('student study cards omit redundant memory instructions', () => {
  assert.equal(studentWebappSource.includes('Сначала вспоминаем перевод сами'), false);
  assert.equal(studentWebappSource.includes('Выберите, насколько хорошо помните слово'), false);
});

test('student webapp exposes homework section and loads homework API', () => {
  assert.ok(studentWebappSource.includes('data-section="homework"'));
  assert.ok(studentWebappSource.includes('Домашка'));
  assert.ok(studentWebappSource.includes('/api/student/homework'));
  assert.ok(studentWebappSource.includes('Пока домашки нет. После урока преподаватель отправит её сюда.'));
  assert.ok(studentWebappSource.includes('Текущее ДЗ'));
  assert.ok(studentWebappSource.includes('Предыдущее ДЗ'));
});

test('student webapp uses cat-inspired TutorHelper visual shell without adding new progress actions', () => {
  assert.ok(studentWebappSource.includes('TutorHelper'));
  assert.ok(studentWebappSource.includes('class="cat-avatar"'));
  assert.ok(studentWebappSource.includes('class="bottom-nav"'));
  assert.ok(studentWebappSource.includes('Мои занятия'));
  assert.ok(studentWebappSource.includes('Карточка ${currentIndex + 1} из ${studyCards.length}'));
  assert.ok(studentWebappSource.includes('Новых слов: +${newCount}'));
  assert.ok(studentWebappSource.includes('bro is bilingual now'));
  assert.ok(studentWebappSource.includes('Котик ждёт твой следующий ход'));
  assert.equal(studentWebappSource.includes('data-study-progress="forgot"'), false);
  assert.equal(studentWebappSource.includes('XP'), false);
  assert.equal(studentWebappSource.includes('streak'), false);
});

test('student webapp uses unified mascot assets and outline icons without fake audio controls', () => {
  assert.ok(studentWebappSource.includes('MASCOT_AVATAR_SRC'));
  assert.ok(studentWebappSource.includes('MASCOT_LOUNGE_SRC'));
  assert.ok(studentWebappSource.includes('tutorhelper-cat-avatar.png'));
  assert.ok(studentWebappSource.includes('tutorhelper-cat-lounge.png'));
  assert.ok(studentWebappSource.includes('class="cat-avatar-img"'));
  assert.ok(studentWebappSource.includes('class="cat-mascot-img"'));
  assert.ok(studentWebappSource.includes('function iconSvg(name)'));
  assert.ok(studentWebappSource.includes('iconSvg("cards")'));
  assert.ok(studentWebappSource.includes('iconSvg("homework")'));
  assert.ok(studentWebappSource.includes('iconSvg("stats")'));
  assert.ok(studentWebappSource.includes('iconSvg("learn")'));
  assert.ok(studentWebappSource.includes('iconSvg("list")'));
  assert.ok(studentWebappSource.includes('iconSvg("words")'));
  assert.equal(studentWebappSource.includes('🔊'), false);
  assert.equal(studentWebappSource.includes('🐱'), false);
  assert.equal(studentWebappSource.includes('🎴'), false);
  assert.equal(studentWebappSource.includes('✏️'), false);
  assert.equal(studentWebappSource.includes('▥'), false);
});
