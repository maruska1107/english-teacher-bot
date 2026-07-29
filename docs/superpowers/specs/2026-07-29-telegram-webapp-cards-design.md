# Telegram WebApp Cards & Learning Profiles Design

Date: 2026-07-29
Status: Draft for user review

## Goal

Extend the English Tutor AI bot from “Zoom lesson report sender” into a fuller learning workflow:

1. Tutors create individual students and groups.
2. Zoom meetings are linked to a learning profile, not only to a tutor.
3. Lesson analysis produces vocabulary cards.
4. Cards are stored inside our app instead of Quizlet.
5. Students open a Telegram WebApp to study published cards.
6. Group lessons produce group-level reports and group-level cards, while each student keeps their own study progress.

This design intentionally avoids Quizlet as a core dependency. Quizlet export can be added later, but the source of truth for cards and progress should be our own database.

## Product vocabulary

### Teacher

A Telegram user allowed to use the tutor/admin side of the bot. This maps to the existing `users` table with role `teacher`.

### Student

A real learner. A student can have a Telegram account linked through an invite link, but this is optional at creation time.

Examples:

- `Анна`
- `Мария`
- `Катя`

### Learning profile

The main unit for lessons, reports, Zoom meetings, cards, and statistics.

A learning profile can represent:

- one individual student;
- a pair;
- a group;
- a named class.

Examples:

- `Анна` — individual profile;
- `Мария + Катя` — group profile;
- `Speaking B1` — group profile.

This avoids forcing every Zoom lesson into a single-student model. For group meetings, statistics should be profile-level, not artificially split between students.

## Recommended MVP behavior

### 1. Teacher creates a profile

Teacher flow:

```text
[Добавить ученика]
[Добавить группу]
```

For an individual student:

1. Teacher enters name, e.g. `Анна`.
2. Backend creates:
   - `students` row for `Анна`;
   - `learning_profiles` row named `Анна` with type `individual`;
   - `learning_profile_members` row linking `Анна` to the profile.
3. Bot gives teacher an invite link for Anna.

For a group:

1. Teacher enters group name, e.g. `Speaking B1`.
2. Teacher adds member names, e.g. `Мария`, `Катя`, `Оля`.
3. Backend creates one `learning_profiles` row with type `group` and member `students` rows.
4. Bot gives separate invite links for each student.

### 2. Student connects through invite link

Invite link format:

```text
https://t.me/EnglishTutorHelperAIBot?start=student_<token>
```

When the student opens it:

1. Bot validates the invite token.
2. Bot links `student.telegram_user_id` to the Telegram user ID.
3. Bot sends a button to open the WebApp.

Security requirement:

- store only `invite_token_hash` in DB;
- never store raw invite token after creation;
- support revoking/regenerating invites;
- verify Telegram WebApp `initData` before returning student data.

### 3. Teacher links a Zoom meeting to a learning profile

Use a hybrid flow.

Existing command remains:

```text
/add_zoom_meeting <Zoom link>
```

New behavior:

1. Bot extracts the Zoom `meeting_id` as today.
2. If teacher has learning profiles, bot asks:

```text
К чему привязать эту конференцию?
[Анна]
[Speaking B1]
[Мария + Катя]
[Создать новый профиль]
[Без профиля]
```

3. The chosen `learning_profile_id` is saved on the Zoom meeting subscription.

Teacher WebApp should also support:

```text
Profile → Zoom conferences → Add conference
```

Both command and WebApp produce the same DB state.

### 4. Webhook creates lessons with profile context

Current behavior:

```text
Zoom webhook → find teacher → check meeting subscription → create lesson
```

New behavior:

```text
Zoom webhook → find teacher → check meeting subscription → get learning_profile_id → create lesson
```

`lessons.learning_profile_id` should be nullable during migration/backward compatibility, but new subscribed meetings should normally set it.

### 5. Analysis creates draft vocabulary cards

Prompt/schema should change from a simple list:

```json
"vocabulary": ["..."]
```

to structured cards:

