"""notifications system — notifications, notification_preferences, device_tokens

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("transaction_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("security_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("monthly_summary", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("milestone_alerts", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("maturity_reminders", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "device_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(512), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False, server_default="android"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_device_tokens_user_id", "device_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_table("device_tokens")
    op.drop_table("notification_preferences")
    op.drop_index("ix_notifications_created_at", "notifications")
    op.drop_index("ix_notifications_user_id", "notifications")
    op.drop_table("notifications")
