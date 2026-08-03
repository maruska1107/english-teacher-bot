# Openverse Images for Vocabulary Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically attach an openly licensed Openverse image to each newly created draft card, let teachers replace or remove it, and show it on both sides of the stable student study card.

**Architecture:** Add nullable image metadata to `VocabularyCard`, isolate Openverse HTTP/parsing in a new async service, and let only the backend call Openverse. Automatic enrichment is best-effort after the card itself is committed; teacher selection sends an Openverse image ID that the server re-fetches and validates. Both WebApps consume the same serialized metadata without storing image files locally.

**Tech Stack:** Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, httpx, inline HTML/CSS/JavaScript, pytest, Docker Compose, PostgreSQL, Nginx.

## Global Constraints

- Work in `/opt/english-teacher-bot` on `feat/mvp-foundation`.
- Apply automatic lookup only to cards created after deployment; do not backfill old rows.
- Do not store image binaries in PostgreSQL, local disk, Docker volumes, or Git.
- Allow only Openverse licenses `cc0`, `pdm`, `by`, and `by-sa` and HTTPS URLs.
- Always preserve and display creator/source/license attribution; creator may be absent only when Openverse omits it.
- Never send teacher/student identity or Telegram data to Openverse.
- Openverse errors, timeouts, malformed responses, empty results, database errors during optional enrichment, and `429` responses must not fail card creation.
- Students must never trigger Openverse API requests.
- Teacher image mutations require ownership and `draft` status.
- Student image cards use height `460px`, image height `126px`, and zero geometry delta on flip.
- Existing cards without images retain their current behavior.
- Confirm `SILENT_TELEGRAM_USER_IDS` without printing it before production deployment.
- Remove `/design-preview/student-image-card` only after production verification.

---

## File Map

- Create `alembic/versions/0006_vocabulary_card_images.py`: six nullable image metadata columns.
- Modify `app/models/vocabulary_card.py`: ORM mappings.
- Modify `app/schemas/cards.py`: shared teacher image fields and teacher image-operation schemas.
- Modify `app/schemas/student_cards.py`: nullable student image metadata.
- Modify `app/repositories/vocabulary_cards.py`: set/clear image metadata.
- Create `app/services/openverse_images.py`: query building, HTTP calls, filtering, candidate conversion, best-effort enrichment.
- Modify `app/core/config.py`: non-secret Openverse settings.
- Modify `app/analysis/service.py`: enrich newly generated lesson cards after their base transaction succeeds.
- Modify `app/api/teacher_cards.py`: serialization, manual-card enrichment, options/select/remove endpoints.
- Modify `app/api/student_cards.py`: image metadata serialization only.
- Modify `app/api/teacher_webapp.py`: selected thumbnail, attribution, alternatives, replace/remove/show-more UI.
- Modify `app/api/student_webapp.py`: fixed image region on both sides and broken-image fallback.
- Create `tests/test_openverse_images.py`: service unit tests.
- Modify `tests/test_teacher_cards_api.py`, `tests/test_student_cards_api.py`, `tests/test_analysis_service.py`, and `tests/test_foundation.py`: API/integration/UI regression tests.

### Task 1: Persist and serialize nullable image metadata

**Files:**
- Create: `alembic/versions/0006_vocabulary_card_images.py`
- Modify: `app/models/vocabulary_card.py`
- Modify: `app/schemas/cards.py`
- Modify: `app/schemas/student_cards.py`
- Modify: `app/repositories/vocabulary_cards.py`
- Test: `tests/test_teacher_cards_api.py`
- Test: `tests/test_student_cards_api.py`

**Interfaces:**
- Produces ORM fields `image_url`, `image_source_url`, `image_creator`, `image_license`, `image_license_url`, `image_search_query` as nullable strings/text.
- Produces repository methods `set_image(card, candidate, search_query)` and `clear_image(card)`.

- [ ] **Step 1: Write failing serialization and repository tests**

Add image metadata to the seeded published card and assert both teacher and student JSON include all six nullable fields. Add a repository test:

```python
candidate = CardImageCandidate(
    image_id="openverse-1",
    image_url="https://api.openverse.org/v1/images/openverse-1/thumb/",
    source_url="https://example.org/source",
    creator="Alice",
    license="by",
    license_url="https://creativecommons.org/licenses/by/4.0/",
)
repository.set_image(draft_card, candidate, "journey travel")
assert draft_card.image_creator == "Alice"
repository.clear_image(draft_card)
assert draft_card.image_url is None
assert draft_card.image_search_query == "journey travel"
```

