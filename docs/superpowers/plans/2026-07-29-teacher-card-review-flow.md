# Teacher Card Review Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the teacher's flat card list with a profile-first review flow where new cards are checked, edited/deleted, and batch-published per student/group.

**Architecture:** Extend the existing monolith without migrations. Add focused teacher-card schemas and repository methods, expose new FastAPI endpoints under the existing teacher WebApp auth, then rewrite `/teacher/cards` HTML/JS to use a profile list and selected-profile review screen.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, PostgreSQL/SQLite tests, Telegram WebApp `initData`, Docker Compose, ruff, pytest.

## Global Constraints

- Production project path is `/opt/english-teacher-bot`.
- Branch is `feat/mvp-foundation`.
- Use existing tables only: `learning_profiles`, `vocabulary_cards`, `learning_profile_members`; no migration for this iteration.
- Teacher WebApp APIs must continue requiring verified `x-telegram-init-data`.
- UI wording must use simple Russian: `Новые карточки`, `Опубликованные`, `Удалить`, `Опубликовать все карточки`, `+ Добавить слово`.
- Do not show `draft`, `published`, or `archive` wording/actions in the teacher WebApp UI.
- Delete unwanted cards permanently; do not add archive UI.
- Manual cards are created as internal `draft` and shown as `Новые карточки`.
- Keep Docker image tag explicit: `english-teacher-bot-backend:0.1.0`.
- Do not expose secrets, tokens, passwords, or connection strings.

---

## File Structure

- Modify `app/schemas/cards.py`: add profile summary, manual card create, and batch publish request/response schemas.
- Modify `app/repositories/learning_profiles.py`: add profile-count listing for teacher cards.
- Modify `app/repositories/vocabulary_cards.py`: add manual draft creation, permanent delete, and batch publish for a profile.
- Modify `app/api/teacher_cards.py`: add endpoints `GET /api/teacher/card-profiles`, `POST /api/teacher/cards`, `DELETE /api/teacher/cards/{card_id}`, `POST /api/teacher/cards/publish-batch`.
- Modify `app/api/teacher_webapp.py`: replace flat draft-card UI with profile-first UI and no archive action.
- Modify `tests/test_teacher_cards_api.py`: cover new backend behaviors.
- Modify `tests/test_foundation.py`: cover new teacher WebApp strings/API markers and absence of archive UI.

---

### Task 1: Add backend schemas and repository support

**Files:**
- Modify: `app/schemas/cards.py`
- Modify: `app/repositories/learning_profiles.py`
- Modify: `app/repositories/vocabulary_cards.py`
- Test: `tests/test_teacher_cards_api.py`

**Interfaces:**
- Consumes existing models: `LearningProfile`, `VocabularyCard`, `User`.
- Produces schemas:
  - `TeacherCardProfileRead(id: int, name: str, profile_type: str, new_card_count: int, published_card_count: int)`
  - `TeacherCardProfileListResponse(profiles: list[TeacherCardProfileRead])`
  - `VocabularyCardCreate(learning_profile_id: int, term: str, translation_ru: str, definition_en: str | None, example_sentence: str | None, source_phrase: str | None, level: str | None)`
  - `BatchPublishCardsRequest(learning_profile_id: int)`
  - `BatchPublishCardsResponse(published_count: int)`
- Produces repository methods:
  - `LearningProfileRepository.list_with_card_counts(teacher_user_id: int) -> list[tuple[LearningProfile, int, int]]`
  - `VocabularyCardRepository.create_manual_draft_card(teacher_user_id: int, payload: VocabularyCardCreate) -> VocabularyCard`
  - `VocabularyCardRepository.delete_card(card: VocabularyCard) -> None`
  - `VocabularyCardRepository.publish_draft_cards_for_profile(teacher_user_id: int, learning_profile_id: int) -> int`

- [ ] **Step 1: Write failing tests for profile counts and repository behavior**

Append these tests to `tests/test_teacher_cards_api.py`:

