from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ZoomMeetingSubscription


class ZoomMeetingSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_for_user(
        self,
        user_id: int,
        meeting_id: str,
        meeting_url: str,
        learning_profile_id: int | None = None,
    ) -> ZoomMeetingSubscription:
        subscription = self.session.scalar(
            select(ZoomMeetingSubscription).where(
                ZoomMeetingSubscription.user_id == user_id,
                ZoomMeetingSubscription.meeting_id == meeting_id,
            )
        )
        if subscription is None:
            subscription = ZoomMeetingSubscription(
                user_id=user_id,
                learning_profile_id=learning_profile_id,
                meeting_id=meeting_id,
                meeting_url=meeting_url,
                is_active=True,
            )
            self.session.add(subscription)
        else:
            subscription.meeting_url = meeting_url
            subscription.learning_profile_id = learning_profile_id
            subscription.is_active = True
        self.session.flush()
        return subscription

    def active_for_user_and_meeting(self, user_id: int, meeting_id: str) -> ZoomMeetingSubscription | None:
        return self.session.scalar(
            select(ZoomMeetingSubscription).where(
                ZoomMeetingSubscription.user_id == user_id,
                ZoomMeetingSubscription.meeting_id == meeting_id,
                ZoomMeetingSubscription.is_active.is_(True),
            )
        )

    def active_exists(self, user_id: int, meeting_id: str) -> bool:
        return self.active_for_user_and_meeting(user_id=user_id, meeting_id=meeting_id) is not None

    def count_active_for_user(self, user_id: int) -> int:
        return len(
            self.session.scalars(
                select(ZoomMeetingSubscription.id).where(
                    ZoomMeetingSubscription.user_id == user_id,
                    ZoomMeetingSubscription.is_active.is_(True),
                )
            ).all()
        )
