"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-20 00:00:00.000000

Creates all core tables and indexes for the TerahBank initial release.
Also enforces audit_log immutability by revoking UPDATE/DELETE from the
API service account (terahbank_user).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Pre-built ENUM helpers — create_type=False means we manage creation ourselves
# via the explicit CREATE TYPE calls below, preventing double-create errors.
_kyc_status        = postgresql.ENUM("pending", "approved", "rejected",          name="kyc_status_enum",      create_type=False)
_acct_status       = postgresql.ENUM("active", "suspended", "closed",            name="acct_status_enum",     create_type=False)
_acct_type         = postgresql.ENUM("standard", "project", "term_deposit",      name="acct_type_enum",       create_type=False)
_acct_stat         = postgresql.ENUM("active", "closed", "locked",               name="acct_stat_enum",       create_type=False)
_txn_type          = postgresql.ENUM("deposit", "withdrawal", "transfer", "fee", "interest", "penalty", name="txn_type_enum", create_type=False)
_channel           = postgresql.ENUM("mtn_momo", "orange_money", "visa", "mastercard", "internal",      name="channel_enum",  create_type=False)
_txn_status        = postgresql.ENUM("pending", "processing", "success", "failed", "reversed",          name="txn_status_enum", create_type=False)
_card_status       = postgresql.ENUM("active", "frozen", "expired", "cancelled", name="card_status_enum",     create_type=False)
_doc_type          = postgresql.ENUM("national_id", "passport", "residence_permit", name="doc_type_enum",     create_type=False)
_kyc_doc_status    = postgresql.ENUM("pending", "approved", "rejected",          name="kyc_doc_status_enum",  create_type=False)
_policy_type       = postgresql.ENUM("health", "device", "micro",               name="policy_type_enum",      create_type=False)
_policy_status     = postgresql.ENUM("active", "expired", "cancelled",          name="policy_status_enum",    create_type=False)

_ALL_ENUMS = [
    _kyc_status, _acct_status, _acct_type, _acct_stat,
    _txn_type, _channel, _txn_status, _card_status,
    _doc_type, _kyc_doc_status, _policy_type, _policy_status,
]


