# Simplified Card UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Скрыть три перегружающих teacher-поля и две student-подсказки без изменения данных/API.

**Architecture:** Меняется только inline JavaScript разметка. Скрытые teacher-значения берутся из объекта карточки при формировании update payload, поэтому не очищаются.

**Tech Stack:** Python/FastAPI inline HTML/JavaScript, Node test runner, pytest, Ruff.

## Global Constraints

- Не менять БД, схемы API и анализ уроков.
- Сохранять существующие значения `definition_en`, `source_phrase`, `level` при редактировании видимых полей.

---

### Task 1: Упростить teacher и student карточки

**Files:**
- Modify: `app/api/teacher_webapp.py`
- Modify: `app/api/student_webapp.py`
- Modify: `tests/js/teacher_images.test.js`
- Modify: `tests/js/student_card_ui.test.js`

**Interfaces:**
- Consumes: объекты карточек API с прежними полями.
- Produces: update payload с сохранёнными скрытыми значениями.

- [ ] Добавить Node assertions: teacher HTML не содержит трёх labels/controls и published definition; payload сохраняет три значения из card state; student HTML не содержит двух подсказок.
- [ ] Запустить Node tests и подтвердить ожидаемый FAIL.
- [ ] Удалить teacher markup, брать скрытые значения из объекта карточки в payload, убрать published definition; удалить student `revealHint` и его вывод.
- [ ] Запустить Node tests и подтвердить PASS.
- [ ] Запустить `./scripts/test_all.sh`, `git diff --check`, commit и production deployment.