`clear_image` intentionally preserves `image_search_query` for later replacement.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_teacher_cards_api.py tests/test_student_cards_api.py -q'
```

Expected: failures for missing image schema/model fields and repository methods.

- [ ] **Step 3: Add migration, ORM fields, schemas, and repository methods**

Create revision `0006_vocabulary_card_images`, down revision `0005_learning_profiles_cards`, adding/removing these nullable columns:

```python
COLUMNS = (
    ("image_url", sa.Text()),
    ("image_source_url", sa.Text()),
    ("image_creator", sa.String(length=255)),
    ("image_license", sa.String(length=50)),
    ("image_license_url", sa.Text()),
    ("image_search_query", sa.Text()),
)
```

Define schemas:

```python
class CardImageCandidate(BaseModel):
    image_id: str
    image_url: str
    source_url: str
    creator: str | None = None
    license: Literal["cc0", "pdm", "by", "by-sa"]
    license_url: str | None = None

class CardImageOptionsResponse(BaseModel):
    options: list[CardImageCandidate]
    next_offset: int

class CardImageSelection(BaseModel):
    image_id: str = Field(min_length=1, max_length=100)
```

Add the six nullable metadata properties to `VocabularyCardRead` and `StudentCardRead`. Implement repository mapping from `CardImageCandidate`, and clear only the five selected-image fields while retaining the search query.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: pass.

- [ ] **Step 5: Verify migration without touching production PostgreSQL**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/alembic:/app/alembic:ro" backend \
  -c 'python -m compileall -q alembic/versions/0006_vocabulary_card_images.py'
python3 -c 'from pathlib import Path; p=Path("alembic/versions/0006_vocabulary_card_images.py").read_text(); assert "0005_learning_profiles_cards" in p and p.count("op.add_column") == 6 and p.count("op.drop_column") == 6'
```

Expected: both commands exit `0`. The migration is applied to PostgreSQL only during Task 5 deployment.

- [ ] **Step 6: Commit**

```bash
git add alembic/versions/0006_vocabulary_card_images.py app/models/vocabulary_card.py \
  app/schemas/cards.py app/schemas/student_cards.py app/repositories/vocabulary_cards.py \
  tests/test_teacher_cards_api.py tests/test_student_cards_api.py
git commit -m "feat: store vocabulary card image metadata"
```

### Task 2: Add the Openverse client and best-effort automatic enrichment

**Files:**
- Create: `app/services/openverse_images.py`
- Create: `tests/test_openverse_images.py`
- Modify: `app/core/config.py`
- Modify: `app/analysis/service.py`
- Modify: `app/api/teacher_cards.py`
- Modify: `tests/test_analysis_service.py`
- Modify: `tests/test_teacher_cards_api.py`

**Interfaces:**
- Produces `build_image_query(card) -> str`.
- Produces async `OpenverseImageClient.search(query, offset=0, limit=3) -> list[CardImageCandidate]`.
- Produces async `OpenverseImageClient.get(image_id) -> CardImageCandidate | None`.
- Produces async `enrich_card_image(session, card, settings, client) -> bool`.
- Produces FastAPI dependency `get_openverse_image_client(settings) -> OpenverseImageClient`.

- [ ] **Step 1: Write failing Openverse unit tests**

Use `httpx.MockTransport` and assert:

```python
assert build_image_query(card) == "journey"
assert request.headers["user-agent"] == "EnglishTutorAI/0.1 (support@englishtutorai.ru)"
assert request.url.params["license_type"] == "commercial"
assert request.url.params["license"] == "cc0,pdm,by,by-sa"
```

Return a mixed payload and assert only HTTPS candidates with licenses in `{"cc0", "pdm", "by", "by-sa"}` survive. Add separate tests for timeout, `429`, malformed JSON, missing source URL, and empty results; each returns `[]` or `None` without raising.

- [ ] **Step 2: Run tests and verify RED**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_openverse_images.py -q'
```

Expected: import failure because the service does not exist.

- [ ] **Step 3: Implement settings and client**

Add settings:

```python
openverse_images_enabled: bool = True
openverse_api_base_url: str = "https://api.openverse.org/v1"
openverse_timeout_seconds: float = 4.0
openverse_result_page_size: int = 3
openverse_batch_concurrency: int = 2
openverse_user_agent: str = "EnglishTutorAI/0.1 (support@englishtutorai.ru)"
```

`search` maps `offset` to `page = offset // limit + 1`, sends `q`, `page`, `page_size`, `license_type=commercial`, and the explicit license allowlist. Catch `httpx.HTTPError`, JSON/value errors, and non-200/`429` responses; log a short warning and return no candidates. Process and return no more than the effective requested limit even if an upstream response contains extra rows.

`get(image_id)` URL-quotes the ID, fetches `/images/{id}/`, and applies the same candidate validator. Candidate extraction prefers `thumbnail`, then `url`, and requires HTTPS `foreign_landing_url`.

- [ ] **Step 4: Implement best-effort enrichment**

