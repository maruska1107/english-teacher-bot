# Stable Student Cards and Soft Lilac Palette Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop student study-card content from shifting on flip, remove the duplicate `Не знаю` action, and apply the approved soft lilac light palette to `/student/cards`.

**Architecture:** Keep the existing FastAPI-generated HTML/CSS/JavaScript page and student progress API unchanged. Stabilize the UI with fixed CSS grid regions inside `.flashcard` and an always-present fixed-height `.study-actions` container below it; apply a page-local light color token set and render only `Ещё учу` and `Знаю` after the flip.

**Tech Stack:** Python 3.12, FastAPI, inline HTML/CSS/JavaScript, pytest, ruff, Docker Compose, Nginx.

## Global Constraints

- Work in `/opt/english-teacher-bot` on branch `feat/mvp-foundation`.
- Use strict TDD: add assertions first, run the focused test and observe the expected failure, then implement.
- Apply the visual change only to `/student/cards`; do not change the teacher WebApp.
- Do not change API contracts, database schema, or progress status values.
- `Ещё учу` sends `learning`; `Знаю` sends `known`.
- Use a consistent light palette for this iteration instead of Telegram theme colors.
- Keep `SILENT_TELEGRAM_USER_IDS` configured during development and deployment.
- Run tests Docker-first with source mounts.
- Do not print `.env`, tokens, passwords, OAuth credentials, or connection strings.
- Remove the temporary `/design-preview/cards` Nginx route only after the real student WebApp is deployed and browser-verified.

## File Map

- Modify `tests/test_foundation.py`: page-level regression requirements for actions, stable layout, and palette.
- Modify `app/api/student_webapp.py`: student-only CSS tokens, stable flashcard layout, fixed action area, and two-button study flow.
- Runtime cleanup `/etc/nginx/sites-available/englishtutorai.ru`: remove the temporary design-preview location after production verification.
- Runtime cleanup `/var/www/english-tutor-preview/index.html`: remove the temporary preview artifact after production verification.

---

### Task 1: Stable two-action study card with soft lilac palette

**Files:**
- Modify: `tests/test_foundation.py:128-192`
- Modify: `app/api/student_webapp.py:6-100, 219-263`

**Interfaces:**
- Consumes: existing `renderStudyCard()`, `flipCard()`, `updateProgress(cardId, progress)`, and `data-study-progress` click handling.
- Produces: `.flashcard` with fixed grid regions, `.study-actions` with a constant height, and exactly two study actions (`learning` and `known`).

- [ ] **Step 1: Write the failing page regression assertions**

In `test_student_cards_webapp_page_is_available`, replace the existing action/layout assertions:

```python
    assert "Не знаю" in response.text
    assert "Ещё учу" in response.text
    assert "Знаю" in response.text
    assert "min-height: 340px" in response.text
    assert "overflow-y: auto" in response.text
```

with:

```python
    assert "Не знаю" not in response.text
    assert "Ещё учу" in response.text
    assert "Знаю" in response.text
    assert response.text.count('data-study-progress="learning"') == 1
    assert response.text.count('data-study-progress="known"') == 1
    assert "height: 340px" in response.text
    assert "grid-template-rows: 24px 110px minmax(0, 1fr) 42px" in response.text
    assert ".flashcard-main" in response.text
    assert "overflow-y: auto" in response.text
    assert ".study-actions" in response.text
    assert "min-height: 64px" in response.text
    assert '<div class="actions study-actions">${actions}</div>' in response.text
    assert "#f7f5fa" in response.text
    assert "#8b86b4" in response.text
    assert "#f0dfd8" in response.text
    assert "#dcebe2" in response.text
    assert "var(--tg-theme-" not in response.text
```

