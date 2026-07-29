# Learning Profiles Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the database/model foundation for students, learning profiles, profile memberships, vocabulary cards, student card progress, and profile links from Zoom subscriptions/lessons.

**Architecture:** Keep the existing FastAPI monolith and SQLAlchemy 2.x patterns. This stage is data-only: models, repositories, Alembic migration, tests, exports, and no user-facing Telegram/WebApp behavior changes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x typed models, Alembic, PostgreSQL, Docker Compose, pytest, ruff.

## Global Constraints

- Work in `/opt/english-teacher-bot` on branch `feat/mvp-foundation`.
- Use strict TDD: write failing tests first and verify failure before implementation.
- Docker-first verification: run tests in `docker compose run --rm backend` with source mounts.
- Do not output `.env` values, API keys, tokens, passwords, OAuth tokens, or connection strings.
- Keep `SILENT_TELEGRAM_USER_IDS=925045715` active in production `.env`; do not message the tutor during development.
- Do not add Redis/Celery/RabbitMQ/Kafka/Kubernetes or new services.
- Keep source lesson data deletion behavior unchanged.
- Use nullable foreign keys for migration compatibility where existing rows may lack profile context.

---

### Task 1: Schema tests for learning profile entities

**Files:**
- Modify: `tests/test_foundation.py`
- Later tasks create/modify model files.

**Interfaces:**
- Consumes: existing `Base`, `User`, `Lesson`, `ZoomMeetingSubscription` model imports.
- Produces: failing tests that define expected model class names and relationships:
  - `Student`
  - `LearningProfile`
  - `LearningProfileMember`
  - `VocabularyCard`
  - `StudentCardProgress`

- [ ] **Step 1: Write the failing schema test**

Append imports to `tests/test_foundation.py`:

```python
from app.models import (
    LearningProfile,
    LearningProfileMember,
    Student,
    StudentCardProgress,
    VocabularyCard,
)
```

Add a test:

```python
def test_database_schema_supports_learning_profiles_and_cards():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        teacher = User(telegram_user_id=956230172, role="teacher", is_active=True)
        session.add(teacher)
        session.flush()

        student = Student(
            teacher_user_id=teacher.id,
            name="Анна",
            telegram_user_id=111222333,
            invite_token_hash="hashed-token",
            invite_status="active",
        )
        profile = LearningProfile(
            teacher_user_id=teacher.id,
            name="Анна",
            profile_type="individual",
            card_publish_mode="manual_review",
        )
        session.add_all([student, profile])
        session.flush()

        membership = LearningProfileMember(
            learning_profile_id=profile.id,
            student_id=student.id,
        )
        subscription = ZoomMeetingSubscription(
            user_id=teacher.id,
            learning_profile_id=profile.id,
            meeting_id="987654321",
            meeting_url="https://example.zoom.us/j/987654321",
            is_active=True,
        )
        lesson = Lesson(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            meeting_id="987654321",
            meeting_uuid="meeting-uuid-learning-profile",
            processing_status="completed",
        )
        session.add_all([membership, subscription, lesson])
        session.flush()

        card = VocabularyCard(
            teacher_user_id=teacher.id,
            learning_profile_id=profile.id,
            lesson_id=lesson.id,
            term="make progress",
            translation_ru="делать успехи",
            definition_en="to improve",
            example_sentence="She made progress with pronunciation.",
            source_phrase="make progress",
            level="A2",
            status="draft",
        )
        session.add(card)
        session.flush()

        progress = StudentCardProgress(
            student_id=student.id,
            card_id=card.id,
            status="new",
            review_count=0,
        )
        session.add(progress)
        session.commit()

        saved_profile = session.get(LearningProfile, profile.id)
        assert saved_profile.teacher.telegram_user_id == 956230172
        assert saved_profile.memberships[0].student.name == "Анна"
        assert saved_profile.zoom_meeting_subscriptions[0].meeting_id == "987654321"
        assert saved_profile.lessons[0].meeting_uuid == "meeting-uuid-learning-profile"
        assert saved_profile.vocabulary_cards[0].term == "make progress"
        assert saved_profile.vocabulary_cards[0].student_progress[0].student.name == "Анна"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /opt/english-teacher-bot && chmod -R a+rX tests app alembic pyproject.toml && docker compose run --rm --entrypoint sh -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" -v "$PWD/alembic:/app/alembic:ro" -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" backend -c 'pytest tests/test_foundation.py::test_database_schema_supports_learning_profiles_and_cards -q'
```

Expected: FAIL because new model classes are not importable.

- [ ] **Step 3: Commit after Task 2 passes, not before**

No commit in Task 1 alone; this test becomes green in Task 2.

---

### Task 2: SQLAlchemy models and exports

**Files:**
- Create: `app/models/student.py`
- Create: `app/models/learning_profile.py`
- Create: `app/models/learning_profile_member.py`
- Create: `app/models/vocabulary_card.py`
- Create: `app/models/student_card_progress.py`
- Modify: `app/models/user.py`
- Modify: `app/models/lesson.py`
- Modify: `app/models/zoom_meeting_subscription.py`
- Modify: `app/models/__init__.py`
- Test: `tests/test_foundation.py`

