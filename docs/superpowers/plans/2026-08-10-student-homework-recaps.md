# Student Homework and Lesson Recaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP learner-facing “Домашка” interface with current and previous lesson recap/homework snapshots.

**Architecture:** Add a small `StudentHomework` persistence model with two slots (`current`, `previous`) per student/profile. Expose it through the existing student WebApp auth path and render it inside `student_webapp.py` next to cards. Seed/dev and later teacher-confirmation flows will call the repository to publish a confirmed recap; this first implementation includes the storage/API/UI and a dev-seed path for review.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, Telegram WebApp auth, vanilla HTML/CSS/JS, pytest, Node TAP tests, Ruff.

## Global Constraints

- Store only current and previous homework/recap snapshots; older snapshots are overwritten.
- Student-facing content is visible only after confirmation/publication.
- Student API must use existing Telegram WebApp auth and linked-student lookup.
- Teacher/data ownership checks must remain intact.
- No long-term homework history, completion tracking, uploads, due dates, or reminders in this slice.
- Keep Russian UX copy simple and non-technical.
- Run `./scripts/test_all.sh` and `git diff --check` before deployment.

---

### Task 1: Persistence model and repository

**Files:**
- Create: `app/models/student_homework.py`
- Modify: `app/models/__init__.py`
- Create: `app/repositories/student_homework.py`
- Create: `alembic/versions/0007_student_homework.py`
- Test: `tests/test_student_homework.py`

**Interfaces:**
- Produces: `StudentHomeworkRepository.publish_current(...) -> StudentHomework`
- Produces: `StudentHomeworkRepository.current_and_previous(student_id: int) -> list[StudentHomework]`

- [ ] Write failing repository tests for publishing first homework and shifting current to previous.
- [ ] Add SQLAlchemy model with `slot` limited by application logic to `current|previous`.
- [ ] Add Alembic migration.
- [ ] Implement repository shift/delete behavior.
- [ ] Run `./scripts/test_all.sh` and commit.

### Task 2: Student homework API

**Files:**
- Modify: `app/schemas/student_cards.py`
- Modify: `app/api/student_cards.py`
- Test: `tests/test_student_cards_api.py` or existing student card API tests

**Interfaces:**
- Produces: `GET /api/student/homework` returning `{items: [...]}` with current/previous snapshots.

- [ ] Write failing API tests for linked student getting homework and unlinked/auth failures staying protected.
- [ ] Add Pydantic response schemas.
- [ ] Add `/api/student/homework` route using `get_current_student`.
- [ ] Run `./scripts/test_all.sh` and commit.

### Task 3: Student WebApp Homework tab

**Files:**
- Modify: `app/api/student_webapp.py`
- Modify: `tests/js/student_card_ui.test.js` or add static HTML source test

**Interfaces:**
- Consumes: `GET /api/student/homework`.

- [ ] Write failing JS/static tests that the WebApp exposes “Карточки” and “Домашка” views and empty homework copy.
- [ ] Add tab/chip navigation in the existing lilac style.
- [ ] Render current homework with summary/focus/homework checklist and previous homework collapsed/secondary.
- [ ] Keep existing cards behavior unchanged.
- [ ] Run `./scripts/test_all.sh` and commit.

### Task 4: Dev seed publishes reviewable homework

**Files:**
- Modify: `app/telegram/commands.py`
- Test: `tests/test_telegram_commands.py`

**Interfaces:**
- Consumes: `StudentHomeworkRepository.publish_current(...)`.

- [ ] Write failing test that `/dev_seed_data` creates current homework for the seeded student.
- [ ] Implement dev seed learner recap/homework publication.
- [ ] Run `./scripts/test_all.sh` and commit.

### Task 5: Deployment and production verification

**Files:**
- No code files unless verification finds issues.

- [ ] Run final `./scripts/test_all.sh && git diff --check`.
- [ ] Create DB backup before Alembic migration.
- [ ] Deploy backend with `docker compose up -d --build backend`.
- [ ] Verify `/health`, `/ready`, Alembic current revision `0007_student_homework`, backend logs.
- [ ] Verify production HTML contains “Домашка” and `/dev_seed_data` creates a current homework snapshot in a temporary reviewer/test account, then clean up.
- [ ] Push `feat/mvp-foundation` to GitHub.

## Self-review

- Spec coverage: persistence, API, student UI, dev seed, tests, deployment are covered.
- Placeholder scan: no TBD/TODO placeholders.
- Type consistency: repository names and route names are defined before use.
