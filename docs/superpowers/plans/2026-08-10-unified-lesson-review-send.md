# Unified Lesson Review Send Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make “На проверку” the single place where a teacher edits lesson cards and sends homework plus cards together.

**Architecture:** Extend the existing teacher lesson review API to include lesson draft cards and to update/delete draft cards by lesson-owned card ID. Change confirm to publish draft cards for the reviewed lesson before publishing StudentHomework. Reuse existing card image rendering and edit helpers in teacher WebApp; keep the full card image replacement flow in the existing student workspace for now, but allow text edit/delete directly in lesson review.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Telegram WebApp auth, existing VocabularyCardRepository/StudentHomeworkRepository, inline JS, Node TAP tests, pytest/Ruff.

## Global Constraints

- Students see lesson cards only after teacher clicks “Подтвердить и отправить всё”.
- Confirm publishes only draft cards for that lesson, not all draft cards for the profile.
- Teachers can edit/delete only their own draft cards from the review.
- Keep Russian copy simple and non-technical.
- Run `./scripts/test_all.sh && git diff --check`, deploy, verify production, and push.

---

### Task 1: API red/green

- [ ] Add failing tests: lesson review response contains card details; confirm publishes lesson draft cards; deleted card is not published; foreign teacher cannot edit/delete.
- [ ] Extend schemas with `cards` and `profile_id`.
- [ ] Add review card PATCH/DELETE endpoints scoped by teacher and draft status.
- [ ] Update confirm to publish draft cards for `lesson_id`.

### Task 2: WebApp red/green

- [ ] Add failing JS static tests for “Подтвердить и отправить всё”, inline review cards, save-before-confirm, delete review card, and no “Проверить карточки” detour.
- [ ] Render editable review cards inside “На проверку”.
- [ ] Save card edits before confirm; confirm sends the unified package.

### Task 3: Verification/deploy

- [ ] Run full gate.
- [ ] Deploy backend.
- [ ] Verify production HTML markers and functional API with temporary data.
- [ ] Push branch.