```python
def test_teacher_profile_repository_counts_new_and_published_cards():
    session = make_session()
    teacher, profile, _, _ = seed_teacher_profile_and_cards(session)
    other_profile = LearningProfile(
        teacher_user_id=teacher.id,
        name="Анна",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    session.add(other_profile)
    session.flush()
    session.add(
        VocabularyCard(
            teacher_user_id=teacher.id,
            learning_profile_id=other_profile.id,
            term="apple",
            translation_ru="яблоко",
            status="draft",
        )
    )
    session.commit()

    from app.repositories.learning_profiles import LearningProfileRepository

    rows = LearningProfileRepository(session).list_with_card_counts(teacher.id)

    assert [(row[0].name, row[1], row[2]) for row in rows] == [
        ("Speaking B1", 1, 1),
        ("Анна", 1, 0),
    ]


def test_vocabulary_repository_can_create_delete_and_batch_publish_cards():
    session = make_session()
    teacher, profile, draft_card, published_card = seed_teacher_profile_and_cards(session)

    from app.repositories.vocabulary_cards import VocabularyCardRepository
    from app.schemas.cards import VocabularyCardCreate

    repository = VocabularyCardRepository(session)
    manual_card = repository.create_manual_draft_card(
        teacher_user_id=teacher.id,
        payload=VocabularyCardCreate(
            learning_profile_id=profile.id,
            term="fluency",
            translation_ru="беглость речи",
            definition_en="speaking smoothly",
            example_sentence="Her fluency improved.",
            source_phrase=None,
            level="B1",
        ),
    )
    session.commit()

    assert manual_card.status == "draft"
    assert manual_card.learning_profile_id == profile.id

    repository.delete_card(published_card)
    published_count = repository.publish_draft_cards_for_profile(teacher.id, profile.id)
    session.commit()

    assert published_count == 2
    assert session.get(VocabularyCard, published_card.id) is None
    assert session.get(VocabularyCard, draft_card.id).status == "published"
    assert session.get(VocabularyCard, manual_card.id).status == "published"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /opt/english-teacher-bot
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_teacher_cards_api.py::test_teacher_profile_repository_counts_new_and_published_cards tests/test_teacher_cards_api.py::test_vocabulary_repository_can_create_delete_and_batch_publish_cards -q'
```

Expected: FAIL because `list_with_card_counts`, `VocabularyCardCreate`, and repository methods do not exist.

- [ ] **Step 3: Add schemas**

Append to `app/schemas/cards.py`:

```python
class TeacherCardProfileRead(BaseModel):
    id: int
    name: str
    profile_type: str
    new_card_count: int
    published_card_count: int


class TeacherCardProfileListResponse(BaseModel):
    profiles: list[TeacherCardProfileRead]


class VocabularyCardCreate(BaseModel):
    learning_profile_id: int
    term: str = Field(min_length=1)
    translation_ru: str = Field(min_length=1)
    definition_en: str | None = None
    example_sentence: str | None = None
    source_phrase: str | None = None
    level: str | None = None


class BatchPublishCardsRequest(BaseModel):
    learning_profile_id: int


class BatchPublishCardsResponse(BaseModel):
    published_count: int
```

- [ ] **Step 4: Add `LearningProfileRepository.list_with_card_counts`**

Modify imports in `app/repositories/learning_profiles.py`:

```python
from sqlalchemy import func, select

from app.models import LearningProfile, LearningProfileMember, Student, VocabularyCard
```

Add method inside `LearningProfileRepository`:

```python
    def list_with_card_counts(self, teacher_user_id: int) -> list[tuple[LearningProfile, int, int]]:
        draft_count = func.count(VocabularyCard.id).filter(VocabularyCard.status == "draft")
        published_count = func.count(VocabularyCard.id).filter(VocabularyCard.status == "published")
        rows = self.session.execute(
            select(LearningProfile, draft_count, published_count)
            .outerjoin(VocabularyCard, VocabularyCard.learning_profile_id == LearningProfile.id)
            .where(LearningProfile.teacher_user_id == teacher_user_id)
            .group_by(LearningProfile.id)
            .order_by(LearningProfile.created_at, LearningProfile.id)
        ).all()
        return [(profile, int(new_count or 0), int(published or 0)) for profile, new_count, published in rows]
```

- [ ] **Step 5: Add vocabulary card repository methods**

Modify imports in `app/repositories/vocabulary_cards.py`:

```python
from app.schemas.cards import VocabularyCardCreate, VocabularyCardUpdate
```

Add methods inside `VocabularyCardRepository`:

