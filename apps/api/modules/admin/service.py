# User management, KYC queue, system config, reporting, RBAC enforcement.
# Config PATCH: super_admin only. Validate → audit log → update DB → invalidate Redis config cache.
# User suspend: audit log → set status=suspended → invalidate all user sessions in Redis.
# KYC approve: audit log → set kyc_status=approved → notify user.
# Reports: always query read replica (DATABASE_URL_READ). Never primary DB for reports.

import csv
import io
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.schemas import TerahResponse
from core.security import verify_password

from modules.notifications.service import dispatch_kyc_approved, dispatch_kyc_rejected

from .repository import AdminRepository
from .schemas import (
    AdminTokenResponse,
    AdminTransactionItem,
    AdminTransactionListResponseData,
    AdminUserDetail,
    AdminUserItem,
    AdminUserListResponseData,
    ConfigItem,
    ConfigListResponseData,
    FraudAlertItem,
    FraudAlertListResponseData,
    KYCDecisionRequest,
    KYCDecisionResponseData,
    KYCQueueItem,
    KYCQueueResponseData,
    ReportResponseData,
    UpdateConfigRequest,
    UpdateUserStatusRequest,
)

logger = logging.getLogger("terahbank.admin")

# Sentinel UUID for system-generated audit log entries
_SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

# Fraud rule thresholds (XAF as BIGINT units)
_FRAUD_LARGE_TXN_THRESHOLD = 1_000_000       # 1,000,000 XAF
_FRAUD_VELOCITY_WINDOW_MINUTES = 10
_FRAUD_VELOCITY_MAX_TXNS = 10
_FRAUD_NEW_DEVICE_WITHDRAWAL_THRESHOLD = 500_000   # 500,000 XAF
_FRAUD_NEW_ACCOUNT_AGE_HOURS = 24


def _get_actor_id(admin) -> UUID:
    if admin is not None and hasattr(admin, "id"):
        return admin.id
    return _SYSTEM_ACTOR_ID