def upgrade() -> None:
    bind = op.get_bind()

    # ── Create all ENUM types first (checkfirst=True is safe on re-runs) ──────
    for enum in _ALL_ENUMS:
        enum.create(bind, checkfirst=True)

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: users
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("kyc_status", _kyc_status, nullable=False, server_default="pending"),
        sa.Column("account_status", _acct_status, nullable=False, server_default="active"),
        sa.Column("preferred_language", sa.String(10), server_default="fr"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_users_phone_number", "users", ["phone_number"], unique=True)
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_kyc_status", "users", ["kyc_status"])
    op.create_index("idx_users_account_status", "users", ["account_status"])
    op.create_index("idx_users_kyc_created", "users", ["kyc_status", sa.text("created_at DESC")])

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: accounts
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_type", _acct_type, nullable=False),
        sa.Column("account_number", sa.String(20), nullable=False),
        sa.Column("balance", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("status", _acct_stat, nullable=False, server_default="active"),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("target_amount", sa.BigInteger, nullable=True),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("penalty_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("interest_rate", sa.Numeric(5, 4), nullable=True),
        sa.Column("maturity_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_accounts_user_id", "accounts", ["user_id"])
    op.create_index("idx_accounts_user_type", "accounts", ["user_id", "account_type"])
    op.create_index("idx_accounts_user_status", "accounts", ["user_id", "status"])
    op.create_index("idx_accounts_account_number", "accounts", ["account_number"], unique=True)
    op.create_index(
        "idx_accounts_maturity_date", "accounts", ["maturity_date"],
        postgresql_where=sa.text("account_type = 'term_deposit' AND status = 'active'"),
    )
    op.create_index(
        "idx_accounts_target_date", "accounts", ["target_date"],
        postgresql_where=sa.text("account_type = 'project' AND status = 'active'"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: transactions
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reference", sa.String(50), nullable=False),
        sa.Column("debit_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("credit_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("amount", sa.BigInteger, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="XAF"),
        sa.Column("transaction_type", _txn_type, nullable=False),
        sa.Column("channel", _channel, nullable=False),
        sa.Column("status", _txn_status, nullable=False, server_default="pending"),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("initiated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_transactions_credit_account", "transactions", ["credit_account_id", sa.text("created_at DESC")])
    op.create_index("idx_transactions_debit_account",  "transactions", ["debit_account_id",  sa.text("created_at DESC")])
    op.create_index("idx_transactions_status",         "transactions", ["status"])
    op.create_index("idx_transactions_created_at",     "transactions", [sa.text("created_at DESC")])
    op.create_index("idx_transactions_status_created", "transactions", ["status", sa.text("created_at DESC")])
    op.create_index(
        "idx_transactions_external_ref", "transactions", ["external_reference"],
        postgresql_where=sa.text("external_reference IS NOT NULL"),
    )
    op.create_index(
        "idx_transactions_idempotency", "transactions", ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index("idx_transactions_reference",     "transactions", ["reference"], unique=True)
    op.create_index("idx_transactions_account_time",  "transactions", ["debit_account_id", sa.text("created_at DESC")])
    op.create_index("idx_transactions_channel_status","transactions", ["channel", "status"])
    op.create_index("idx_transactions_type",          "transactions", ["transaction_type"])

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: cards
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("card_token", sa.String(255), nullable=False),
        sa.Column("last_four", sa.String(4), nullable=False),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("status", _card_status, nullable=False, server_default="active"),
        sa.Column("daily_limit", sa.BigInteger, nullable=True),
        sa.Column("per_transaction_limit", sa.BigInteger, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_cards_user_id",    "cards", ["user_id"])
    op.create_index("idx_cards_account_id", "cards", ["account_id"])
    op.create_index("idx_cards_status",     "cards", ["user_id", "status"])
    op.create_index("idx_cards_token",      "cards", ["card_token"], unique=True)

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: kyc_documents
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "kyc_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("document_type", _doc_type, nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("status", _kyc_doc_status, nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_kyc_user_id", "kyc_documents", ["user_id"])
    op.create_index("idx_kyc_status",  "kyc_documents", ["status", sa.text("uploaded_at ASC")])
    op.create_index(
        "idx_kyc_reviewed_by", "kyc_documents", ["reviewed_by"],
        postgresql_where=sa.text("reviewed_by IS NOT NULL"),
    )

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: insurance_policies
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "insurance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.String(100), nullable=False),
        sa.Column("policy_type", _policy_type, nullable=False),
        sa.Column("policy_number", sa.String(255), nullable=False),
        sa.Column("status", _policy_status, nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("expiry_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_insurance_user_id", "insurance_policies", ["user_id"])
    op.create_index(
        "idx_insurance_expiry", "insurance_policies", ["expiry_date"],
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index("idx_insurance_partner", "insurance_policies", ["partner_id"])

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: audit_logs   — IMMUTABLE: no UPDATE / DELETE for API service account
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_audit_actor",      "audit_logs", ["actor_id",    sa.text("created_at DESC")])
    op.create_index("idx_audit_entity",     "audit_logs", ["entity_type", "entity_id", sa.text("created_at DESC")])
    op.create_index("idx_audit_action",     "audit_logs", ["action",      sa.text("created_at DESC")])
    op.create_index("idx_audit_created_at", "audit_logs", [sa.text("created_at DESC")])
    op.create_index("idx_audit_actor_type", "audit_logs", ["actor_type",  sa.text("created_at DESC")])

    # Enforce immutability at the DB layer — no application code can override this.
    op.execute("REVOKE UPDATE, DELETE ON audit_logs FROM terahbank_user;")

    # ──────────────────────────────────────────────────────────────────────────
    # TABLE: system_config
    # ──────────────────────────────────────────────────────────────────────────
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # ── Seed: default financial parameters ────────────────────────────────────
    # System UUID (all zeros) as actor — no real user owns initial seed data.
    op.execute("""
        INSERT INTO system_config (key, value, updated_by, updated_at) VALUES
            ('term_deposit_interest_rate',   '0.0200',   '00000000-0000-0000-0000-000000000000', NOW()),
            ('project_penalty_rate',         '0.0500',   '00000000-0000-0000-0000-000000000000', NOW()),
            ('term_deposit_penalty_rate',    '0.0150',   '00000000-0000-0000-0000-000000000000', NOW()),
            ('standard_min_balance',         '100000',   '00000000-0000-0000-0000-000000000000', NOW()),
            ('standard_min_initial_deposit', '10000',    '00000000-0000-0000-0000-000000000000', NOW()),
            ('term_deposit_min_amount',      '20000000', '00000000-0000-0000-0000-000000000000', NOW()),
            ('max_cards_per_user',           '3',        '00000000-0000-0000-0000-000000000000', NOW()),
            ('otp_expire_minutes',           '5',        '00000000-0000-0000-0000-000000000000', NOW()),
            ('session_inactivity_minutes',   '15',       '00000000-0000-0000-0000-000000000000', NOW()),
            ('max_otp_attempts',             '5',        '00000000-0000-0000-0000-000000000000', NOW()),
            ('otp_lockout_minutes',          '30',       '00000000-0000-0000-0000-000000000000', NOW())
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE ON audit_logs TO terahbank_user;")

    op.drop_table("system_config")
    op.drop_table("audit_logs")
    op.drop_table("insurance_policies")
    op.drop_table("kyc_documents")
    op.drop_table("cards")
    op.drop_table("transactions")
    op.drop_table("accounts")
    op.drop_table("users")

    bind = op.get_bind()
    for enum in reversed(_ALL_ENUMS):
        enum.drop(bind, checkfirst=True)
