'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const pythonSource = fs.readFileSync('app/api/teacher_webapp.py', 'utf8');
const scriptStart = pythonSource.indexOf('SCRIPT = """') + 'SCRIPT = """'.length;
const scriptEnd = pythonSource.indexOf('\n"""', scriptStart);
assert.ok(scriptStart >= 'SCRIPT = """'.length && scriptEnd > scriptStart, 'teacher SCRIPT must be extractable');
const browserSource = pythonSource.slice(scriptStart, scriptEnd);

function extractFunction(name) {
  const marker = `function ${name}(`;
  const markerStart = browserSource.indexOf(marker);
  assert.notEqual(markerStart, -1, `${name} must exist`);
  const start = browserSource.slice(Math.max(0, markerStart - 6), markerStart) === 'async '
    ? markerStart - 6
    : markerStart;
  const bodyStart = browserSource.indexOf('{', markerStart);
  let depth = 0;
  let quote = '';
  let escaped = false;
  for (let index = bodyStart; index < browserSource.length; index += 1) {
    const char = browserSource[index];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (char === '"' || char === "'" || char === '`') {
      quote = char;
    } else if (char === '{') {
      depth += 1;
    } else if (char === '}') {
      depth -= 1;
      if (depth === 0) return browserSource.slice(start, index + 1);
    }
  }
  throw new Error(`unterminated function ${name}`);
}

function contextWith(functionNames, setup = '') {
  const context = vm.createContext({ AbortController, URL });
  vm.runInContext(`${setup}\n${functionNames.map(extractFunction).join('\n')}`, context);
  return context;
}

function evaluate(context, expression) {
  return vm.runInContext(expression, context);
}

test('pagination replaces batches and honors the final 303 boundary', () => {
  const context = contextWith(['imageOptionsRequestOffset', 'imageOptionsPage']);
  const result = evaluate(context, `(() => {
    const first = imageOptionsPage({ options: [] }, { options: [1, 2, 3, 99], next_offset: 3 }, 0);
    const second = imageOptionsPage(first, { options: [4, 5, 6], next_offset: 6 }, 3);
    const last = imageOptionsPage(second, { options: [7, 8, 9], next_offset: 303 }, 300);
    return { first, second, last, request300: imageOptionsRequestOffset({ nextOffset: 300 }, true),
      request303: imageOptionsRequestOffset(last, true) };
  })()`);
  assert.deepEqual(Array.from(result.first.options), [1, 2, 3]);
  assert.deepEqual(Array.from(result.second.options), [4, 5, 6]);
  assert.equal(result.request300, 300);
  assert.equal(result.last.hasMore, false);
  assert.equal(result.request303, null);
});

test('request generation invalidates and aborts stale image option responses', () => {
  const context = contextWith(
    ['beginImageOptionsRequest', 'isCurrentImageOptionsRequest', 'cancelImageOptionsRequest'],
    'const imageOptionsState = new Map(); let imageOptionsRequestGeneration = 0;',
  );
  const result = evaluate(context, `(() => {
    imageOptionsState.set(7, { open: true, options: [] });
    const oldRequest = beginImageOptionsRequest(7);
    const replacement = beginImageOptionsRequest(7);
    const oldAfterReplacement = isCurrentImageOptionsRequest(7, oldRequest.token);
    const replacementWasCurrent = isCurrentImageOptionsRequest(7, replacement.token);
    cancelImageOptionsRequest(7);
    return { oldAborted: oldRequest.controller.signal.aborted, oldAfterReplacement,
      replacementWasCurrent, replacementAborted: replacement.controller.signal.aborted,
      currentAfterCancel: isCurrentImageOptionsRequest(7, replacement.token) };
  })()`);
  assert.deepEqual(JSON.parse(JSON.stringify(result)), {
    oldAborted: true,
    oldAfterReplacement: false,
    replacementWasCurrent: true,
    replacementAborted: true,
    currentAfterCancel: false,
  });
});

