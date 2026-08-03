# Teacher WebApp Soft Lilac Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved soft lilac theme and bordered metadata badges to the teacher WebApp without changing teacher workflows or backend behavior.

**Architecture:** Keep the teacher WebApp's existing inline HTML and JavaScript unchanged. Replace only its inline CSS token system and component colors, protected by HTML regression assertions and verified against the production page in a browser.

**Tech Stack:** FastAPI inline HTML/CSS/JavaScript, pytest/TestClient, Ruff, Docker Compose, Nginx, browser console.

## Global Constraints

- Work in `/opt/english-teacher-bot` on `feat/mvp-foundation`.
- Modify presentation only in `app/api/teacher_webapp.py`.
- Keep teacher APIs, payloads, profile selection, tabs, manual card validation, deletion, publication, Telegram initialization, and backend status semantics unchanged.
- Use page background `#f7f5fa` and teacher primary accent `#746e9f`.
- Give `ученик / группа`, `+N новых слов`, and published-count badges visible 1 px borders.
- Keep primary actions darker than the student WebApp; use soft green for new-card badges and subdued rose for delete/error states.
- Do not print `.env`, Telegram IDs, tokens, or credentials.
- Confirm `SILENT_TELEGRAM_USER_IDS` is configured before deployment without printing its value.
- Remove `/design-preview/teacher-theme` only after production verification.

---

## File Map

- Modify `tests/test_foundation.py`: regression contract for teacher palette, bordered badges, focus states, and retained workflows.
- Modify `app/api/teacher_webapp.py`: teacher-only CSS token and component theme update.
- Modify `/etc/nginx/sites-available/englishtutorai.ru` outside Git after verification: remove the temporary preview location.
- Remove `/var/www/english-tutor-preview/teacher-theme.html` after verification.

### Task 1: Theme the teacher WebApp without changing behavior

**Files:**
- Modify: `tests/test_foundation.py:85-125`
- Modify: `app/api/teacher_webapp.py:6-66`

**Interfaces:**
- Consumes: existing `GET /teacher/cards` HTML response and existing teacher DOM classes.
- Produces: the same DOM and JavaScript behavior with a CSS-only soft lilac teacher theme.

- [ ] **Step 1: Add failing regression assertions**

Append these assertions to `test_teacher_cards_webapp_page_is_available` before the HEAD request:

```python
    assert "#f7f5fa" in response.text
    assert "#746e9f" in response.text
    assert "#dcebe2" in response.text
    assert "#f6e7e8" in response.text
    assert "var(--tg-theme-" not in response.text
    assert "--primary: #746e9f" in response.text
    assert ".badge-new" in response.text
    assert "border-color: var(--known-border)" in response.text
    assert ".badge-muted" in response.text
    assert "border-color: #d8d2e5" in response.text
    assert "input:focus, textarea:focus" in response.text
    assert "rgba(116, 110, 159, 0.14)" in response.text
```

Existing workflow assertions remain unchanged.

- [ ] **Step 2: Run the focused test and verify RED**

```bash
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_foundation.py::test_teacher_cards_webapp_page_is_available -q'
```

Expected: FAIL because the teacher page still contains Telegram theme variables and lacks `#746e9f`.

- [ ] **Step 3: Replace the teacher CSS with the approved theme**

Keep `SCRIPT` and the HTML response unchanged. Replace only `STYLE` in `app/api/teacher_webapp.py` with:

```python
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
"""
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the Step 2 command again.

Expected: `1 passed`.

- [ ] **Step 5: Run full verification**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests -q && ruff check app tests'
git diff --check
git diff --stat
git status --short
```

Expected: all tests pass, Ruff reports `All checks passed!`, and only the teacher WebApp plus its test are modified.

- [ ] **Step 6: Commit the implementation**

```bash
git add app/api/teacher_webapp.py tests/test_foundation.py
git commit -m "style: align teacher cards with lilac theme"
```

### Task 2: Deploy, browser-verify, remove preview, and push

**Files:**
- Verify: `app/api/teacher_webapp.py`
- Modify outside Git: `/etc/nginx/sites-available/englishtutorai.ru`
- Remove outside Git: `/var/www/english-tutor-preview/teacher-theme.html`

**Interfaces:**
- Consumes: the committed teacher CSS and current Docker Compose stack.
- Produces: verified production HTML at `/teacher/cards`, removed preview at `/design-preview/teacher-theme`, and a synchronized remote branch.

- [ ] **Step 1: Check safe deployment prerequisites**

```bash
test -f .env
grep -Eq '^SILENT_TELEGRAM_USER_IDS=.+' .env
git status --short --branch
```

