"""Terra knowledge schema: additive columns, corpus tables and FTS5.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.db.migrate import upgrade_schema_sync

    upgrade_schema_sync(op.get_bind())


def downgrade() -> None:
    # SQLite cannot drop columns portably. Forward-only for the local app.
    pass