```python
    def create_manual_draft_card(self, teacher_user_id: int, payload: VocabularyCardCreate) -> VocabularyCard:
        card = VocabularyCard(
            teacher_user_id=teacher_user_id,
            learning_profile_id=payload.learning_profile_id,
            lesson_id=None,
            term=payload.term.strip(),
            translation_ru=payload.translation_ru.strip(),
            definition_en=payload.definition_en.strip() if isinstance(payload.definition_en, str) else payload.definition_en,
            example_sentence=(
                payload.example_sentence.strip() if isinstance(payload.example_sentence, str) else payload.example_sentence
            ),
            source_phrase=payload.source_phrase.strip() if isinstance(payload.source_phrase, str) else payload.source_phrase,
            level=payload.level.strip() if isinstance(payload.level, str) else payload.level,
            status="draft",
        )
        self.session.add(card)
        self.session.flush()
        return card

    def delete_card(self, card: VocabularyCard) -> None:
        self.session.delete(card)
        self.session.flush()

    def publish_draft_cards_for_profile(self, teacher_user_id: int, learning_profile_id: int) -> int:
        cards = self.list_for_teacher(
            teacher_user_id=teacher_user_id,
            learning_profile_id=learning_profile_id,
            status="draft",
        )
        for card in cards:
            self.set_status(card, "published")
        self.session.flush()
        return len(cards)
```

- [ ] **Step 6: Run task tests and full tests**

Run targeted test command from Step 2. Expected: PASS.

Then run:

```bash
cd /opt/english-teacher-bot
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests -q'
```

Expected: all tests pass.

- [ ] **Step 7: Run ruff**

Run:

```bash
cd /opt/english-teacher-bot
docker compose run --rm --user root --entrypoint sh \
  -v "$PWD/app:/app/app" \
  -v "$PWD/tests:/app/tests" \
  -v "$PWD/alembic:/app/alembic" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'ruff check app tests alembic --fix && ruff format app tests alembic'
```

Expected: `All checks passed!` and format output.

- [ ] **Step 8: Commit**

```bash
cd /opt/english-teacher-bot
git add app/schemas/cards.py app/repositories/learning_profiles.py app/repositories/vocabulary_cards.py tests/test_teacher_cards_api.py
git commit -m "feat: add teacher card review repositories"
```

---

### Task 2: Add teacher card review API endpoints

**Files:**
- Modify: `app/api/teacher_cards.py`
- Test: `tests/test_teacher_cards_api.py`

**Interfaces:**
- Consumes Task 1 schemas and repository methods.
- Produces endpoints:
  - `GET /api/teacher/card-profiles -> TeacherCardProfileListResponse`
  - `POST /api/teacher/cards -> VocabularyCardRead`
  - `DELETE /api/teacher/cards/{card_id} -> 204 No Content`
  - `POST /api/teacher/cards/publish-batch -> BatchPublishCardsResponse`

- [ ] **Step 1: Write failing API tests**

Append to `tests/test_teacher_cards_api.py`:

