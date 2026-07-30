# Student Card Sections Design

Date: 2026-07-29

## Goal

Make the student card WebApp cleaner by reducing the top-level navigation to the two real student tasks: studying cards and checking progress.

## User-facing Sections

The student WebApp `/student/cards` has two top-level buttons:

```text
Карточки
Статистика
```

## Section: Карточки

This is the main study mode.

It shows only the flip-card learning flow:

1. English word/phrase first.
2. Tap card to reveal Russian translation.
3. After reveal, show buttons:
   - `Не знаю`
   - `Ещё учу`
   - `Знаю`

The study section must not show progress summary blocks or a separate full-list tab above the card. It may show only the card position, for example `Карточка 1 из 12`.

If there are cards with status `new`, the card position line shows a compact badge:

```text
+N новых слов
```

Study cards include every card whose student progress status is not `known`:

- `new`
- `learning`

There is no separate top-level `Новое`, `Неизученное`, `Обучение`, `Все`, or `Все карточки` section.

## Section: Статистика

This section contains the progress summary:

```text
Мой прогресс
Всего
Знаю
Учу
Новые
Осталось учить
Выучено %
```

No additional backend endpoint is needed. The frontend calculates these values from `/api/student/cards`.

## Data Model

No database migration is required.

The existing `/api/student/cards` endpoint already returns published cards and student progress statuses:

- `new`
- `learning`
- `known`

## Wording

Use simple Russian:

- `Карточки`
- `Статистика`
- `+N новых слов`
- `Мой прогресс`

Do not use technical wording like `progress`, `status`, or `dataset` in visible UI.

## Testing Plan

Page-level tests should verify that `/student/cards` contains:

- `Карточки`
- `Статистика`
- `+${newCount} новых слов`
- `renderStats`
- no top-level `summary-grid` block before the study section
- no `data-section="unlearned"`
- no `data-section="all"`
- no `Обучение`
- no `Новое`
- no `Все карточки`

Existing student API tests remain unchanged.

## Out of Scope

- Separate custom study sets.
- Student opt-in before a teacher-published card enters study mode.
- Daily/weekly streak statistics.
- Spaced repetition scheduling.
