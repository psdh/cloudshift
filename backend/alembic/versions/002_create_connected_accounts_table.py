"""create connected_accounts table

Revision ID: 002
Revises: 001
Create Date: 2026-01-06 06:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create connected_accounts table
    op.create_table(
        'connected_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.Enum('onedrive', 'google_drive', name='cloudprovider'), nullable=False),
        sa.Column('access_token', sa.String(length=1000), nullable=False),
        sa.Column('refresh_token', sa.String(length=1000), nullable=True),
        sa.Column('token_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('account_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'provider', name='uix_user_provider')
    )

    # Create indexes
    op.create_index(op.f('ix_connected_accounts_id'), 'connected_accounts', ['id'], unique=False)
    op.create_index(op.f('ix_connected_accounts_user_id'), 'connected_accounts', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_connected_accounts_user_id'), table_name='connected_accounts')
    op.drop_index(op.f('ix_connected_accounts_id'), table_name='connected_accounts')

    # Drop table
    op.drop_table('connected_accounts')

    # Drop enum type
    op.execute('DROP TYPE cloudprovider')