```python
async def enrich_card_image(session, card, settings, client) -> bool:
    if not settings.openverse_images_enabled:
        return False
    query = build_image_query(card)
    card.image_search_query = query
    options = await client.search(query=query, offset=0, limit=1)
    if not options:
        session.flush()
        return False
    VocabularyCardRepository(session).set_image(card, options[0], query)
    return True
```

For manual creation, convert `create_card` to `async def`, commit the base card first, then call enrichment and commit again. In tests, set `openverse_images_enabled=False` in existing helpers; add one explicit test using `app.dependency_overrides[get_openverse_image_client]` with a fake client.

For lesson analysis, inject an optional image client into `AnalysisService`, have `_save_draft_vocabulary_cards` return the created cards, and commit analysis/cards first. Gather only external lookups under `asyncio.Semaphore(settings.openverse_batch_concurrency)` without sharing a SQLAlchemy session across coroutines; then apply each result sequentially. Isolate each optional metadata transaction with rollback on database failure. Existing tests use `openverse_images_enabled=False`; one new test injects a fake client and verifies only newly returned cards are enriched.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_openverse_images.py tests/test_analysis_service.py tests/test_teacher_cards_api.py -q'
```

Expected: pass with no external network access.

- [ ] **Step 6: Commit**

```bash
git add app/services/openverse_images.py app/core/config.py app/analysis/service.py \
  app/api/teacher_cards.py tests/test_openverse_images.py tests/test_analysis_service.py \
  tests/test_teacher_cards_api.py
git commit -m "feat: enrich new cards with Openverse images"
```

### Task 3: Add secure teacher image options, selection, removal, and UI

**Files:**
- Modify: `app/api/teacher_cards.py`
- Modify: `app/api/teacher_webapp.py`
- Modify: `tests/test_teacher_cards_api.py`
- Modify: `tests/test_foundation.py`

**Interfaces:**
- Produces `GET /api/teacher/cards/{card_id}/image-options?offset=N`.
- Produces `PUT /api/teacher/cards/{card_id}/image` with `{ "image_id": "..." }`.
- Produces `DELETE /api/teacher/cards/{card_id}/image`.

- [ ] **Step 1: Write failing endpoint and page tests**

API tests use a fake client and assert:

- options returns three candidates plus `next_offset=3`;
- selection re-fetches the candidate by ID and persists server-returned metadata;
- removal clears selected metadata but retains the search query;
- another teacher receives `404`;
- published cards receive `409` for all mutation/search endpoints;
- missing or rejected Openverse IDs receive `422`;
- no arbitrary image URL is accepted by `PUT`.

Page tests assert these markers:

```python
assert "Заменить картинку" in response.text
assert "Убрать картинку" in response.text
assert "Показать ещё" in response.text
assert "image-options" in response.text
assert "image_id" in response.text
assert "image_source_url" in response.text
assert "escapeHtml(card.image_creator" in response.text
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_teacher_cards_api.py tests/test_foundation.py::test_teacher_cards_webapp_page_is_available -q'
```

Expected: 404/missing marker failures.

- [ ] **Step 3: Implement endpoints**

Use one helper:

```python
def get_teacher_draft_card_or_404(session, teacher, card_id):
    card = VocabularyCardRepository(session).get_for_teacher(teacher.id, card_id)
    if card is None:
        raise HTTPException(404, "Card not found")
    if card.status != "draft":
        raise HTTPException(409, "Only draft card images can be changed")
    return card
```

Options uses `card.image_search_query or build_image_query(card)`, clamps `offset` to `0..300`, and requests exactly three. Selection accepts only `image_id`, calls `client.get`, rejects missing candidates with `422`, and persists server-fetched metadata. Removal calls `clear_image`.

- [ ] **Step 4: Implement teacher UI**

In each draft card render a fixed thumbnail when `image_url` exists, escaped compact attribution links, and bordered actions `Заменить картинку` / `Убрать картинку`. Maintain per-card transient state:

```javascript
const imageOptionState = new Map();
// cardId -> { options: [], nextOffset: 0, loading: false }
```

`Заменить` calls options offset `0`; `Показать ещё` calls `nextOffset`; choosing a tile sends only `{ image_id: option.image_id }`; remove sends DELETE. After selection/removal, replace the matching object in `draftCards` and rerender. Use `escapeHtml` for all creator/license text and `encodeURI` only on server-validated HTTPS URLs.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add app/api/teacher_cards.py app/api/teacher_webapp.py tests/test_teacher_cards_api.py tests/test_foundation.py
git commit -m "feat: let teachers manage card images"
```

### Task 4: Show attributed images on both student card sides without jumps

**Files:**
- Modify: `app/api/student_cards.py`
- Modify: `app/api/student_webapp.py`
- Modify: `tests/test_student_cards_api.py`
- Modify: `tests/test_foundation.py`