These assertions define the approved two-action flow, stable layout markers, and selected palette.

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd /opt/english-teacher-bot && chmod -R a+rX tests app alembic pyproject.toml && docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_foundation.py::test_student_cards_webapp_page_is_available -q'
```

Expected: FAIL because `Не знаю` is still rendered and the fixed grid/action-area/palette markers are absent.

- [ ] **Step 3: Add the student-only light palette and stable layout CSS**

At the top of `STYLE`, replace the current root rule with these page-local tokens:

```css
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
```

Use these tokens in the existing selectors:

```css
body { background: var(--page-bg); color: var(--text); }
.lead, .status, .summary-line, .study-progress { color: var(--muted); }
.mode-button, .tab-active { background: var(--primary); color: #ffffff; border-color: var(--primary-border); }
.secondary-button { background: var(--primary-soft); color: var(--primary-soft-text); border-color: var(--border); }
.summary-card, .section-card, .list-card, .flashcard { background: var(--surface); border-color: var(--border); }
.summary-value, .flashcard-main, .list-card { color: var(--text); }
.card-mode-tab-active { background: #e7e3f0; color: #5f5980; }
.card-mode-tab, .filter-chip { background: #f0edf4; color: #625d70; }
.filter-chip-active { background: var(--badge-bg); color: var(--badge-text); }
.badge { background: var(--badge-bg); color: var(--badge-text); }
.learning { background: var(--learning-bg); color: var(--learning-text); border-color: var(--learning-border); }
.known { background: var(--known-bg); color: var(--known-text); border-color: var(--known-border); }
.error { background: var(--error-bg); color: var(--error-text); }
```

Replace every remaining `var(--tg-theme-...)` reference in `STYLE` with the corresponding local token above. The finished `/student/cards` page must not depend on Telegram theme colors in this light-theme iteration.

Make every button border explicit:

```css
button {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  font-weight: 800;
  cursor: pointer;
}
```

Remove the unused `.unknown` rule.

Replace the current centered flex layout in `.flashcard` with fixed regions:

```css
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
.study-actions {
  min-height: 64px;
  margin-top: 0;
  align-items: center;
}
```

- [ ] **Step 4: Render one fixed action area and remove the duplicate button**

In `renderStudyCard()`, replace the flipped action markup:

```javascript
  const actions = isFlipped
    ? `<div class="actions">
        <button class="unknown" data-study-progress="learning">Не знаю</button>
        <button class="learning" data-study-progress="learning">Ещё учу</button>
        <button class="known" data-study-progress="known">Знаю</button>
      </div>`
    : "";
```

with button-only content:

```javascript
  const actions = isFlipped
    ? `<button class="learning" data-study-progress="learning">Ещё учу</button>
       <button class="known" data-study-progress="known">Знаю</button>`
    : "";
```

Always render the stable action container after the card:

```javascript
    </article>
    <div class="actions study-actions">${actions}</div>`;
```

The empty front-side container is not focusable and occupies the same height as the flipped action row.

- [ ] **Step 5: Run the focused test and verify GREEN**

Run the same focused Docker command from Step 2.

Expected: `1 passed`.

- [ ] **Step 6: Run the full suite, linter, and diff checks**

Run:

```bash
cd /opt/english-teacher-bot && chmod -R a+rX tests app alembic pyproject.toml && docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests -q && ruff check app tests' && git diff --check
```

Expected: all 67 existing tests plus the updated regression assertions pass, ruff reports `All checks passed!`, and `git diff --check` exits 0.

- [ ] **Step 7: Commit the implementation**

```bash
git add app/api/student_webapp.py tests/test_foundation.py
git commit -m "fix: stabilize student study cards"
```

Expected: one implementation commit containing only the student WebApp and its page regression test.

---

### Task 2: Deploy, browser-verify geometry, and remove the preview

**Files:**
- Runtime: `/opt/english-teacher-bot` Docker services.
- Runtime modify: `/etc/nginx/sites-available/englishtutorai.ru`.
- Runtime remove: `/var/www/english-tutor-preview/index.html`.

**Interfaces:**
- Consumes: production `/student/cards`, global JavaScript functions `renderStudyCard()` and `flipCard()`, and health endpoints.
- Produces: verified production student WebApp, removed temporary preview route, and pushed Git history.

- [ ] **Step 1: Confirm safety prerequisites without printing secrets**

Run:

```bash
cd /opt/english-teacher-bot && \
  test -f .env && \
  grep -Eq '^SILENT_TELEGRAM_USER_IDS=.+' .env && \
  git status --short --branch
```

Expected: the silent-list check exits 0 and the branch shows only committed changes.

- [ ] **Step 2: Build and restart the backend**

Run as a tracked background process if the terminal classifies Compose as long-lived:

```bash
cd /opt/english-teacher-bot && docker compose up -d --build backend nginx
```

Expected: image build exits 0 and the backend container is recreated and started.

- [ ] **Step 3: Verify service health and deployed page markers**

Run:

```bash
curl -fsS --retry 10 --retry-delay 2 https://englishtutorai.ru/health
curl -fsS --retry 10 --retry-delay 2 https://englishtutorai.ru/ready
page="$(curl -fsS https://englishtutorai.ru/student/cards)"
printf '%s' "$page" | grep -Fq 'grid-template-rows: 24px 110px minmax(0, 1fr) 42px'
printf '%s' "$page" | grep -Fq '<div class="actions study-actions">${actions}</div>'
printf '%s' "$page" | grep -Fq '#8b86b4'
if printf '%s' "$page" | grep -Fq 'Не знаю'; then exit 1; fi
```

Expected: health is `ok`, readiness is `ready`, all selected design markers exist, and `Не знаю` is absent.

- [ ] **Step 4: Verify fixed geometry and actions in the live browser**

Open `https://englishtutorai.ru/student/cards`, then evaluate this expression with the browser console:

```javascript
(() => {
  allCards = [{
    id: 999001,
    term: "journey",
    translation_ru: "путешествие",
    example_sentence: "A deliberately long example that remains inside the details region. ".repeat(12),
    status: "new",
  }];
  currentSection = "cards";
  currentCardMode = "study";
  currentIndex = 0;
  isFlipped = false;
  renderStudyCard();
  const frontCard = studyEl.querySelector("[data-flashcard]").getBoundingClientRect();
  const frontMain = studyEl.querySelector(".flashcard-main").getBoundingClientRect();
  const frontActions = studyEl.querySelector(".study-actions").getBoundingClientRect();
  flipCard();
  const backCard = studyEl.querySelector("[data-flashcard]").getBoundingClientRect();
  const backMain = studyEl.querySelector(".flashcard-main").getBoundingClientRect();
  const backActions = studyEl.querySelector(".study-actions").getBoundingClientRect();
  const details = studyEl.querySelector(".flashcard-extra");
  return {
    cardTopDelta: backCard.top - frontCard.top,
    cardHeightDelta: backCard.height - frontCard.height,
    mainTopDelta: backMain.top - frontMain.top,
    mainHeightDelta: backMain.height - frontMain.height,
    actionsTopDelta: backActions.top - frontActions.top,
    actionsHeightDelta: backActions.height - frontActions.height,
    buttons: [...studyEl.querySelectorAll("[data-study-progress]")].map((button) => button.textContent.trim()),
    detailsScrollContained: details.scrollHeight >= details.clientHeight,
  };
})()
```

Expected:

```json
{
  "cardTopDelta": 0,
  "cardHeightDelta": 0,
  "mainTopDelta": 0,
  "mainHeightDelta": 0,
  "actionsTopDelta": 0,
  "actionsHeightDelta": 0,
  "buttons": ["Ещё учу", "Знаю"],
  "detailsScrollContained": true
}
```

- [ ] **Step 5: Remove the temporary public preview**

Remove only this block from `/etc/nginx/sites-available/englishtutorai.ru`:

```nginx
    location = /design-preview/cards {
        alias /var/www/english-tutor-preview/index.html;
        default_type text/html;
        add_header X-Robots-Tag "noindex, nofollow" always;
    }
```

Use an exact guarded replacement, then validate, reload, and remove the artifact:

```bash
python3 - <<'PY'
from pathlib import Path

path = Path("/etc/nginx/sites-available/englishtutorai.ru")
block = '''    location = /design-preview/cards {
        alias /var/www/english-tutor-preview/index.html;
        default_type text/html;
        add_header X-Robots-Tag "noindex, nofollow" always;
    }

'''
content = path.read_text()
if content.count(block) != 1:
    raise SystemExit("design preview location is missing or duplicated")
path.write_text(content.replace(block, ""))
PY
nginx -t
systemctl reload nginx
rm -f /var/www/english-tutor-preview/index.html
curl -sS -o /dev/null -w '%{http_code}\n' https://englishtutorai.ru/design-preview/cards
```

Expected: Nginx syntax succeeds and the preview URL no longer returns `200` (it should fall through to the backend and return `404`).

- [ ] **Step 6: Run final production and repository verification**

Run:

```bash
cd /opt/english-teacher-bot && \
  curl -fsS https://englishtutorai.ru/health && printf '\n' && \
  curl -fsS https://englishtutorai.ru/ready && printf '\n' && \
  docker compose ps && \
  git status --short --branch && \
  git log --oneline -3
```

Expected: backend/nginx/PostgreSQL are running, PostgreSQL is healthy, health/readiness pass, and the worktree is clean.

- [ ] **Step 7: Push the approved design and implementation commits**

```bash
cd /opt/english-teacher-bot && git push
```

Expected: branch `feat/mvp-foundation` is updated on `origin` with the design and implementation commits.