test('retry loading state clears an old error and leaves controls recoverable', () => {
  const context = contextWith(['imageOptionsLoadingState']);
  const state = evaluate(context, 'imageOptionsLoadingState({ open: false, error: "failed", empty: true, loading: false })');
  assert.equal(state.open, true);
  assert.equal(state.error, '');
  assert.equal(state.empty, false);
  assert.equal(state.loading, true);
});

test('closing and reopening retries offset zero after pagination or selection errors', async () => {
  const context = contextWith(
    [
      'imageOptionsRequestOffset',
      'imageOptionsPage',
      'imageOptionsLoadingState',
      'beginImageOptionsRequest',
      'isCurrentImageOptionsRequest',
      'loadImageOptions',
      'toggleImageOptions',
    ],
    `const imageOptionsState = new Map();
    let imageOptionsRequestGeneration = 0;
    const requests = [];
    function syncDraftEditsFromDom() {}
    function renderSelectedProfile() {}
    async function api(path) {
      const state = imageOptionsState.get(7);
      requests.push({ path, error: state.error, loading: state.loading });
      return { options: [], next_offset: 3 };
    }`,
  );
  const result = await evaluate(context, `(async () => {
    const outcomes = [];
    for (const error of [
      'Не удалось загрузить картинки. Попробуйте ещё раз.',
      'Не удалось выбрать картинку. Попробуйте ещё раз.',
    ]) {
      imageOptionsState.set(7, {
        open: true,
        options: [{ image_id: 'cached' }],
        nextOffset: 6,
        error,
        loading: false,
      });
      await toggleImageOptions(7);
      await toggleImageOptions(7);
      outcomes.push({ state: imageOptionsState.get(7), request: requests.at(-1) });
    }
    return { outcomes, requestCount: requests.length };
  })()`);

  assert.equal(result.requestCount, 2);
  for (const outcome of result.outcomes) {
    assert.equal(outcome.request.path, '/api/teacher/cards/7/image-options?offset=0');
    assert.equal(outcome.request.error, '');
    assert.equal(outcome.request.loading, true);
    assert.equal(outcome.state.error, '');
  }
});

test('broken selected image hides its complete region including attribution', () => {
  const context = contextWith(['hideBrokenImageRegion']);
  const result = evaluate(context, `(() => {
    const area = { hidden: false };
    const image = { removed: [], closest: selector => selector === '.card-image-area' ? area : null,
      removeAttribute(name) { this.removed.push(name); } };
    hideBrokenImageRegion(image);
    return { hidden: area.hidden, removed: image.removed };
  })()`);
  assert.equal(result.hidden, true);
  assert.deepEqual(Array.from(result.removed), ['src']);
});