```python
def test_teacher_can_list_card_profiles_with_counts():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    client = make_client(session)

    response = client.get(
        "/api/teacher/card-profiles",
        headers={"x-telegram-init-data": signed_init_data(1001)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "profiles": [
            {
                "id": profile.id,
                "name": "Speaking B1",
                "profile_type": "group",
                "new_card_count": 1,
                "published_card_count": 1,
            }
        ]
    }


def test_teacher_can_create_delete_and_batch_publish_cards_via_api():
    session = make_session()
    _, profile, draft_card, published_card = seed_teacher_profile_and_cards(session)
    client = make_client(session)
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    create_response = client.post(
        "/api/teacher/cards",
        headers=headers,
        json={
            "learning_profile_id": profile.id,
            "term": "fluency",
            "translation_ru": "беглость речи",
            "definition_en": "speaking smoothly",
            "example_sentence": "Her fluency improved.",
            "source_phrase": None,
            "level": "B1",
        },
    )
    delete_response = client.delete(f"/api/teacher/cards/{published_card.id}", headers=headers)
    publish_response = client.post(
        "/api/teacher/cards/publish-batch",
        headers=headers,
        json={"learning_profile_id": profile.id},
    )

    assert create_response.status_code == 200
    assert create_response.json()["status"] == "draft"
    assert delete_response.status_code == 204
    assert session.get(VocabularyCard, published_card.id) is None
    assert publish_response.status_code == 200
    assert publish_response.json() == {"published_count": 2}
    assert session.get(VocabularyCard, draft_card.id).status == "published"
    assert session.get(VocabularyCard, create_response.json()["id"]).status == "published"


def test_teacher_cannot_create_card_for_other_teacher_profile_or_batch_publish_it():
    session = make_session()
    _, profile, _, _ = seed_teacher_profile_and_cards(session)
    other_teacher = User(telegram_user_id=2002, role="teacher", is_active=True)
    other_profile = LearningProfile(
        teacher_user_id=other_teacher.id,
        name="Other",
        profile_type="individual",
        card_publish_mode="manual_review",
    )
    session.add(other_teacher)
    session.flush()
    other_profile.teacher_user_id = other_teacher.id
    session.add(other_profile)
    session.commit()
    client = make_client(session)
    headers = {"x-telegram-init-data": signed_init_data(1001)}

    create_other = client.post(
        "/api/teacher/cards",
        headers=headers,
        json={
            "learning_profile_id": other_profile.id,
            "term": "bad",
            "translation_ru": "плохо",
        },
    )
    publish_other = client.post(
        "/api/teacher/cards/publish-batch",
        headers=headers,
        json={"learning_profile_id": other_profile.id},
    )
    publish_own = client.post(
        "/api/teacher/cards/publish-batch",
        headers=headers,
        json={"learning_profile_id": profile.id},
    )

    assert create_other.status_code == 404
    assert publish_other.status_code == 404
    assert publish_own.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd /opt/english-teacher-bot
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_teacher_cards_api.py::test_teacher_can_list_card_profiles_with_counts tests/test_teacher_cards_api.py::test_teacher_can_create_delete_and_batch_publish_cards_via_api tests/test_teacher_cards_api.py::test_teacher_cannot_create_card_for_other_teacher_profile_or_batch_publish_it -q'
```

Expected: FAIL because endpoints do not exist.

- [ ] **Step 3: Add imports in `app/api/teacher_cards.py`**

Update imports:

```python
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from app.models import LearningProfile, User, VocabularyCard
from app.repositories.learning_profiles import LearningProfileRepository
from app.schemas.cards import (
    BatchPublishCardsRequest,
    BatchPublishCardsResponse,
    TeacherCardProfileListResponse,
    TeacherCardProfileRead,
    VocabularyCardCreate,
    VocabularyCardListResponse,
    VocabularyCardRead,
    VocabularyCardUpdate,
)
```

- [ ] **Step 4: Add helper functions**

Add below `get_current_teacher`:

```python
def profile_to_response(profile: LearningProfile, new_count: int, published_count: int) -> TeacherCardProfileRead:
    return TeacherCardProfileRead(
        id=profile.id,
        name=profile.name,
        profile_type=profile.profile_type,
        new_card_count=new_count,
        published_card_count=published_count,
    )


def get_teacher_profile_or_404(session: Session, teacher: User, profile_id: int) -> LearningProfile:
    profile = session.get(LearningProfile, profile_id)
    if profile is None or profile.teacher_user_id != teacher.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile
```

- [ ] **Step 5: Add endpoints**

Create a second router because `teacher_cards.py` currently uses prefix `/api/teacher/cards`, while the desired profile endpoint is `/api/teacher/card-profiles`.

At module top after existing router:

```python
profiles_router = APIRouter(prefix="/api/teacher/card-profiles", tags=["teacher-card-profiles"])
```

Add endpoint on `profiles_router`:

```python
@profiles_router.get("", response_model=TeacherCardProfileListResponse)
def list_card_profiles(
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> TeacherCardProfileListResponse:
    rows = LearningProfileRepository(session).list_with_card_counts(teacher.id)
    return TeacherCardProfileListResponse(
        profiles=[profile_to_response(profile, new_count, published_count) for profile, new_count, published_count in rows]
    )
```

Add these endpoints on existing `router`:

```python
@router.post("", response_model=VocabularyCardRead)
def create_card(
    payload: VocabularyCardCreate,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> VocabularyCardRead:
    get_teacher_profile_or_404(session, teacher, payload.learning_profile_id)
    card = VocabularyCardRepository(session).create_manual_draft_card(teacher.id, payload)
    session.commit()
    return card_to_response(card)


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: int,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> Response:
    repository = VocabularyCardRepository(session)
    card = repository.get_for_teacher(teacher.id, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    repository.delete_card(card)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/publish-batch", response_model=BatchPublishCardsResponse)
def publish_batch(
    payload: BatchPublishCardsRequest,
    session: Annotated[Session, Depends(get_db_session)],
    teacher: Annotated[User, Depends(get_current_teacher)],
) -> BatchPublishCardsResponse:
    get_teacher_profile_or_404(session, teacher, payload.learning_profile_id)
    published_count = VocabularyCardRepository(session).publish_draft_cards_for_profile(
        teacher_user_id=teacher.id,
        learning_profile_id=payload.learning_profile_id,
    )
    session.commit()
    return BatchPublishCardsResponse(published_count=published_count)
```