def _create_admin_access_token(admin_id: str | UUID, role: str) -> str:
    """Issue a 12-hour RS256 JWT for admin sessions. type=admin_access."""
    import core.security as _sec
    from jose import jwt
    from core.config import settings

    _sec._ensure_keys_loaded()
    now = datetime.utcnow()
    payload = {
        "sub": str(admin_id),
        "jti": secrets.token_urlsafe(32),
        "type": "admin_access",
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=12),
    }
    return jwt.encode(payload, _sec._private_key, algorithm=settings.JWT_ALGORITHM)


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = AdminRepository(db)

    # ── Admin auth ────────────────────────────────────────────────────────────

    async def admin_login(self, email: str, password: str) -> TerahResponse:
        """Authenticate admin user, issue admin JWT."""
        admin = await self._repo.get_admin_by_email(email)
        if admin is None or not verify_password(password, admin.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."},
            )

        if not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCOUNT_INACTIVE", "message": "Admin account is inactive."},
            )

        token = _create_admin_access_token(admin.id, admin.role)

        await self._repo.update_admin(admin, last_login_at=datetime.utcnow())
        await write_audit_log(
            self.db,
            actor_id=admin.id,
            actor_type="admin",
            action="ADMIN_LOGIN_SUCCESS",
            entity_type="admin_user",
            entity_id=admin.id,
            metadata={"role": admin.role},
        )

        return TerahResponse(
            success=True,
            data=AdminTokenResponse(
                access_token=token,
                role=admin.role,
            ).model_dump(),
        )

    # ── KYC queue ─────────────────────────────────────────────────────────────

    async def get_kyc_queue(self, offset: int = 0, limit: int = 20) -> TerahResponse:
        """Return paginated list of pending KYC documents with user details."""
        rows, total = await self._repo.get_kyc_queue(offset=offset, limit=limit)
        items = [
            KYCQueueItem(
                document_id=str(doc.id),
                user_id=str(user.id),
                full_name=user.full_name,
                email=user.email,
                phone_number=user.phone_number,
                document_type=doc.document_type,
                uploaded_at=doc.uploaded_at,
            )
            for doc, user in rows
        ]
        return TerahResponse(
            success=True,
            data=KYCQueueResponseData(
                items=items,
                total=total,
                offset=offset,
                limit=limit,
            ).model_dump(mode="json"),
        )

    async def make_kyc_decision(
        self,
        user_id: str,
        payload: KYCDecisionRequest,
        admin=None,
    ) -> TerahResponse:
        """
        Approve or reject a user's KYC document.
        - Updates KYCDocument.status
        - Updates User.kyc_status
        - Writes audit log with KYC_APPROVED or KYC_REJECTED
        - Dispatches user notification (stub — BullMQ in Milestone 6.2)
        """
        try:
            uid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_USER_ID", "message": "Invalid user ID format."},
            )

        if payload.decision == "rejected" and not payload.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "REJECTION_REASON_REQUIRED",
                    "message": "A rejection_reason is required when rejecting a KYC document.",
                },
            )

        user = await self._repo.get_user_by_id(uid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        doc = await self._repo.get_latest_pending_document(uid)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "NO_PENDING_DOCUMENT",
                    "message": "No pending KYC document found for this user.",
                },
            )

        now = datetime.utcnow()
        doc_update: dict = {"status": payload.decision, "reviewed_at": now}
        if payload.rejection_reason:
            doc_update["rejection_reason"] = payload.rejection_reason
        await self._repo.update_document(doc, **doc_update)
        await self._repo.update_user(user, kyc_status=payload.decision)

        actor_id = _get_actor_id(admin)
        action = "KYC_APPROVED" if payload.decision == "approved" else "KYC_REJECTED"
        await write_audit_log(
            self.db,
            actor_id=actor_id,
            actor_type="admin",
            action=action,
            entity_type="user",
            entity_id=user.id,
            metadata={
                "decision": payload.decision,
                "document_id": str(doc.id),
                "rejection_reason": payload.rejection_reason,
            },
        )

        if payload.decision == "approved":
            await dispatch_kyc_approved(self.db, user)
        else:
            await dispatch_kyc_rejected(self.db, user, payload.rejection_reason or "")
        logger.info("KYC decision: user=%s decision=%s doc=%s actor=%s", user_id, payload.decision, doc.id, actor_id)

        return TerahResponse(
            success=True,
            data=KYCDecisionResponseData(
                user_id=user_id,
                kyc_status=payload.decision,
                document_id=str(doc.id),
            ).model_dump(),
            message=f"KYC {payload.decision} for user {user_id}.",
        )

    # ── User management ───────────────────────────────────────────────────────

    async def list_users(
        self,
        search: str | None = None,
        kyc_status: str | None = None,
        account_status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> TerahResponse:
        """FR-051: Paginated, searchable user list."""
        users, total = await self._repo.list_users(
            search=search,
            kyc_status=kyc_status,
            account_status=account_status,
            offset=offset,
            limit=limit,
        )
        items = [
            AdminUserItem(
                user_id=str(u.id),
                full_name=u.full_name,
                email=u.email,
                phone_number=u.phone_number,
                kyc_status=u.kyc_status,
                account_status=u.account_status,
                preferred_language=u.preferred_language,
                created_at=u.created_at,
            )
            for u in users
        ]
        return TerahResponse(
            success=True,
            data=AdminUserListResponseData(
                users=items,
                total=total,
                offset=offset,
                limit=limit,
            ).model_dump(mode="json"),
        )

    async def get_user(self, user_id: str) -> TerahResponse:
        """FR-051: User detail view with accounts summary."""
        try:
            uid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_USER_ID", "message": "Invalid user ID format."},
            )

        user = await self._repo.get_user_by_id(uid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        accounts = await self._repo.get_user_accounts(uid)
        accounts_data = [
            {
                "account_id": str(a.id),
                "account_type": a.account_type,
                "account_number": a.account_number,
                "balance": a.balance,
                "status": a.status,
            }
            for a in accounts
        ]

        return TerahResponse(
            success=True,
            data=AdminUserDetail(
                user_id=str(user.id),
                full_name=user.full_name,
                email=user.email,
                phone_number=user.phone_number,
                kyc_status=user.kyc_status,
                account_status=user.account_status,
                preferred_language=user.preferred_language,
                created_at=user.created_at,
                accounts=accounts_data,
            ).model_dump(mode="json"),
        )

    async def update_user_status(
        self,
        user_id: str,
        payload: UpdateUserStatusRequest,
        admin=None,
    ) -> TerahResponse:
        """Suspend, close, or reactivate a user account."""
        try:
            uid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_USER_ID", "message": "Invalid user ID format."},
            )

        user = await self._repo.get_user_by_id(uid)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "USER_NOT_FOUND", "message": "User not found."},
            )

        await self._repo.update_user(user, account_status=payload.status)

        action_map = {
            "active": "ACCOUNT_REOPENED",
            "suspended": "USER_SUSPENDED",
            "closed": "ACCOUNT_CLOSED",
        }
        actor_id = _get_actor_id(admin)
        await write_audit_log(
            self.db,
            actor_id=actor_id,
            actor_type="admin",
            action=action_map[payload.status],
            entity_type="user",
            entity_id=user.id,
            metadata={"new_status": payload.status},
        )

        # TODO (Milestone 6.2): notify user of account status change
        logger.info("User status updated: user=%s status=%s actor=%s", user_id, payload.status, actor_id)

        return TerahResponse(
            success=True,
            data={"user_id": user_id, "account_status": payload.status},
            message=f"User account status updated to {payload.status}.",
        )

    # ── Transactions ──────────────────────────────────────────────────────────

    async def list_transactions(
        self,
        user_id: str | None = None,
        transaction_type: str | None = None,
        channel: str | None = None,
        txn_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> TerahResponse:
        """FR-053: Full-filter paginated transaction list for admin monitoring."""
        uid: UUID | None = None
        if user_id:
            try:
                uid = UUID(user_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "INVALID_USER_ID", "message": "Invalid user_id format."},
                )

        txns, total = await self._repo.list_transactions(
            user_id=uid,
            transaction_type=transaction_type,
            channel=channel,
            txn_status=txn_status,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=limit,
        )

        items = [
            AdminTransactionItem(
                transaction_id=str(t.id),
                reference=t.reference,
                user_id=str(t.initiated_by),
                transaction_type=t.transaction_type,
                channel=t.channel,
                amount=t.amount,
                currency=t.currency,
                status=t.status,
                debit_account_id=str(t.debit_account_id) if t.debit_account_id else None,
                credit_account_id=str(t.credit_account_id) if t.credit_account_id else None,
                external_reference=t.external_reference,
                created_at=t.created_at,
                completed_at=t.completed_at,
            )
            for t in txns
        ]

        return TerahResponse(
            success=True,
            data=AdminTransactionListResponseData(
                transactions=items,
                total=total,
                offset=offset,
                limit=limit,
            ).model_dump(mode="json"),
        )

    # ── System config ─────────────────────────────────────────────────────────

    async def get_config(self) -> TerahResponse:
        """FR-054: Return all system configuration keys."""
        configs = await self._repo.get_all_config()
        items = [
            ConfigItem(key=c.key, value=c.value, updated_at=c.updated_at)
            for c in configs
        ]
        return TerahResponse(
            success=True,
            data=ConfigListResponseData(config=items).model_dump(mode="json"),
        )

    async def update_config(self, payload: UpdateConfigRequest, admin=None) -> TerahResponse:
        """FR-054: Upsert config key — super_admin only (enforced by router dep)."""
        actor_id = _get_actor_id(admin)
        cfg = await self._repo.upsert_config(
            key=payload.key,
            value=payload.value,
            updated_by=actor_id,
        )

        # Invalidate Redis config cache so live services pick up the change
        try:
            from core.redis import get_redis_client
            rc = get_redis_client()
            await rc.delete(f"config:{payload.key}")
            await rc.delete("config:all")
        except Exception:
            logger.warning("Failed to invalidate Redis config cache for key=%s", payload.key)

        await write_audit_log(
            self.db,
            actor_id=actor_id,
            actor_type="admin",
            action="CONFIG_UPDATED",
            entity_type="system_config",
            entity_id=None,
            metadata={"key": payload.key, "new_value": payload.value},
        )

        return TerahResponse(
            success=True,
            data=ConfigItem(
                key=cfg.key,
                value=cfg.value,
                updated_at=cfg.updated_at,
            ).model_dump(mode="json"),
            message=f"Config key '{payload.key}' updated.",
        )

    # ── Fraud alerts ──────────────────────────────────────────────────────────

    async def get_fraud_alerts(self, offset: int = 0, limit: int = 50) -> TerahResponse:
        """Return paginated fraud alert audit log entries."""
        alerts, total = await self._repo.get_fraud_alerts(offset=offset, limit=limit)
        items = [
            FraudAlertItem(
                alert_id=str(a.id),
                rule=a.action.replace("FRAUD_ALERT_", ""),
                actor_id=str(a.actor_id),
                entity_type=a.entity_type or "",
                entity_id=str(a.entity_id) if a.entity_id else None,
                metadata=a.metadata_ or {},
                created_at=a.created_at,
            )
            for a in alerts
        ]
        return TerahResponse(
            success=True,
            data=FraudAlertListResponseData(
                alerts=items,
                total=total,
                offset=offset,
                limit=limit,
            ).model_dump(mode="json"),
        )

    # ── Fraud detection rules engine ──────────────────────────────────────────

    async def check_fraud_rules(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        amount: int,
        transaction_type: str,
        channel: str,
        credit_account_id: UUID | None,
        is_new_device: bool = False,
    ) -> None:
        """
        Phase-1 fraud rules engine. Evaluates 4 rules after a transaction is committed.
        Writes FRAUD_ALERT_* audit log entries for any triggered rule.
        Never raises — fraud alerts are non-blocking (fire-and-log only).
        """
        try:
            await self._run_fraud_rules(
                user_id=user_id,
                transaction_id=transaction_id,
                amount=amount,
                transaction_type=transaction_type,
                channel=channel,
                credit_account_id=credit_account_id,
                is_new_device=is_new_device,
            )
        except Exception:
            logger.exception("Fraud rule check failed for txn=%s", transaction_id)

    async def _run_fraud_rules(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        amount: int,
        transaction_type: str,
        channel: str,
        credit_account_id: UUID | None,
        is_new_device: bool,
    ) -> None:
        base_meta: dict = {
            "transaction_id": str(transaction_id),
            "amount": amount,
            "transaction_type": transaction_type,
            "channel": channel,
        }

        # Rule 1: LARGE_TRANSACTION — single txn > 1,000,000 XAF
        if amount > _FRAUD_LARGE_TXN_THRESHOLD:
            await write_audit_log(
                self.db,
                actor_id=user_id,
                actor_type="system",
                action="FRAUD_ALERT_LARGE_TRANSACTION",
                entity_type="transaction",
                entity_id=transaction_id,
                metadata={**base_meta, "threshold": _FRAUD_LARGE_TXN_THRESHOLD},
            )
            logger.warning("FRAUD_ALERT_LARGE_TRANSACTION: user=%s txn=%s amount=%d", user_id, transaction_id, amount)

        # Rule 2: VELOCITY_BREACH — 10+ transactions within 10 minutes
        since = datetime.utcnow() - timedelta(minutes=_FRAUD_VELOCITY_WINDOW_MINUTES)
        recent_count = await self._repo.count_recent_transactions(user_id, since)
        if recent_count >= _FRAUD_VELOCITY_MAX_TXNS:
            await write_audit_log(
                self.db,
                actor_id=user_id,
                actor_type="system",
                action="FRAUD_ALERT_VELOCITY_BREACH",
                entity_type="transaction",
                entity_id=transaction_id,
                metadata={
                    **base_meta,
                    "txn_count_in_window": recent_count,
                    "window_minutes": _FRAUD_VELOCITY_WINDOW_MINUTES,
                },
            )
            logger.warning("FRAUD_ALERT_VELOCITY_BREACH: user=%s count=%d", user_id, recent_count)

        # Rule 3: NEW_DEVICE_LARGE_WITHDRAWAL — unrecognized device + large withdrawal
        if (
            is_new_device
            and transaction_type in ("withdrawal", "transfer")
            and amount > _FRAUD_NEW_DEVICE_WITHDRAWAL_THRESHOLD
        ):
            await write_audit_log(
                self.db,
                actor_id=user_id,
                actor_type="system",
                action="FRAUD_ALERT_NEW_DEVICE_LARGE_WITHDRAWAL",
                entity_type="transaction",
                entity_id=transaction_id,
                metadata={**base_meta, "threshold": _FRAUD_NEW_DEVICE_WITHDRAWAL_THRESHOLD},
            )
            logger.warning("FRAUD_ALERT_NEW_DEVICE_LARGE_WITHDRAWAL: user=%s txn=%s", user_id, transaction_id)

        # Rule 4: NEW_ACCOUNT_RECIPIENT — recipient account created < 24h ago
        if credit_account_id is not None:
            age_days = await self._repo.get_account_age_days(credit_account_id)
            if age_days is not None and age_days < 1:
                await write_audit_log(
                    self.db,
                    actor_id=user_id,
                    actor_type="system",
                    action="FRAUD_ALERT_NEW_ACCOUNT_RECIPIENT",
                    entity_type="transaction",
                    entity_id=transaction_id,
                    metadata={
                        **base_meta,
                        "recipient_account_id": str(credit_account_id),
                        "account_age_days": age_days,
                    },
                )
                logger.warning("FRAUD_ALERT_NEW_ACCOUNT_RECIPIENT: user=%s recipient_account=%s", user_id, credit_account_id)

    # ── Reports (FR-055) ──────────────────────────────────────────────────────

    async def export_transactions_csv(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> StreamingResponse:
        """FR-055: Export all transactions as CSV download."""
        txns, total = await self._repo.list_transactions(
            date_from=date_from,
            date_to=date_to,
            offset=0,
            limit=100_000,  # Cap at 100k rows per export
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "transaction_id", "reference", "user_id", "transaction_type",
            "channel", "amount_xaf", "currency", "status",
            "debit_account_id", "credit_account_id", "external_reference",
            "created_at", "completed_at",
        ])
        for t in txns:
            writer.writerow([
                str(t.id), t.reference, str(t.initiated_by), t.transaction_type,
                t.channel, t.amount, t.currency, t.status,
                str(t.debit_account_id) if t.debit_account_id else "",
                str(t.credit_account_id) if t.credit_account_id else "",
                t.external_reference or "",
                t.created_at.isoformat(), t.completed_at.isoformat() if t.completed_at else "",
            ])

        output.seek(0)
        filename = f"transactions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    async def export_commissions_csv(self) -> StreamingResponse:
        """FR-055: Export insurance commission data as CSV download."""
        policies, _total = await self._repo.list_insurance_policies(offset=0, limit=100_000)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "policy_id", "user_id", "partner_id", "policy_type", "product_name",
            "policy_number", "status", "start_date", "expiry_date",
            "commission_amount_xaf", "created_at",
        ])
        for p in policies:
            writer.writerow([
                str(p.id), str(p.user_id), p.partner_id, p.policy_type, p.product_name,
                p.policy_number, p.status,
                p.start_date.isoformat(), p.expiry_date.isoformat(),
                p.commission_amount, p.created_at.isoformat(),
            ])

        output.seek(0)
        filename = f"insurance_commissions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    async def export_users_csv(self) -> StreamingResponse:
        """FR-055: Export all users as CSV download."""
        users, _total = await self._repo.list_users(offset=0, limit=100_000)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "user_id", "full_name", "email", "phone_number",
            "kyc_status", "account_status", "preferred_language", "created_at",
        ])
        for u in users:
            writer.writerow([
                str(u.id), u.full_name, u.email, u.phone_number,
                u.kyc_status, u.account_status, u.preferred_language,
                u.created_at.isoformat(),
            ])

        output.seek(0)
        filename = f"users_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