```json
"vocabulary_cards": [
  {
    "term": "make progress",
    "translation_ru": "делать успехи",
    "definition_en": "to improve or move forward",
    "example_sentence": "She made great progress with pronunciation.",
    "source_phrase": "I make progress every lesson",
    "level": "A2"
  }
]
```

Cards should be saved as `draft` by default.

Default publication mode:

```text
manual_review
```

Future setting per learning profile:

```text
card_publish_mode = manual_review | auto_publish
```

For MVP, keep `manual_review` as the default and safest behavior.

### 6. Teacher reviews and publishes cards

After lesson analysis:

```text
Отчёт по уроку готов ✅

Профиль: Speaking B1
Новые карточки: 12

[Проверить карточки]
[Опубликовать все]
```

In teacher WebApp, the tutor can:

- view draft cards;
- edit term/translation/example/level;
- delete a card;
- publish one card;
- publish all cards from a lesson.

### 7. Student studies cards in WebApp

Student WebApp main screen:

```text
Мои карточки

Speaking B1
Новые: 12
На повторение: 5
Всего: 42

[Учить новые]
[Повторить]
[Все карточки]
```

If a student belongs to multiple profiles, show all profiles.

Card interaction:

```text
Front: make progress
Back: делать успехи
Example: She made great progress with pronunciation.

[Знаю]
[Повторить]
[Сложно]
```

## Data model

### `students`

```text
id
teacher_user_id -> users.id
name
telegram_user_id nullable
invite_token_hash nullable
invite_status: active | used | revoked
created_at
updated_at
```

Notes:

- `telegram_user_id` is nullable because the teacher can create a student before the student opens the bot.
- Invite token should be hashed.

### `learning_profiles`

```text
id
teacher_user_id -> users.id
name
profile_type: individual | group
card_publish_mode: manual_review | auto_publish
created_at
updated_at
```

### `learning_profile_members`

```text
id
learning_profile_id -> learning_profiles.id
student_id -> students.id
created_at
```

Unique constraint:

```text
(learning_profile_id, student_id)
```

### `zoom_meeting_subscriptions`

Add:

```text
learning_profile_id nullable -> learning_profiles.id
```

Existing uniqueness `(user_id, meeting_id)` can remain for now. A single teacher should not attach the same Zoom meeting to multiple profiles unless we deliberately support that later.

### `lessons`

Add:

```text
learning_profile_id nullable -> learning_profiles.id
```

A lesson’s profile comes from the matched Zoom meeting subscription at webhook time.

### `vocabulary_cards`

```text
id
teacher_user_id -> users.id
learning_profile_id -> learning_profiles.id
lesson_id nullable -> lessons.id
term
translation_ru
definition_en nullable
example_sentence nullable
source_phrase nullable
level nullable
status: draft | published | archived
created_at
updated_at
published_at nullable
```

Cards belong to the learning profile, not to a single student. For groups, the card is stored once and shown to every member.

### `student_card_progress`

```text
id
student_id -> students.id
card_id -> vocabulary_cards.id
status: new | learning | known | difficult
review_count
last_reviewed_at nullable
next_review_at nullable
created_at
updated_at
```

Unique constraint:

```text
(student_id, card_id)
```

This gives each student individual progress without duplicating cards.

## Statistics and “10th report” logic

Statistics should be learning-profile-level first.

Examples:

- `Анна`: individual profile progress after 10 lessons.
- `Speaking B1`: group progress after 10 group lessons.

For group lessons, do not try to infer individual speaking statistics from a shared transcript unless later we add reliable speaker attribution. The honest MVP approach is:

```text
one group lesson → one group report → one group vocabulary set
```

Cards are shared per profile, but each student has individual card progress.

Future milestone report trigger:

```text
when completed lessons count for learning_profile_id reaches 10, 20, 30, ...
```

Milestone report can summarize:

- recurring mistakes across reports;
- vocabulary themes;
- published card counts;
- difficult cards across members;
- next recommendations.

## Telegram commands and buttons

### Keep existing commands