- [ ] **Step 6: Include `profiles_router` in `app/api/router.py`**

Modify `app/api/router.py` import for teacher cards to import both routers, then include both:

```python
from app.api.teacher_cards import profiles_router as teacher_card_profiles_router
from app.api.teacher_cards import router as teacher_cards_router

api_router.include_router(teacher_card_profiles_router)
api_router.include_router(teacher_cards_router)
```

- [ ] **Step 7: Run targeted and full tests**

Run targeted command from Step 2. Expected: PASS.

Then run full suite:

```bash
cd /opt/english-teacher-bot
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests -q'
```

Expected: all tests pass.

- [ ] **Step 8: Run ruff and commit**

Run ruff command from Task 1 Step 7. Expected: pass.

Commit:

```bash
cd /opt/english-teacher-bot
git add app/api/teacher_cards.py app/api/router.py tests/test_teacher_cards_api.py
git commit -m "feat: add teacher card review API"
```

---

### Task 3: Replace teacher WebApp with profile-first UI

**Files:**
- Modify: `app/api/teacher_webapp.py`
- Modify: `tests/test_foundation.py`

**Interfaces:**
- Consumes Task 2 endpoints:
  - `GET /api/teacher/card-profiles`
  - `GET /api/teacher/cards?profile_id=<id>&status=draft`
  - `GET /api/teacher/cards?profile_id=<id>&status=published`
  - `POST /api/teacher/cards`
  - `PATCH /api/teacher/cards/{card_id}`
  - `DELETE /api/teacher/cards/{card_id}`
  - `POST /api/teacher/cards/publish-batch`
- Produces `/teacher/cards` UI with profile list, selected profile, new/published sections, manual add, delete, and batch publish.

- [ ] **Step 1: Write failing page test**

Modify `test_teacher_cards_webapp_page_is_available` in `tests/test_foundation.py` to assert:

```python
    assert "/api/teacher/card-profiles" in response.text
    assert "Новые карточки" in response.text
    assert "Опубликованные" in response.text
    assert "+ Добавить слово" in response.text
    assert "Опубликовать все карточки" in response.text
    assert "Удалить" in response.text
    assert "+N новых слов" in response.text
    assert "Профилей пока нет" in response.text
    assert "archive" not in response.text
```

Keep existing assertions for `Telegram.WebApp`, `x-telegram-init-data`, and `/api/teacher/cards`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /opt/english-teacher-bot
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests/test_foundation.py::test_teacher_cards_webapp_page_is_available -q'
```

Expected: FAIL because current page is flat draft list and contains archive action.

- [ ] **Step 3: Replace `app/api/teacher_webapp.py` style and script**

Rewrite `app/api/teacher_webapp.py` as one HTML page that keeps existing route functions and defines:

```javascript
let profiles = [];
let selectedProfile = null;
let currentTab = "draft";
let draftCards = [];
let publishedCards = [];
```

Implement JS functions with these exact responsibilities:

```javascript
async function loadProfiles() {
  // GET /api/teacher/card-profiles, store response.profiles in profiles, render profile list.
}

function profileTemplate(profile) {
  // Return one clickable profile card containing profile.name, Russian profile type, +N новых слов, and N опубликовано.
}

async function openProfile(profileId) {
  // Find profile in profiles, set selectedProfile, reset currentTab to "draft", then call loadProfileCards().
}

async function loadProfileCards() {
  // GET draft and published cards for selectedProfile.id, store in draftCards/publishedCards, then render detail screen.
}

function renderSelectedProfile() {
  // Render back button, profile name, tabs, add-word form button, draft or published list, and batch publish button.
}

function editableCardTemplate(card) {
  // Return editable inputs for term, translation_ru, definition_en, example_sentence, source_phrase, level, plus Удалить.
}

function publishedCardTemplate(card) {
  // Return a compact read-only card display with term, translation_ru, optional example, and label Опубликовано.
}

