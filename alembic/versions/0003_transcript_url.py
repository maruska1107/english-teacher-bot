"""add lesson transcript download url

Revision ID: 0003_transcript_url
Revises: 0002_zoom_oauth_states
Create Date: 2026-07-22 00:00:02.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_transcript_url"
down_revision: str | None = "0002_zoom_oauth_states"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("lessons", sa.Column("transcript_download_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("lessons", "transcript_download_url")
