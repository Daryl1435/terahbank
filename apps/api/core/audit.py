from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


async def write_audit_log(
    db: AsyncSession,
    actor_id: UUID,
    action: str,
    actor_type: str = "user",
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Write an immutable audit log entry.
    MUST be called before returning from any mutation endpoint.
    The audit_logs table has no UPDATE or DELETE privileges for the API service account.

    Action code standards:
      Auth:        LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, OTP_REQUESTED, OTP_VERIFIED, DEVICE_REGISTERED
      Account:     ACCOUNT_OPENED, ACCOUNT_CLOSED, BALANCE_UPDATED
      Transaction: TRANSFER_INITIATED, DEPOSIT_SUCCESS, WITHDRAWAL_FAILED
      Admin:       KYC_APPROVED, KYC_REJECTED, CONFIG_UPDATED, USER_SUSPENDED
    """
    from modules.admin.models import AuditLog

    log = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_=metadata,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    await db.flush()
