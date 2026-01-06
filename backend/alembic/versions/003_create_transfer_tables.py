"""create transfer tables

Revision ID: 003
Revises: 002
Create Date: 2026-01-06 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    op.execute("""
        CREATE TYPE jobstatus AS ENUM (
            'draft', 'pending', 'running', 'paused',
            'completed', 'failed', 'cancelled', 'scheduled'
        )
    """)
    op.execute("""
        CREATE TYPE itemstatus AS ENUM (
            'pending', 'in_progress', 'completed', 'failed', 'skipped'
        )
    """)
    op.execute("""
        CREATE TYPE conflictresolution AS ENUM (
            'ask', 'skip', 'rename', 'overwrite'
        )
    """)

    # Create transfer_jobs table
    op.create_table(
        'transfer_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('draft', 'pending', 'running', 'paused', 'completed', 'failed', 'cancelled', 'scheduled', name='jobstatus'), nullable=False),
        sa.Column('source_provider', sa.String(length=50), nullable=False),
        sa.Column('dest_provider', sa.String(length=50), nullable=False),
        sa.Column('source_folder_id', sa.String(length=500), nullable=True),
        sa.Column('dest_folder_id', sa.String(length=500), nullable=True),
        sa.Column('config', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create indexes for transfer_jobs
    op.create_index(op.f('ix_transfer_jobs_id'), 'transfer_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_transfer_jobs_user_id'), 'transfer_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_transfer_jobs_status'), 'transfer_jobs', ['status'], unique=False)

    # Create transfer_items table
    op.create_table(
        'transfer_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('source_file_id', sa.String(length=500), nullable=False),
        sa.Column('source_path', sa.Text(), nullable=False),
        sa.Column('dest_path', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'in_progress', 'completed', 'failed', 'skipped', name='itemstatus'), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['transfer_jobs.id'], ondelete='CASCADE')
    )

    # Create indexes for transfer_items
    op.create_index(op.f('ix_transfer_items_id'), 'transfer_items', ['id'], unique=False)
    op.create_index(op.f('ix_transfer_items_job_id'), 'transfer_items', ['job_id'], unique=False)
    op.create_index(op.f('ix_transfer_items_status'), 'transfer_items', ['status'], unique=False)

    # Create conflict_records table
    op.create_table(
        'conflict_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('resolution', sa.Enum('ask', 'skip', 'rename', 'overwrite', name='conflictresolution'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['job_id'], ['transfer_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['item_id'], ['transfer_items.id'], ondelete='CASCADE')
    )

    # Create indexes for conflict_records
    op.create_index(op.f('ix_conflict_records_id'), 'conflict_records', ['id'], unique=False)
    op.create_index(op.f('ix_conflict_records_job_id'), 'conflict_records', ['job_id'], unique=False)
    op.create_index(op.f('ix_conflict_records_item_id'), 'conflict_records', ['item_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_conflict_records_item_id'), table_name='conflict_records')
    op.drop_index(op.f('ix_conflict_records_job_id'), table_name='conflict_records')
    op.drop_index(op.f('ix_conflict_records_id'), table_name='conflict_records')
    op.drop_index(op.f('ix_transfer_items_status'), table_name='transfer_items')
    op.drop_index(op.f('ix_transfer_items_job_id'), table_name='transfer_items')
    op.drop_index(op.f('ix_transfer_items_id'), table_name='transfer_items')
    op.drop_index(op.f('ix_transfer_jobs_status'), table_name='transfer_jobs')
    op.drop_index(op.f('ix_transfer_jobs_user_id'), table_name='transfer_jobs')
    op.drop_index(op.f('ix_transfer_jobs_id'), table_name='transfer_jobs')

    # Drop tables
    op.drop_table('conflict_records')
    op.drop_table('transfer_items')
    op.drop_table('transfer_jobs')

    # Drop enums
    op.execute('DROP TYPE conflictresolution')
    op.execute('DROP TYPE itemstatus')
    op.execute('DROP TYPE jobstatus')
