"""add vocabulary card image metadata

Revision ID: 0006_vocabulary_card_images
Revises: 0005_learning_profiles_cards
Create Date: 2026-08-03 00:00:06.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_vocabulary_card_images"
down_revision: str | None = "0005_learning_profiles_cards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vocabulary_cards", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("vocabulary_cards", sa.Column("image_source_url", sa.Text(), nullable=True))
    op.add_column("vocabulary_cards", sa.Column("image_creator", sa.String(length=255), nullable=True))
    op.add_column("vocabulary_cards", sa.Column("image_license", sa.String(length=50), nullable=True))
    op.add_column("vocabulary_cards", sa.Column("image_license_url", sa.Text(), nullable=True))
    op.add_column("vocabulary_cards", sa.Column("image_search_query", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vocabulary_cards", "image_search_query")
    op.drop_column("vocabulary_cards", "image_license_url")
    op.drop_column("vocabulary_cards", "image_license")
    op.drop_column("vocabulary_cards", "image_creator")
    op.drop_column("vocabulary_cards", "image_source_url")
    op.drop_column("vocabulary_cards", "image_url")