function payloadFromCard(cardEl) {
  // Read term, translation_ru, definition_en, example_sentence, source_phrase, and level from the editable card element.
}

async function saveAllDraftCardEdits() {
  // PATCH every card currently in draftCards using payloadFromCard before batch publish.
}

async function publishAllDraftCards() {
  // Disable the batch button, call saveAllDraftCardEdits(), POST /api/teacher/cards/publish-batch, reload profiles/cards.
}

async function deleteCard(cardId) {
  // confirm('Удалить эту карточку?'), DELETE /api/teacher/cards/{cardId}, then reload profile cards and counts.
}

async function createManualCard() {
  // POST /api/teacher/cards with selectedProfile.id and form values, then clear form and reload profile cards/counts.
}
```

The page must not contain string `archive`.

- [ ] **Step 4: Required UI markup**

The HTML returned by `_page()` must include these static strings so tests and users see the intended flow:

```html
<h1>Карточки</h1>
<p class="lead">Сначала выберите ученика или группу, затем проверьте новые карточки.</p>
<section id="profiles"></section>
<section id="profile-detail" class="hidden"></section>
```

Include text in templates:

```text
+N новых слов
Новые карточки
Опубликованные
+ Добавить слово
Опубликовать все карточки
Удалить
Профилей пока нет. Добавьте ученика или группу в Telegram.
Новых карточек пока нет.
Опубликованных карточек пока нет.
```

- [ ] **Step 5: Run targeted and full tests**

Run targeted command from Step 2. Expected: PASS.

Then run:

```bash
cd /opt/english-teacher-bot
chmod -R a+rX tests app alembic pyproject.toml
docker compose run --rm --entrypoint sh \
  -v "$PWD/tests:/app/tests:ro" \
  -v "$PWD/app:/app/app:ro" \
  -v "$PWD/alembic:/app/alembic:ro" \
  -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" \
  backend -c 'pytest tests -q'
```

Expected: all tests pass.

- [ ] **Step 6: Run ruff and commit**

Run ruff command from Task 1 Step 7. Expected: pass.

Commit:

```bash
cd /opt/english-teacher-bot
git add app/api/teacher_webapp.py tests/test_foundation.py
git commit -m "feat: add profile-first teacher cards webapp"
```

---

### Task 4: Deploy and verify production

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes all prior tasks.
- Produces deployed live teacher card review flow.

- [ ] **Step 1: Confirm clean state and recent commits**

Run:

```bash
cd /opt/english-teacher-bot
git status --short
git log --oneline -5
```

Expected: clean or only intentional changes already committed.

- [ ] **Step 2: Build and deploy backend/nginx**

Run:

```bash
cd /opt/english-teacher-bot
docker compose build backend
docker compose up -d backend nginx
```

Expected: backend image `english-teacher-bot-backend:0.1.0` built and backend container recreated.

- [ ] **Step 3: Verify health**

Run:

```bash
curl -fsS https://englishtutorai.ru/health && printf '\n'
curl -fsS https://englishtutorai.ru/ready && printf '\n'
```

Expected:

```json
{"status":"ok","service":"english-teacher-bot"}
{"status":"ready","database":"ok"}
```

- [ ] **Step 4: Verify live teacher WebApp HTML**

Run:

```bash
python3 - <<'PY'
import urllib.request
html = urllib.request.urlopen('https://englishtutorai.ru/teacher/cards', timeout=20).read().decode()
checks = [
    '/api/teacher/card-profiles',
    'Новые карточки',
    'Опубликованные',
    '+ Добавить слово',
    'Опубликовать все карточки',
    'Удалить',
    '+N новых слов',
]
print({item: item in html for item in checks})
print({'contains_archive': 'archive' in html})
PY
```

Expected every check is `True` and `contains_archive` is `False`.

- [ ] **Step 5: Verify API auth boundaries live without secrets**

Run:

```bash
curl -s -o /tmp/card-profiles-response.txt -w '%{http_code}\n' https://englishtutorai.ru/api/teacher/card-profiles
cat /tmp/card-profiles-response.txt
```

Expected HTTP `401` and message that Telegram WebApp `initData` is required.

- [ ] **Step 6: Push commits**

Run:

```bash
cd /opt/english-teacher-bot
git push
git status --short
```

Expected: push succeeds and status is clean.
