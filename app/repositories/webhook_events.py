from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProcessedWebhookEvent


class ProcessedWebhookEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, event_id: str) -> ProcessedWebhookEvent | None:
        return self.session.scalar(select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.event_id == event_id))

    def create(self, event_id: str, event_type: str, status: str) -> ProcessedWebhookEvent:
        event = ProcessedWebhookEvent(event_id=event_id, event_type=event_type, status=status)
        self.session.add(event)
        self.session.flush()
        return event
