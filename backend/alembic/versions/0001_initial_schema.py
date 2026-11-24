"""Baseline: full TravelGraph schema.

Revision ID: 0001
Revises:
Create Date: 2026-11-18

Baseline stub: builds the schema from the current SQLAlchemy models (checkfirst, so it is a no-op
when `app.db.migrate.create_all` already ran). Later revisions should be generated with
`alembic revision --autogenerate` and contain explicit operations.
"""
from typing import Sequence, Union

from alembic import op

import app.models  # noqa: F401
from app.db.base import Base

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
