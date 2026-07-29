# Teacher Card Review Flow Design

Date: 2026-07-29

## Goal

Make the teacher WebApp useful when cards accumulate across lessons, students, and groups. The teacher should not see one flat list of all cards. Instead, the teacher first chooses a learning profile, sees how many new words need review, then reviews that profile's cards in context.

## Terms

- **Learning profile**: an individual student or group. This remains the main context for cards.
- **New cards**: teacher-facing label for cards with backend status `draft`. The UI must not show the word `draft`.
- **Published cards**: cards visible to students.
- **Delete**: permanently remove an unwanted card. There is no archive UI for this flow.

## User Flow

### Entry

The teacher sends `/cards` in Telegram and opens the Teacher WebApp.

### Screen 1: Profiles

The first screen lists learning profiles owned by the teacher.

Each profile card shows:

- profile name;
- profile type: individual or group, shown in simple Russian;
- green badge `+N новых слов` for new cards waiting for review;
- published count, for example `12 опубликовано`.

The teacher taps a profile to open its card review screen.

### Screen 2: Selected Profile Cards

The selected profile screen shows:

- profile name;
- back button to the profile list;
- two sections/tabs:
  - `Новые карточки`;
  - `Опубликованные`.

The primary work area is `Новые карточки`.

For each new card, the teacher can edit:

- English word/phrase;
- Russian translation;
- English definition;
- example;
- source phrase;
- level.

Each new card has a `Удалить` action. Delete removes the card from the database. The UI does not offer archive.

At the bottom of the new-card section there is one batch action:

```text
Опубликовать все карточки
```

This publishes all remaining new cards for the selected profile after the teacher has edited/deleted what they want.

### Manual Add

Inside a selected profile, the teacher can click:

```text
+ Добавить слово
```

The teacher enters the same fields as above. The manually added card is created as a **new card** first, not immediately shown to students. It appears in `Новые карточки` and will be published by the same batch button.

This keeps one consistent review path:

```text
add/check/edit/delete -> publish all
```

## Backend/API Design

Keep the existing verified Telegram WebApp auth via `x-telegram-init-data`.

### List profiles with card counts

```http
GET /api/teacher/card-profiles
```

Response shape:

```json
{
  "profiles": [
    {
      "id": 1,
      "name": "Тест Мария",
      "profile_type": "individual",
      "new_card_count": 4,
      "published_card_count": 2
    }
  ]
}
```

Counts:

- `new_card_count`: cards with status `draft` for the profile;
- `published_card_count`: cards with status `published` for the profile.

### List cards for selected profile

Reuse existing endpoint:

```http
GET /api/teacher/cards?profile_id=<id>&status=draft
GET /api/teacher/cards?profile_id=<id>&status=published
```

The UI labels `draft` cards as `Новые карточки`.

### Update card

Reuse existing endpoint:

```http
PATCH /api/teacher/cards/{card_id}
```

### Create manual card

Add:

```http
POST /api/teacher/cards
```

Payload:

```json
{
  "learning_profile_id": 1,
  "term": "journey",
  "translation_ru": "путешествие",
  "definition_en": "a trip from one place to another",
  "example_sentence": "The journey was long.",
  "source_phrase": null,
  "level": "A2"
}
```

Created card status: `draft`.

### Delete card

Add:

```http
DELETE /api/teacher/cards/{card_id}
```

Deletes the card permanently if it belongs to the current teacher.

### Batch publish new cards for profile

Add:

```http
POST /api/teacher/cards/publish-batch
```

Payload:

```json
{
  "learning_profile_id": 1
}
```

Behavior:

- publish all `draft` cards for that teacher and profile;
- return the number published.

Response:

```json
{
  "published_count": 4
}
```

## UI Details

### Wording

Use simple Russian:

- `Новые карточки`, not `draft`;
- `Опубликованные`, not `published`;
- `Удалить`, not `архивировать`;
- `Опубликовать все карточки` for batch action;
- `+ Добавить слово` for manual add.

### Deletion UX

Deletion should require a small confirmation in the browser, for example:

```text
Удалить эту карточку?
```

No archive is shown. Deleted cards are gone from the teacher and student flows.

### Batch Publish UX

The batch button should be disabled while publishing. After success:

- new-card list reloads;
- profile counts update;
- published section updates;
- status message shows `Опубликовано: N`.

### Empty States

Profiles screen:

```text
Профилей пока нет. Добавьте ученика или группу в Telegram.
```

Selected profile, no new cards:

```text
Новых карточек пока нет.
```

Selected profile, no published cards:

```text
Опубликованных карточек пока нет.
```

## Data Model

No database migration is required for this iteration.

Use existing tables:

- `learning_profiles`;
- `vocabulary_cards`;
- `learning_profile_members`.

Use existing card statuses:

- `draft` internally = `Новые карточки` in UI;
- `published` internally = `Опубликованные` in UI.

Archive remains possible as an internal old status from prior code, but the new UI does not expose it. New unwanted cards are deleted instead.

## Testing Plan

Backend tests:

- teacher can list profiles with new/published card counts;
- unauthorized profile list returns 401/403 as current teacher APIs do;
- teacher can create a manual card as `draft` for their own profile;
- teacher cannot create a card for another teacher's profile;
- teacher can delete own card;
- teacher cannot delete another teacher's card;
- batch publish publishes only current teacher's `draft` cards for the selected profile;
- batch publish does not publish another profile's cards.

Frontend/page tests:

- `/teacher/cards` contains profile-list UI strings;
- page contains `/api/teacher/card-profiles`;
- page contains `Новые карточки`, `Опубликованные`, `+ Добавить слово`, `Опубликовать все карточки`, `Удалить`;
- page no longer exposes `archive` action in teacher UI.

Manual live verification:

- `/health` and `/ready` OK;
- `/teacher/cards` live HTML contains the new profile/card-review markers;
- `/cards` still opens the Telegram WebApp button.

## Out of Scope for This Iteration

- lesson-by-lesson grouping inside a profile;
- teacher analytics by student/group;
- archive screen;
- bulk select/unselect checkboxes;
- drag-and-drop ordering;
- separate profile management UI.

These can be added later after the core profile-first review flow is working.