Expected: silent-list check exits zero and only committed work is present. Do not print the value.

- [ ] **Step 2: Build and deploy**

```bash
docker compose up -d --build backend nginx
```

Expected: backend image builds, PostgreSQL is healthy, and backend starts.

- [ ] **Step 3: Verify production markers and health**

```bash
curl -fsS --retry 10 --retry-delay 2 https://englishtutorai.ru/health
curl -fsS --retry 10 --retry-delay 2 https://englishtutorai.ru/ready
page="$(curl -fsS https://englishtutorai.ru/teacher/cards)"
printf '%s' "$page" | grep -Fq '#746e9f'
printf '%s' "$page" | grep -Fq 'border-color: var(--known-border)'
printf '%s' "$page" | grep -Fq 'input:focus, textarea:focus'
if printf '%s' "$page" | grep -Fq 'var(--tg-theme-'; then exit 1; fi
docker compose ps
docker compose logs --since=3m --no-color backend
```

Expected: health is `ok`, ready is `ready`, all CSS markers match, and logs contain no startup errors.

- [ ] **Step 4: Browser-verify profiles and detail controls**

Open `https://englishtutorai.ru/teacher/cards`, then inject profile data in the browser console:

```javascript
profiles = [{
  id: 9001,
  name: "Анна Петрова",
  profile_type: "individual",
  new_card_count: 4,
  published_card_count: 28
}];
renderProfiles();
({
  badges: [...document.querySelectorAll(".badge")].map((el) => ({
    text: el.textContent.trim(),
    border: getComputedStyle(el).borderTopWidth,
    borderColor: getComputedStyle(el).borderTopColor,
  })),
  pageBackground: getComputedStyle(document.body).backgroundColor,
});
```

Expected: all three badges report `1px` borders; body background resolves to the approved pale lilac.

Then render a profile detail without API calls:

```javascript
selectedProfile = profiles[0];
currentTab = "draft";
draftCards = [{
  id: 9002,
  term: "thoughtful",
  translation_ru: "вдумчивый",
  example_sentence: "That was a thoughtful answer."
}];
publishedCards = [];
addFormOpen = true;
renderSelectedProfile();
({
  primaryBackground: getComputedStyle(document.querySelector(".primary")).backgroundColor,
  deleteBackground: getComputedStyle(document.querySelector(".danger")).backgroundColor,
  createDisabled: document.querySelector('[data-action="create-card"]').disabled,
  requiredFields: [...document.querySelectorAll('[data-add-word-form] input')].map((el) => el.name),
});
```

Expected: primary and delete colors resolve to muted colors, the create button remains disabled for blank required fields, and required inputs remain `new_term` and `new_translation_ru`. Visually inspect narrow width for wrapping, borders, no clipping, and no overlap.

- [ ] **Step 5: Remove the temporary preview**

Remove this exact Nginx block:

```nginx
    location = /design-preview/teacher-theme {
        alias /var/www/english-tutor-preview/teacher-theme.html;
        default_type text/html;
        add_header X-Robots-Tag "noindex, nofollow" always;
    }

```

Because the generic patch tool cannot write `/etc/nginx`, use a temporary Python script that requires exactly one occurrence before replacement:

```python
from pathlib import Path

path = Path("/etc/nginx/sites-available/englishtutorai.ru")
block = '''    location = /design-preview/teacher-theme {
        alias /var/www/english-tutor-preview/teacher-theme.html;
        default_type text/html;
        add_header X-Robots-Tag "noindex, nofollow" always;
    }

'''
content = path.read_text()
if content.count(block) != 1:
    raise SystemExit("teacher preview location is missing or duplicated")
path.write_text(content.replace(block, ""))
```

Then run:

```bash
python3 /tmp/remove_teacher_theme_preview.py
nginx -t
systemctl reload nginx
rm -f /var/www/english-tutor-preview/teacher-theme.html
code=$(curl -sS -o /dev/null -w '%{http_code}' https://englishtutorai.ru/design-preview/teacher-theme)
test "$code" = 404
```

Expected: Nginx config is valid and preview returns `404`.

- [ ] **Step 6: Fresh final verification and push**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests -q && ruff check app tests'
curl -fsS https://englishtutorai.ru/health
curl -fsS https://englishtutorai.ru/ready
nginx -t
git push
git status --short --branch
git rev-list --left-right --count origin/feat/mvp-foundation...HEAD
```

Expected: tests and Ruff pass, services are healthy, Nginx is valid, Git working tree is clean, and divergence is `0 0`.
