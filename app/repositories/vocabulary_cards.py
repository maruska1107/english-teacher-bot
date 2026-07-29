from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningProfileMember, StudentCardProgress, VocabularyCard
from app.schemas.cards import VocabularyCardCreate, VocabularyCardUpdate


def _strip_optional(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


class VocabularyCardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_draft_cards(
        self,
        teacher_user_id: int,
        learning_profile_id: int,
        lesson_id: int | None,
        cards: list[dict[str, str | None]],
    ) -> list[VocabularyCard]:
        saved_cards = [
            VocabularyCard(
                teacher_user_id=teacher_user_id,
                learning_profile_id=learning_profile_id,
                lesson_id=lesson_id,
                term=str(card["term"]).strip(),
                translation_ru=str(card["translation_ru"]).strip(),
                definition_en=card.get("definition_en"),
                example_sentence=card.get("example_sentence"),
                source_phrase=card.get("source_phrase"),
                level=card.get("level"),
                status="draft",
            )
            for card in cards
            if card.get("term") and card.get("translation_ru")
        ]
        self.session.add_all(saved_cards)
        self.session.flush()
        return saved_cards

    def create_manual_draft_card(self, teacher_user_id: int, payload: VocabularyCardCreate) -> VocabularyCard:
        card = VocabularyCard(
            teacher_user_id=teacher_user_id,
            learning_profile_id=payload.learning_profile_id,
            lesson_id=None,
            term=payload.term.strip(),
            translation_ru=payload.translation_ru.strip(),
            definition_en=_strip_optional(payload.definition_en),
            example_sentence=_strip_optional(payload.example_sentence),
            source_phrase=_strip_optional(payload.source_phrase),
            level=_strip_optional(payload.level),
            status="draft",
        )
        self.session.add(card)
        self.session.flush()
        return card

    def list_for_teacher(
        self,
        teacher_user_id: int,
        learning_profile_id: int | None = None,
        status: str | None = None,
    ) -> list[VocabularyCard]:
        query = select(VocabularyCard).where(VocabularyCard.teacher_user_id == teacher_user_id)
        if learning_profile_id is not None:
            query = query.where(VocabularyCard.learning_profile_id == learning_profile_id)
        if status is not None:
            query = query.where(VocabularyCard.status == status)
        query = query.order_by(VocabularyCard.created_at.desc(), VocabularyCard.id.desc())
        return list(self.session.scalars(query))

    def list_published_for_student(self, student_id: int) -> list[tuple[VocabularyCard, str]]:
        rows = self.session.execute(
            select(VocabularyCard, StudentCardProgress.status)
            .join(
                LearningProfileMember,
                LearningProfileMember.learning_profile_id == VocabularyCard.learning_profile_id,
            )
            .outerjoin(
                StudentCardProgress,
                (StudentCardProgress.card_id == VocabularyCard.id) & (StudentCardProgress.student_id == student_id),
            )
            .where(
                LearningProfileMember.student_id == student_id,
                VocabularyCard.status == "published",
            )
            .order_by(VocabularyCard.created_at.desc(), VocabularyCard.id.desc())
        ).all()
        return [(card, progress_status or "new") for card, progress_status in rows]

    def get_published_for_student(self, student_id: int, card_id: int) -> VocabularyCard | None:
        return self.session.scalar(
            select(VocabularyCard)
            .join(
                LearningProfileMember,
                LearningProfileMember.learning_profile_id == VocabularyCard.learning_profile_id,
            )
            .where(
                LearningProfileMember.student_id == student_id,
                VocabularyCard.id == card_id,
                VocabularyCard.status == "published",
            )
        )

    def get_for_teacher(self, teacher_user_id: int, card_id: int) -> VocabularyCard | None:
        return self.session.scalar(
            select(VocabularyCard).where(
                VocabularyCard.teacher_user_id == teacher_user_id,
                VocabularyCard.id == card_id,
            )
        )

    def update_card(self, card: VocabularyCard, payload: VocabularyCardUpdate) -> VocabularyCard:
        update_data = payload.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(card, field_name, value.strip() if isinstance(value, str) else value)
        self.session.flush()
        return card

    def set_status(self, card: VocabularyCard, status: str) -> VocabularyCard:
        card.status = status
        if status == "published" and card.published_at is None:
            card.published_at = datetime.now(UTC)
        self.session.flush()
        return card

    def delete_card(self, card: VocabularyCard) -> None:
        self.session.delete(card)
        self.session.flush()

    def publish_draft_cards_for_profile(self, teacher_user_id: int, learning_profile_id: int) -> int:
        cards = self.list_for_teacher(
            teacher_user_id=teacher_user_id,
            learning_profile_id=learning_profile_id,
            status="draft",
        )
        for card in cards:
            self.set_status(card, "published")
        self.session.flush()
        return len(cards)