**Interfaces:**
- Consumes nullable image metadata from `StudentCardRead`.
- Produces an image-enabled `460px` study card with a `126px` image and unchanged `learning`/`known` progress actions.

- [ ] **Step 1: Write failing API/UI assertions**

Add student JSON expectations for all image fields. Page assertions:

```python
assert "height: 460px" in response.text
assert "height: 126px" in response.text
assert ".flashcard-image" in response.text
assert "object-fit: cover" in response.text
assert "handleImageError" in response.text
assert "image_source_url" in response.text
assert "image_license_url" in response.text
assert "Фото:" in response.text
```

Retain assertions for exactly one `learning` and one `known` action and for the fixed action area.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_student_cards_api.py tests/test_foundation.py::test_student_cards_webapp_page_is_available -q'
```

Expected: missing image JSON and HTML/CSS markers.

- [ ] **Step 3: Serialize student metadata and implement the stable image layout**

Add image fields in `student_cards.card_to_response`. In study rendering, build one escaped image block before side-specific word/translation text, so the same block is present on both flips. Cards with images receive class `flashcard-with-image` and grid:

```css
.flashcard-with-image {
  height: 460px;
  grid-template-rows: 24px 152px 82px minmax(0, 1fr) 36px;
}
.flashcard-image { width: 100%; height: 126px; object-fit: cover; border: 1px solid var(--border); border-radius: 16px; }
```

The wrapper includes a compact source link and a separate license link. `handleImageError(img)` hides the wrapper and adds `flashcard-image-failed`; it does not throw or alter progress handlers. Cards without metadata retain the existing `340px` grid.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Step 2 command. Expected: pass.

- [ ] **Step 5: Run the complete pre-deploy gate**

```bash
./scripts/test_all.sh
git diff --check
git status --short
```

Expected: the canonical gate runs all Python tests, every `tests/js/*.test.js` security/behavior test, and Ruff; all checks pass.

- [ ] **Step 6: Commit**

```bash
git add app/api/student_cards.py app/api/student_webapp.py tests/test_student_cards_api.py tests/test_foundation.py
git commit -m "feat: show images on student study cards"
```

### Task 5: Deploy, verify real Openverse behavior, remove preview, and push

**Files:**
- Verify production application and database.
- Modify outside Git: `/etc/nginx/sites-available/englishtutorai.ru`.
- Remove outside Git: `/var/www/english-tutor-preview/student-image-card.html`.

- [ ] **Step 1: Confirm deployment safety and run migrations/build**

```bash
test -f .env
grep -Eq '^SILENT_TELEGRAM_USER_IDS=.+' .env
docker compose up -d --build backend nginx
```

Expected: migration `0006_vocabulary_card_images` applies and backend starts.

- [ ] **Step 2: Verify service and real Openverse access**

```bash
curl -fsS --retry 10 --retry-delay 2 https://englishtutorai.ru/health
curl -fsS --retry 10 --retry-delay 2 https://englishtutorai.ru/ready
docker compose exec -T backend python -c "import asyncio; from app.core.config import Settings; from app.services.openverse_images import OpenverseImageClient; s=Settings(); print(asyncio.run(OpenverseImageClient(s).search('apple fruit', 0, 1))[0].license)"
docker compose ps
docker compose logs --since=5m --no-color backend
```

Expected: health/ready succeed, the live API returns one allowed license, PostgreSQL is healthy, and logs have no startup errors.

- [ ] **Step 3: Browser-verify teacher workflow**

Use controlled test data in the live page or a newly created dev card. Confirm automatic thumbnail, attribution, three alternatives, selection, `Показать ещё`, removal, disabled mutation for published cards, and no layout overlap on mobile width. Never publish or delete a real user's card during verification.

- [ ] **Step 4: Browser-verify student geometry**

Inject one card with the real Openverse mockup metadata into the live student page, render front, measure card/image/main/action rectangles, flip, and measure again. Required deltas:

```text
cardTopDelta = 0
cardHeightDelta = 0
imageTopDelta = 0
imageHeightDelta = 0
mainTopDelta = 0
actionsTopDelta = 0
```

Also set an invalid image URL and confirm the card remains usable and progress buttons still render.

- [ ] **Step 5: Remove temporary preview**

Remove the exact Nginx location for `/design-preview/student-image-card` with a checked Python replacement, run `nginx -t`, reload Nginx, delete `/var/www/english-tutor-preview/student-image-card.html`, and assert the URL returns `404`.

- [ ] **Step 6: Fresh final verification and push**

```bash
./scripts/test_all.sh
curl -fsS https://englishtutorai.ru/health
curl -fsS https://englishtutorai.ru/ready
nginx -t
git push
git status --short --branch
git rev-list --left-right --count origin/feat/mvp-foundation...HEAD
```

Expected: tests and Ruff pass, services are healthy, preview is gone, working tree is clean, and divergence is `0 0`.