```text
/start
/connect_zoom
/disconnect_zoom
/status
/last_report
/last_error
/add_zoom_meeting <link>
```

### Add later

```text
/add_student
/add_group
/profiles
/cards
```

However, for a WebApp-first UX, prefer buttons over many commands.

### Recommended teacher buttons

```text
[Открыть кабинет]
[Добавить ученика]
[Добавить группу]
[Подключить Zoom]
```

## WebApp screens

### Teacher WebApp

1. Dashboard
   - profiles list;
   - drafts waiting for review;
   - recent lessons.
2. Profile page
   - members;
   - Zoom meetings;
   - reports;
   - cards;
   - invite links.
3. Card review page
   - draft cards from latest lesson;
   - edit/delete/publish controls.
4. Add profile flow
   - individual or group;
   - member names;
   - invite generation.

### Student WebApp

1. Profile selector, if multiple profiles.
2. Cards dashboard.
3. Study mode.
4. All cards list.
5. Progress summary.

## API boundaries

Add new FastAPI routes under something like:

```text
/api/webapp/teacher/*
/api/webapp/student/*
```

All WebApp routes must verify Telegram `initData`.

Teacher routes require:

```text
Telegram user ID matches an allowed teacher user.
```

Student routes require:

```text
Telegram user ID is linked to a student record.
```

## Security requirements

1. Verify Telegram WebApp `initData` signature on every WebApp API request.
2. Store student invite tokens as hashes, not raw values.
3. Do not expose one teacher’s profiles/cards to another teacher.
4. Do not expose draft cards to students.
5. Do not expose Zoom tokens or internal meeting download URLs to WebApp clients.
6. Keep source lesson data deletion behavior unchanged after processing.
7. Keep the temporary silent-list available while developing so the real tutor is not disturbed.

## Error handling

### Student opens invalid/expired invite

Bot response:

```text
Ссылка недействительна или устарела. Попросите преподавателя отправить новую ссылку.
```

### Teacher adds Zoom meeting before profiles exist

Bot can ask:

```text
У вас пока нет учеников или групп. Создать профиль для этой конференции?
```

### Webhook finds meeting without profile

Allowed transitional behavior:

- create lesson without `learning_profile_id`;
- notify admin/teacher that the meeting is not linked to a profile;
- do not create student cards until linked.

### Analysis returns no vocabulary cards

Still send lesson report. Show:

```text
Новые карточки не найдены.
```

## Implementation sequence recommendation

Do this in stages, each with tests and deployment verification.

### Stage 1 — data model foundation

- add models/migrations for students, learning profiles, memberships, cards, progress;
- add `learning_profile_id` to subscriptions and lessons;
- add repositories;
- no user-facing behavior change yet.

### Stage 2 — teacher profile creation in Telegram

- add `/add_student` and `/add_group` or simple bot-button flows;
- generate invite links;
- connect invite links through `/start student_<token>`.

### Stage 3 — meeting-to-profile linking

- modify `/add_zoom_meeting` to ask profile selection;
- update webhook to attach profile to lesson.

### Stage 4 — vocabulary cards from analysis

- extend analysis schema and prompt;
- save draft `vocabulary_cards`;
- include draft-card count in teacher/admin report.

### Stage 5 — WebApp MVP

- implement Telegram WebApp auth verification;
- add teacher draft review page;
- add student card study page;
- serve static frontend from the monolith initially.

### Stage 6 — progress and milestone reports

- add study actions;
- add `student_card_progress` updates;
- implement profile-level milestone report triggers.

## Open decisions before implementation

1. Should Stage 2 start with Telegram commands only, or immediately with a minimal teacher WebApp?
2. Should groups support adding/removing members in MVP, or only create-once groups at first?
3. Should the first student WebApp be read-only flip cards, or include “Знаю / Сложно / Повторить” immediately?

## Recommended answers to open decisions

1. Start with Telegram commands plus simple inline buttons, then WebApp for cards. This reduces UI scope.
2. Support adding members after group creation; removing can be deferred.
3. Include the three review buttons immediately, but keep scheduling logic simple at first.
