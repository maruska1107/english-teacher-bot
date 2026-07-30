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

This is the main card area. It has an internal switch:

```text
Учить
Список
```

### Mode: Учить

This mode shows the flip-card learning flow:

1. English word/phrase first.
2. Tap card to reveal Russian translation.
3. After reveal, show buttons:
   - `Не знаю`
   - `Ещё учу`
   - `Знаю`

The study mode must not show progress summary blocks. It may show only the card position, for example `Карточка 1 из 12`.

If there are cards with status `new`, the card position line shows a compact badge:

```text
Новых слов: +N
```

Study cards include every card whose student progress status is not `known`:

- `new`
- `learning`

### Mode: Список

This mode shows all published cards. Under the internal `Учить / Список` buttons it shows a bold line with the same style and placement as the study position line:

```text
Слов: N
```

Each card shows:

- English word/phrase;
- Russian translation;
- optional example;
- status label in Russian: `Новое`, `Учу`, or `Знаю`.

Actions:

- if the card status is `known`, show `Повторять`; clicking it returns the card to `learning`;
- otherwise show `Знаю`; clicking it marks the card as `known`.

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
- `Учить`
- `Список`
- `Новых слов: +N`
- `Новое`
- `Учу`
- `Знаю`
- `Повторять`
- `Мой прогресс`

Do not use technical wording like `progress`, `status`, or `dataset` in visible UI.

## Testing Plan

Page-level tests should verify that `/student/cards` contains:

- `Карточки`
- `Статистика`
- `data-card-mode="study"`
- `data-card-mode="list"`
- `Учить`
- `Список`
- `Новых слов: +${newCount}`
- `statusLabel`
- `Повторять`
- `renderCardList`
- `Слов: ${allCards.length}` inside `.study-progress`
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