test('image templates reject unsafe URLs, escape attribution, and use no inline event handlers', () => {
  const context = contextWith(
    ['escapeHtml', 'safeHttpsUrl', 'imageAttributionTemplate', 'cardImageTemplate'],
  );
  const result = evaluate(context, `(() => ({
    unsafe: safeHttpsUrl('javascript:alert(1)'),
    html: cardImageTemplate({ image_url: 'https://images.test/x.jpg?x=<bad>',
      image_source_url: 'https://source.test/x?y=<bad>', image_creator: '<img src=x onerror=alert(1)>',
      image_license: 'by<script>', image_license_url: 'https://license.test/by' })
  }))()`);
  assert.equal(result.unsafe, '');
  assert.ok(result.html.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(result.html.includes('&lt;script&gt;'));
  assert.ok(!result.html.includes('<script>'));
  assert.ok(!/<[^>]+\son(?:error|load|click)=/i.test(result.html));
  assert.ok(result.html.includes('rel="noopener noreferrer"'));
});

test('all image management controls are disabled while an image request is busy', () => {
  assert.match(browserSource, /class="image-option"[^`]*\$\{state\.loading \? "disabled" : ""\}/s);
  assert.match(browserSource, /data-action="toggle-images"[^`]*\$\{imageBusy \? "disabled" : ""\}/s);
  assert.match(browserSource, /data-action="remove-image"[^`]*imageBusy/s);
  assert.match(browserSource, /data-action="more-images"[^`]*state\.loading/s);
});

test('teacher card UI omits hidden fields while preserving their values in update payloads', () => {
  for (const label of ['Определение на английском', 'Фраза из урока', 'Уровень']) {
    assert.equal(browserSource.includes(`<label>${label}</label>`), false, label);
  }
  assert.doesNotMatch(browserSource, /card\.definition_en\s*\?\s*`<p class="readonly-line"/);

  const context = contextWith(
    ['payloadFromCard'],
    `const draftCards = [{ id: 7, definition_en: 'kept definition', source_phrase: 'kept phrase', level: 'B1' }];`,
  );
  const payload = evaluate(context, `payloadFromCard({
    dataset: { cardId: '7' },
    querySelector(selector) {
      const values = { term: 'journey', translation_ru: 'путешествие', example_sentence: 'A long journey.' };
      const field = selector.match(/name="([^\\"]+)"/)[1];
      return { value: values[field] };
    }
  })`);
  assert.deepEqual(JSON.parse(JSON.stringify(payload)), {
    term: 'journey',
    translation_ru: 'путешествие',
    example_sentence: 'A long journey.',
    definition_en: 'kept definition',
    source_phrase: 'kept phrase',
    level: 'B1',
  });
});

test('teacher webapp exposes lesson review section and confirmation API', () => {
  assert.ok(pythonSource.includes('✨ На проверку'));
  assert.ok(pythonSource.includes('👥 Ученики'));
  assert.ok(pythonSource.includes('📚 Уроки'));
  assert.ok(pythonSource.includes('⚙️ Настройки'));
  assert.ok(pythonSource.includes('/api/teacher/lesson-reviews'));
  assert.ok(pythonSource.includes('/confirm'));
  assert.ok(pythonSource.includes('Подтвердить и отправить'));
});

test('teacher student detail keeps top nav stable and uses inner student tabs', () => {
  assert.ok(pythonSource.includes('data-student-tab="cards"'));
  assert.ok(pythonSource.includes('data-student-tab="homework"'));
  assert.ok(pythonSource.includes('data-student-tab="lessons"'));
  assert.ok(pythonSource.includes('/api/teacher/homework?profile_id='));
  assert.ok(pythonSource.includes('Новые карточки:'));
  assert.equal(browserSource.includes('Новых карточек:'), false);
  const renderSelectedProfile = extractFunction('renderSelectedProfile');
  assert.equal(renderSelectedProfile.includes('id="top-tabs"'), false);
  assert.equal(renderSelectedProfile.includes('👥 Ученики'), false);
  assert.ok(renderSelectedProfile.includes('Карточки'));
  assert.ok(renderSelectedProfile.includes('Домашка'));
  assert.ok(renderSelectedProfile.includes('Уроки'));
});

test('teacher student detail unifies student tabs and active content in one panel', () => {
  const renderSelectedProfile = extractFunction('renderSelectedProfile');
  assert.ok(renderSelectedProfile.includes('student-workspace'));
  assert.ok(renderSelectedProfile.includes('${content}'));
  assert.equal(renderSelectedProfile.includes('<section class="panel">\n      <h2>${escapeHtml(selectedProfile.name)}</h2>'), false);
  assert.equal(renderSelectedProfile.includes('${content}`;'), false);
  const profileTemplate = extractFunction('profileTemplate');
  assert.ok(profileTemplate.includes('profileTypeLabel(profile)'));
  assert.equal(profileTemplate.includes('new_card_count'), false);
  assert.equal(profileTemplate.includes('published_card_count'), false);
});