**Interfaces:**
- Produces model classes imported by tests and Alembic:
  - `Student`
  - `LearningProfile`
  - `LearningProfileMember`
  - `VocabularyCard`
  - `StudentCardProgress`
- Adds nullable `learning_profile_id` to `Lesson` and `ZoomMeetingSubscription`.

- [ ] **Step 1: Implement model files**

Create `app/models/student.py`:

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("teacher_user_id", "name", name="uq_students_teacher_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    invite_token_hash: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    invite_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher = relationship("User", back_populates="students")
    memberships = relationship("LearningProfileMember", back_populates="student", cascade="all, delete-orphan")
    card_progress = relationship("StudentCardProgress", back_populates="student", cascade="all, delete-orphan")
```

Create `app/models/learning_profile.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LearningProfile(Base):
    __tablename__ = "learning_profiles"
    __table_args__ = (UniqueConstraint("teacher_user_id", "name", name="uq_learning_profiles_teacher_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_type: Mapped[str] = mapped_column(String(50), nullable=False)
    card_publish_mode: Mapped[str] = mapped_column(String(50), default="manual_review", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    teacher = relationship("User", back_populates="learning_profiles")
    memberships = relationship("LearningProfileMember", back_populates="learning_profile", cascade="all, delete-orphan")
    zoom_meeting_subscriptions = relationship("ZoomMeetingSubscription", back_populates="learning_profile")
    lessons = relationship("Lesson", back_populates="learning_profile")
    vocabulary_cards = relationship("VocabularyCard", back_populates="learning_profile", cascade="all, delete-orphan")
```

Create `app/models/learning_profile_member.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LearningProfileMember(Base):
    __tablename__ = "learning_profile_members"
    __table_args__ = (UniqueConstraint("learning_profile_id", "student_id", name="uq_learning_profile_members_profile_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    learning_profile_id: Mapped[int] = mapped_column(
        ForeignKey("learning_profiles.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    learning_profile = relationship("LearningProfile", back_populates="memberships")
    student = relationship("Student", back_populates="memberships")
```

Create `app/models/vocabulary_card.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VocabularyCard(Base):
    __tablename__ = "vocabulary_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    learning_profile_id: Mapped[int] = mapped_column(ForeignKey("learning_profiles.id", ondelete="CASCADE"), index=True)
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id", ondelete="SET NULL"), index=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False)
    translation_ru: Mapped[str] = mapped_column(String(255), nullable=False)
    definition_en: Mapped[str | None] = mapped_column(Text)
    example_sentence: Mapped[str | None] = mapped_column(Text)
    source_phrase: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    teacher = relationship("User", back_populates="vocabulary_cards")
    learning_profile = relationship("LearningProfile", back_populates="vocabulary_cards")
    lesson = relationship("Lesson", back_populates="vocabulary_cards")
    student_progress = relationship("StudentCardProgress", back_populates="card", cascade="all, delete-orphan")
```

Create `app/models/student_card_progress.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentCardProgress(Base):
    __tablename__ = "student_card_progress"
    __table_args__ = (UniqueConstraint("student_id", "card_id", name="uq_student_card_progress_student_card"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("vocabulary_cards.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    review_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    student = relationship("Student", back_populates="card_progress")
    card = relationship("VocabularyCard", back_populates="student_progress")
```

- [ ] **Step 2: Modify existing relationships**

In `app/models/user.py`, add relationships:

```python
    students = relationship("Student", back_populates="teacher", cascade="all, delete-orphan")
    learning_profiles = relationship("LearningProfile", back_populates="teacher", cascade="all, delete-orphan")
    vocabulary_cards = relationship("VocabularyCard", back_populates="teacher", cascade="all, delete-orphan")
```

In `app/models/lesson.py`, add import `Integer` if needed is not needed. Add column:

```python
    learning_profile_id: Mapped[int | None] = mapped_column(ForeignKey("learning_profiles.id", ondelete="SET NULL"), index=True)
```

Add relationships:

```python
    learning_profile = relationship("LearningProfile", back_populates="lessons")
    vocabulary_cards = relationship("VocabularyCard", back_populates="lesson")
```

In `app/models/zoom_meeting_subscription.py`, add column:

```python
    learning_profile_id: Mapped[int | None] = mapped_column(ForeignKey("learning_profiles.id", ondelete="SET NULL"), index=True)
```

Add relationship:

```python
    learning_profile = relationship("LearningProfile", back_populates="zoom_meeting_subscriptions")
```

In `app/models/__init__.py`, export all new classes.

- [ ] **Step 3: Run schema test to verify pass**

Run the same command from Task 1 Step 2.

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add app/models tests/test_foundation.py
git commit -m "feat: add learning profile data models"
```

---

### Task 3: Alembic migration for learning profile tables

**Files:**
- Create: `alembic/versions/0005_learning_profiles_cards.py`
- Test: `tests/test_foundation.py`

**Interfaces:**
- Consumes model definitions from Task 2.
- Produces DB migration revision `0005_learning_profiles_cards` with `down_revision = "0004_zoom_meeting_subscriptions"`.

- [ ] **Step 1: Create migration file**

Create `alembic/versions/0005_learning_profiles_cards.py` with operations to:

1. create `students`;
2. create `learning_profiles`;
3. create `learning_profile_members`;
4. add nullable `learning_profile_id` to `zoom_meeting_subscriptions`;
5. add nullable `learning_profile_id` to `lessons`;
6. create `vocabulary_cards`;
7. create `student_card_progress`;
8. create indexes and unique constraints matching models.

- [ ] **Step 2: Verify migration chain**

Run:

```bash
cd /opt/english-teacher-bot && docker compose run --rm --entrypoint sh -v "$PWD/app:/app/app:ro" -v "$PWD/alembic:/app/alembic:ro" -v "$PWD/alembic.ini:/app/alembic.ini:ro" -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" backend -c 'alembic upgrade head && alembic current'
```

Expected: current revision includes `0005_learning_profiles_cards`.

- [ ] **Step 3: Run full tests**

Run:

```bash
cd /opt/english-teacher-bot && chmod -R a+rX tests app alembic pyproject.toml && docker compose run --rm --entrypoint sh -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" -v "$PWD/alembic:/app/alembic:ro" -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" backend -c 'pytest tests -q'
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add alembic/versions/0005_learning_profiles_cards.py
git commit -m "feat: add learning profile migration"
```

---

### Task 4: Repositories for profiles and cards

**Files:**
- Create: `app/repositories/students.py`
- Create: `app/repositories/learning_profiles.py`
- Create: `app/repositories/vocabulary_cards.py`
- Create/Modify: `tests/test_learning_profiles.py`

**Interfaces:**
- Produces:
  - `StudentRepository.get_or_create_for_teacher(name: str, teacher_user_id: int) -> Student`
  - `LearningProfileRepository.create_individual_profile(teacher_user_id: int, student_name: str) -> tuple[LearningProfile, Student]`
  - `LearningProfileRepository.create_group_profile(teacher_user_id: int, profile_name: str, member_names: list[str]) -> LearningProfile`
  - `LearningProfileRepository.list_for_teacher(teacher_user_id: int) -> list[LearningProfile]`
  - `VocabularyCardRepository.create_draft_cards(teacher_user_id: int, learning_profile_id: int, lesson_id: int | None, cards: list[dict[str, str | None]]) -> list[VocabularyCard]`

- [ ] **Step 1: Write failing repository tests**

Create `tests/test_learning_profiles.py` testing:

1. individual profile creation creates one student and one membership;
2. group profile creation creates all members;
3. listing profiles is teacher-scoped;
4. draft cards are saved for a profile with status `draft`.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd /opt/english-teacher-bot && chmod -R a+rX tests app alembic pyproject.toml && docker compose run --rm --entrypoint sh -v "$PWD/tests:/app/tests:ro" -v "$PWD/app:/app/app:ro" -v "$PWD/alembic:/app/alembic:ro" -v "$PWD/pyproject.toml:/app/pyproject.toml:ro" backend -c 'pytest tests/test_learning_profiles.py -q'
```

Expected: FAIL because repositories do not exist.

- [ ] **Step 3: Implement repositories minimally**

Follow existing repository style: constructor accepts `Session`, methods use SQLAlchemy `select`, no commits inside repository unless existing project pattern requires it. Caller owns commit.

- [ ] **Step 4: Run repository tests to verify pass**

Run same command as Step 2.

Expected: PASS.

- [ ] **Step 5: Run full tests and ruff**

Run full pytest and ruff commands from Task 3.

Expected: PASS and ruff OK.

- [ ] **Step 6: Commit**

```bash
git add app/repositories tests/test_learning_profiles.py
git commit -m "feat: add learning profile repositories"
```

---

### Task 5: Deploy data foundation safely

**Files:**
- Runtime only: no additional code changes unless verification exposes an issue.

**Interfaces:**
- Consumes commits from Tasks 2-4.
- Produces deployed backend with Alembic revision `0005_learning_profiles_cards` applied.

- [ ] **Step 1: Build and restart backend/nginx**

Run:

```bash
cd /opt/english-teacher-bot && docker compose up -d --build backend nginx
```

Expected: backend starts and migrations run.

- [ ] **Step 2: Verify public health**

Run:

```bash
curl -fsS https://englishtutorai.ru/health && printf '\n' && curl -fsS https://englishtutorai.ru/ready && printf '\n'
```

Expected:

```text
{"status":"ok","service":"english-teacher-bot"}
{"status":"ready","database":"ok"}
```

- [ ] **Step 3: Verify DB migration version without secrets**

Run:

```bash
cd /opt/english-teacher-bot && docker compose exec -T postgres psql -U english_teacher -d english_teacher_bot -c "select version_num from alembic_version;"
```

Expected: `0005_learning_profiles_cards`.

- [ ] **Step 4: Push all commits**

Run:

```bash
git push
```

Expected: branch `feat/mvp-foundation` pushed.
