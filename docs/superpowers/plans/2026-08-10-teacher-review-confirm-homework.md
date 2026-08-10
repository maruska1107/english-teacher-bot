# Teacher Review and Confirm Homework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let teachers review processed lesson results and confirm sending learner-facing recap/homework into the student “Домашка” section.

**Architecture:** Do not add another DB table for review state in this MVP. A lesson is “На проверку” when it has `LessonAnalysis`, belongs to the teacher, has a learning profile with linked student(s), and no `StudentHomework` exists for that lesson. Confirmation creates `StudentHomework` snapshots through the existing repository; this removes the lesson from pending review. Telegram student notifications can be added as a thin async step after the DB publish, but the durable source of truth is the WebApp homework snapshot.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Telegram WebApp auth, existing `StudentHomeworkRepository`, pytest, Node TAP tests, Ruff.

## Global Constraints

- Student sees a new recap/homework only after teacher confirmation.
- Keep only current and previous student homework snapshots.
- Preserve existing teacher ownership checks and Zoom review-mode behavior.
- Do not expose another teacher’s lesson analysis.
- Keep Russian teacher/student copy simple and non-technical.
- Run `./scripts/test_all.sh` and `git diff --check` before deployment.

---

### Task 1: Teacher review API

**Files:**
- Create: `app/api/teacher_lesson_reviews.py`
- Modify: `app/api/router.py`
- Modify: `app/schemas/student_cards.py` or create `app/schemas/teacher_lesson_reviews.py`
- Test: `tests/test_teacher_lesson_reviews_api.py`

**Interfaces:**
- `GET /api/teacher/lesson-reviews` returns pending processed lessons.
- `POST /api/teacher/lesson-reviews/{lesson_id}/confirm` publishes student homework and returns the created snapshot.

- [ ] Write failing API tests for pending list, confirm publish, cross-teacher protection, and repeated confirm conflict.
- [ ] Implement repository/query helpers inline or in a focused repository.
- [ ] Implement confirm by extracting summary, strengths, mistakes/focus, homework, and card count from `LessonAnalysis.analysis_json` and draft cards.
- [ ] Run full gate and commit.

### Task 2: Teacher WebApp “На проверку” UI

**Files:**
- Modify: `app/api/teacher_webapp.py`
- Test: `tests/js/teacher_images.test.js` or new static Node test

**Interfaces:**
- Consumes `/api/teacher/lesson-reviews` and `/confirm`.

- [ ] Write failing static JS test for “✨ На проверку”, “Подтвердить и отправить”, API paths.
- [ ] Add top-level teacher tabs: `👥 Ученики`, `✨ На проверку`, `📚 Уроки`, `⚙️ Настройки` as UI shell.
- [ ] Implement “На проверку” list with lesson summary/homework/cards count.
- [ ] Implement confirm button reloads pending list and updates status.
- [ ] Run full gate and commit.

### Task 3: Deployment verification

- [ ] Run `./scripts/test_all.sh && git diff --check`.
- [ ] Deploy backend.
- [ ] Verify `/health`, `/ready`, Alembic current unchanged at `0007_student_homework` unless a migration is added.
- [ ] Verify production `/teacher/cards` contains “На проверку” and confirm API is protected.
- [ ] Push `feat/mvp-foundation` to GitHub.
