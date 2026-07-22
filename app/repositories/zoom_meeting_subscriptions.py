from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ZoomMeetingSubscription


class ZoomMeetingSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_for_user(self, user_id: int, meeting_id: str, meeting_url: str) -> ZoomMeetingSubscription:
        subscription = self.session.scalar(
            select(ZoomMeetingSubscription).where(
                ZoomMeetingSubscription.user_id == user_id,
                ZoomMeetingSubscription.meeting_id == meeting_id,
            )
        )
        if subscription is None:
            subscription = ZoomMeetingSubscription(
                user_id=user_id,
                meeting_id=meeting_id,
                meeting_url=meeting_url,
                is_active=True,
            )
            self.session.add(subscription)
        else:
            subscription.meeting_url = meeting_url
            subscription.is_active = True
        self.session.flush()
        return subscription

    def active_exists(self, user_id: int, meeting_id: str) -> bool:
        return (
            self.session.scalar(
                select(ZoomMeetingSubscription.id).where(
                    ZoomMeetingSubscription.user_id == user_id,
                    ZoomMeetingSubscription.meeting_id == meeting_id,
                    ZoomMeetingSubscription.is_active.is_(True),
                )
            )
            is not None
        )

    def count_active_for_user(self, user_id: int) -> int:
        return len(
            self.session.scalars(
                select(ZoomMeetingSubscription.id).where(
                    ZoomMeetingSubscription.user_id == user_id,
                    ZoomMeetingSubscription.is_active.is_(True),
                )
            ).all()
        )
