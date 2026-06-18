"""add in_progress, completed status and reject_reason

Revision ID: add_status_fields
Revises: 36cc78853d5b
Create Date: 2026-06-11 13:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'add_status_fields'
down_revision: Union[str, Sequence[str], None] = '36cc78853d5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новые значения в enum initiativestatus (UPPERCASE для совместимости с оригинальной миграцией)
    op.execute("ALTER TYPE initiativestatus ADD VALUE IF NOT EXISTS 'IN_PROGRESS'")
    op.execute("ALTER TYPE initiativestatus ADD VALUE IF NOT EXISTS 'COMPLETED'")
    
    # Добавляем колонку для причины отклонения
    op.add_column('initiatives', sa.Column('reject_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('initiatives', 'reject_reason')
    
    # Примечание: удалить значения из enum нельзя напрямую в PostgreSQL
    # Потребуется создать новый тип, но в MVP опустим этот шаг