# Student Card Sections Design

Date: 2026-07-29

## Goal

Make the student card WebApp cleaner by separating study, unlearned cards, statistics, and the full card list into distinct sections.

## User-facing Sections

The student WebApp `/student/cards` has four top-level buttons:

```text
Учить
Неизученное
Статистика
Все карточки
```

## Section: Учить

This is the main study mode.

It must show only the flip-card learning flow:

1. English word/phrase first.
2. Tap card to reveal Russian translation.
3. After reveal, show buttons:
   - `Не знаю`
   - `Ещё учу`
   - `Знаю`

The study section must not show progress summary blocks or new-card summary blocks above the card. It may show only the card position, for example `Карточка 1 из 12`.

Study cards include every card whose student progress status is not `known`:

- `new`
- `learning`

## Section: Неизученное

This section explains what remains to learn.

It shows two groups:

```text
Новые от преподавателя
```

Cards with status `new`.

```text
Уже в изучении
```

Cards with status `learning`.

The section has a button:

```text
Учить эти слова
```

This button does not create a separate set and does not change card status by itself. It switches the WebApp back to the `Учить` section, where all unlearned cards are already included.

## Section: Статистика

This section contains the existing progress summary previously shown at the top of the WebApp:

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

## Section: Все карточки

This section keeps the full list of published cards.

For each card, show:

- English word/phrase;
- Russian translation;
- optional example;
- current status.

Actions:

- If status is `known`, show `Учить` to return it to `learning`.
- Otherwise show `Знаю` to mark it known.

## Data Model

No database migration is required.

The existing `/api/student/cards` endpoint already returns published cards and student progress statuses:

- `new`
- `learning`
- `known`

## Wording

Use simple Russian:

- `Учить`
- `Неизученное`
- `Статистика`
- `Все карточки`
- `Новые от преподавателя`
- `Уже в изучении`
- `Учить эти слова`
- `Мой прогресс`

Do not use technical wording like `progress`, `status`, or `dataset` in visible UI.

## Testing Plan

Page-level tests should verify that `/student/cards` contains:

- `Учить`
- `Неизученное`
- `Статистика`
- `Все карточки`
- `Новые от преподавателя`
- `Уже в изучении`
- `Учить эти слова`
- `renderStats`
- `renderUnlearned`
- no top-level `summary-grid` block before the study section

Existing student API tests remain unchanged.

## Out of Scope

- Separate custom study sets.
- Student opt-in before a teacher-published card enters study mode.
- Daily/weekly streak statistics.
- Spaced repetition scheduling.
