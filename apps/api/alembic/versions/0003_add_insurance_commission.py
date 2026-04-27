"""add commission_amount and product_name to insurance_policies

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-27

Adds:
  - commission_amount BIGINT (XAF earned by TerahBank per referral)
  - product_name VARCHAR(255) (denormalized from partner catalog for display)
  - index on expiry_date (used by renewal notifier daily query)
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_policies",
        sa.Column("commission_amount", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "insurance_policies",
        sa.Column("product_name", sa.String(255), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_insurance_policies_expiry_date",
        "insurance_policies",
        ["expiry_date"],
    )
    op.create_index(
        "ix_insurance_policies_user_id",
        "insurance_policies",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_insurance_policies_user_id", table_name="insurance_policies")
    op.drop_index("ix_insurance_policies_expiry_date", table_name="insurance_policies")
    op.drop_column("insurance_policies", "product_name")
    op.drop_column("insurance_policies", "commission_amount")
