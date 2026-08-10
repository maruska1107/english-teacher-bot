# Student Homework and Lesson Recaps Design

Date: 2026-08-10
Status: Approved for implementation

## Goal

Add a learner-facing “Домашка” experience that shows the current homework together with a friendly lesson recap, plus the previous homework/recap. Do not build long-term homework history in this MVP.

## Product Flow

After a Zoom lesson transcript is processed, the system prepares a lesson result package:

- teacher-facing report;
- learner-facing recap;
- homework items;
- draft vocabulary cards.

The teacher receives a review message and must confirm before anything new is sent to the student. Until confirmation, the student keeps seeing the previously confirmed homework/recap.

Teacher review message target copy:

```text
✨ Урок с Аней готов

📝 Домашка
Exercise 4, p. 32
Написать 5 предложений о выходных
Повторить слова урока

🧠 Карточки: 8 слов
📚 Итоги урока: готовы

[👀 Посмотреть всё]
[✏️ Изменить]
[✅ Подтвердить и отправить]
```

Learner Telegram message target copy after teacher confirmation:

```text
✨ Аня, итоги сегодняшнего урока готовы

Сегодня говорили о путешествиях и практиковали Past Simple.

📝 Домашка
✓ Exercise 4, page 32
✓ 5–7 предложений про последнюю поездку
✓ повторить 8 новых слов

🧠 Новые карточки: 8

[📝 Открыть ДЗ]
[🧠 Учить 8 слов]
```

The full learner recap appears in the WebApp “Домашка” section:

- short lesson summary;
- “Что получилось”;
- “Фокус” with wrong/correct examples when available;
- homework checklist;
- new cards count;
- previous homework/recap collapsed or secondary.

## Student UI

MVP bottom/navigation shape:

```text
Карточки · Домашка
```

The Homework view shows:

```text
📝 Домашка

Текущее ДЗ
После урока 10 августа

Сегодня говорили о путешествиях и Past Simple.

Фокус:
• was / were
• вопросы в Past Simple

Домашка:
✓ Exercise 4, page 32
✓ 5–7 предложений про последнюю поездку
✓ повторить 8 новых слов

[Учить 8 слов]

Предыдущее ДЗ →
```

If no confirmed homework exists:

```text
Пока домашки нет. После урока преподаватель отправит её сюда.
```

## Storage

Store only two learner-facing records per student/profile:

- current confirmed recap/homework;
- previous confirmed recap/homework.

When teacher confirms a new lesson result:

```text
previous = current
current = new confirmed lesson recap/homework
older data is overwritten
```

This MVP does not keep a permanent homework history.

Recommended shape for each recap/homework snapshot:

- student_id;
- learning_profile_id;
- lesson_id;
- slot: `current` or `previous`;
- lesson_date_label;
- summary_text;
- wins_text;
- focus_text;
- homework_items JSON list of strings;
- new_cards_count;
- created_at;
- updated_at.

## Teacher Confirmation

The existing lesson analysis pipeline may continue creating draft cards and teacher reports. The student-facing recap/homework is only published after teacher confirmation. For the first MVP slice, dev/test seed data may create confirmed homework directly so the student UI can be reviewed without waiting for Zoom transcript analysis.

## Scope exclusions

Do not implement in this slice:

- homework completion checkbox;
- student uploads;
- teacher comments on homework;
- due dates;
- reminders;
- long-term lesson/homework history;
- replacing the existing analysis engine.

## Safety and Access

Student API must use existing Telegram WebApp auth and return only homework for the linked student. Teacher APIs must preserve existing teacher ownership checks. No Zoom, Telegram, OpenAI, or database secrets are exposed in UI or logs.

## Testing

Automated tests should cover:

- current homework is shifted to previous when a new one is confirmed;
- only current and previous slots remain;
- student API rejects unauthenticated/unlinked users;
- student API returns current and previous homework for the linked student;
- student WebApp contains “Карточки” and “Домашка” sections;
- no-homework empty state.

Deployment verification should cover:

- full `./scripts/test_all.sh`;
- `/health` and `/ready`;
- Alembic revision;
- production HTML/API markers;
- backend logs without errors.
