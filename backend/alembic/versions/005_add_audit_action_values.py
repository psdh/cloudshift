"""add audit action enum values

Adds transfer_conflict_detected, transfer_conflict_resolved and system_error
to the auditaction enum (used by the transfer worker and rate limiter).

Revision ID: 005
Revises: 004
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUES = (
    'transfer_conflict_detected',
    'transfer_conflict_resolved',
    'system_error',
)


def upgrade() -> None:
    # PostgreSQL native enum: add the new members in-place. IF NOT EXISTS keeps
    # this idempotent (PostgreSQL 12+ allows ADD VALUE inside a transaction).
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        for value in _NEW_VALUES:
            op.execute(
                f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{value}'"
            )
    # On other dialects (e.g. SQLite used in tests) the enum is a VARCHAR with
    # a CHECK constraint rebuilt from the model metadata, so nothing to do.


def downgrade() -> None:
    # PostgreSQL does not support removing a value from an enum type without
    # recreating the type and rewriting every dependent column. This is a
    # non-reversible additive migration by design.
    pass
