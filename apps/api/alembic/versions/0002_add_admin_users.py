"""add admin_users table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-24

FR-056: Separate admin user table — never mixed with regular users.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, INET

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE admin_role_enum AS ENUM (
                'super_admin', 'operations_staff', 'read_only_analyst'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;

        CREATE TABLE IF NOT EXISTS admin_users (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email       VARCHAR(255) NOT NULL,
            full_name   VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role        admin_role_enum NOT NULL,
            totp_secret VARCHAR(64),
            is_active   BOOLEAN NOT NULL DEFAULT true,
            last_login_at TIMESTAMPTZ,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_admin_users_email UNIQUE (email)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS ix_admin_users_email ON admin_users (email);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_admin_users_email;
        DROP TABLE IF EXISTS admin_users;
        DROP TYPE IF EXISTS admin_role_enum;
    """)
