"""add pin_hash to users

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-27

FR-006/FR-036: PIN setup and verification — bcrypt hash of user PIN stored here.
Column is nullable so existing users without a PIN are unaffected.
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS pin_hash VARCHAR(255) NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS pin_hash;
    """)
