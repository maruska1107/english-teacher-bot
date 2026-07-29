from sqlalchemy.orm import Session

from app.models import VocabularyCard


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
