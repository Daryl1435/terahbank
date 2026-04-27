# Card issuance and management via VISA card-issuing partner API.
# PCI-DSS: raw PAN/CVV never stored or transmitted by this service.
# Only card_token (opaque) + last_four + expiry_date stored in DB.
# Freeze/unfreeze: local DB status update + best-effort partner API notification.

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.config import settings
from core.schemas import TerahResponse
from core.visa_gateway import VisaGatewayClient
from modules.accounts.repository import AccountRepository

from .models import Card
from .repository import CardRepository
from .schemas import CardData, CardListResponse, IssueCardResponse

logger = logging.getLogger("terahbank.cards")


def _card_data(card: Card) -> CardData:
    return CardData(
        card_id=str(card.id),
        account_id=str(card.account_id),
        last_four=card.last_four,
        expiry_date=str(card.expiry_date),
        status=card.status,
        daily_limit=card.daily_limit,
        per_transaction_limit=card.per_transaction_limit,
        created_at=card.created_at,
    )


class CardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = CardRepository(db)

    # ── FR-029: Issue virtual VISA card ───────────────────────────────────────

    async def issue_card(self, user, payload) -> TerahResponse:
        """
        FR-029: Issue a new virtual VISA prepaid card linked to a Standard Account.
        FR-033: Max cards per user enforced (admin-configurable VISA_MAX_CARDS_PER_USER).
        PCI-DSS: Raw PAN/CVV never stored. Only card_token + last_four + expiry_date.
        """
        if not settings.FEATURE_VIRTUAL_CARD:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": "FEATURE_DISABLED", "message": "Virtual card issuance is currently disabled."},
            )

        # 1. Validate target account belongs to user and is a Standard Account
        acct_repo = AccountRepository(self.db)
        try:
            acct_uuid = UUID(payload.account_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ACCOUNT_ID", "message": "Invalid account_id format."},
            )

        account = await acct_repo.get_user_account(acct_uuid, user.id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found or not owned by you."},
            )
        if account.account_type != "standard":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_ACCOUNT_TYPE", "message": "Virtual cards can only be linked to Standard Savings Accounts."},
            )
        if account.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "ACCOUNT_LOCKED", "message": f"Account is {account.status}."},
            )

        # 2. Enforce card limit (FR-033)
        active_count = await self._repo.count_active_by_user(user.id)
        if active_count >= settings.VISA_MAX_CARDS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "CARD_LIMIT_REACHED",
                    "message": f"Maximum {settings.VISA_MAX_CARDS_PER_USER} virtual cards allowed per account.",
                },
            )

        # 3. Call VISA partner — returns card_token, last_four, expiry_date
        gateway = VisaGatewayClient()
        try:
            card_info = await gateway.issue_virtual_card(
                user_id=str(user.id),
                account_id=str(account.id),
                phone_e164=user.phone,
                full_name=user.full_name,
            )
        except Exception as exc:
            logger.error("Card issuance failed: user=%s error=%s", user.id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"code": "CARD_ISSUANCE_FAILED", "message": "Card issuance temporarily unavailable. Please try again."},
            )

        # 4. Create Card record — only token + last_four + expiry stored
        from datetime import date as _date
        raw_expiry = card_info["expiry_date"]
        if len(raw_expiry) == 7:  # YYYY-MM format → add day 01
            raw_expiry = f"{raw_expiry}-01"
        expiry_date = _date.fromisoformat(raw_expiry)

        card = Card(
            user_id=user.id,
            account_id=account.id,
            card_token=card_info["card_token"],
            last_four=card_info["last_four"],
            expiry_date=expiry_date,
            status="active",
            created_at=datetime.now(tz=timezone.utc),
        )
        card = await self._repo.create(card)

        # 5. Audit log + commit
        await write_audit_log(
            self.db,
            actor_id=user.id,
            action="CARD_ISSUED",
            entity_type="card",
            entity_id=card.id,
            metadata={
                "account_id": str(account.id),
                "last_four": card.last_four,
                "expiry_date": str(expiry_date),
            },
        )
        await self.db.commit()

        logger.info("Card issued: user=%s last_four=%s", user.id, card.last_four)

        return TerahResponse(
            success=True,
            data=IssueCardResponse(
                card_id=str(card.id),
                account_id=str(card.account_id),
                last_four=card.last_four,
                expiry_date=str(card.expiry_date),
                status=card.status,
                created_at=card.created_at,
            ).model_dump(mode="json"),
            message="Virtual card issued successfully.",
        )

    # ── FR-029: List cards ────────────────────────────────────────────────────

    async def list_cards(self, user_id) -> TerahResponse:
        cards = await self._repo.list_by_user(user_id)
        return TerahResponse(
            success=True,
            data=CardListResponse(
                cards=[_card_data(c) for c in cards],
                total=len(cards),
            ).model_dump(mode="json"),
        )

    # ── FR-030: Freeze card ───────────────────────────────────────────────────

    async def freeze(self, card_id: str, user_id) -> TerahResponse:
        """FR-030: Freeze card instantly — local DB update + best-effort partner notification."""
        card = await self._get_card_or_404(card_id, user_id)

        if card.status == "frozen":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "CARD_ALREADY_FROZEN", "message": "Card is already frozen."},
            )
        if card.status in ("expired", "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "CARD_INACTIVE", "message": f"Card is {card.status} and cannot be frozen."},
            )

        card = await self._repo.update(card, status="frozen")
        await write_audit_log(
            self.db, actor_id=user_id, action="CARD_FROZEN",
            entity_type="card", entity_id=card.id,
            metadata={"last_four": card.last_four},
        )
        await self.db.commit()

        # Best-effort partner notification (don't raise if it fails)
        gateway = VisaGatewayClient()
        await gateway.update_card_status(card.card_token, "freeze")

        return TerahResponse(success=True, data=_card_data(card).model_dump(mode="json"), message="Card frozen.")

    # ── FR-030: Unfreeze card ─────────────────────────────────────────────────

    async def unfreeze(self, card_id: str, user_id) -> TerahResponse:
        """FR-030: Unfreeze card instantly."""
        card = await self._get_card_or_404(card_id, user_id)

        if card.status != "frozen":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "CARD_NOT_FROZEN", "message": "Card is not frozen."},
            )

        card = await self._repo.update(card, status="active")
        await write_audit_log(
            self.db, actor_id=user_id, action="CARD_UNFROZEN",
            entity_type="card", entity_id=card.id,
            metadata={"last_four": card.last_four},
        )
        await self.db.commit()

        gateway = VisaGatewayClient()
        await gateway.update_card_status(card.card_token, "unfreeze")

        return TerahResponse(success=True, data=_card_data(card).model_dump(mode="json"), message="Card unfrozen.")

    # ── FR-031: Update spending limits ────────────────────────────────────────

    async def update_limits(self, card_id: str, user_id, payload) -> TerahResponse:
        """FR-031: Update per-transaction and daily spending limits."""
        card = await self._get_card_or_404(card_id, user_id)

        if card.status in ("expired", "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "CARD_INACTIVE", "message": f"Card is {card.status}."},
            )

        updates: dict = {}
        if payload.daily_limit is not None:
            updates["daily_limit"] = payload.daily_limit
        if payload.per_transaction_limit is not None:
            updates["per_transaction_limit"] = payload.per_transaction_limit

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "NO_CHANGES", "message": "No limit values provided."},
            )

        card = await self._repo.update(card, **updates)
        await write_audit_log(
            self.db, actor_id=user_id, action="CARD_LIMITS_UPDATED",
            entity_type="card", entity_id=card.id,
            metadata={
                "last_four": card.last_four,
                "daily_limit": card.daily_limit,
                "per_transaction_limit": card.per_transaction_limit,
            },
        )
        await self.db.commit()

        return TerahResponse(success=True, data=_card_data(card).model_dump(mode="json"), message="Limits updated.")

    # ── FR-032: Card transaction history ─────────────────────────────────────

    async def get_transactions(self, card_id: str, user_id) -> TerahResponse:
        """FR-032: Paginated card transaction history — filtered from transactions table by card channel."""
        card = await self._get_card_or_404(card_id, user_id)

        # Transactions linked to this card's account with visa/mastercard channel
        from modules.transactions.repository import TransactionRepository
        from modules.transactions.service import _build_txn_data
        txn_repo = TransactionRepository(self.db)

        rows, total = await txn_repo.list_by_user(
            user_id=user_id,
            account_id=card.account_id,
            transaction_type=None,
            txn_status=None,
            date_from=None,
            date_to=None,
            limit=50,
            offset=0,
        )
        # Filter to card channels only
        card_txns = [t for t in rows if t.channel in ("visa", "mastercard")]

        from modules.transactions.schemas import ListTransactionsResponseData
        return TerahResponse(
            success=True,
            data=ListTransactionsResponseData(
                transactions=[_build_txn_data(t) for t in card_txns],
                total=len(card_txns),
                limit=50,
                offset=0,
            ).model_dump(mode="json"),
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _get_card_or_404(self, card_id: str, user_id) -> Card:
        try:
            card_uuid = UUID(card_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_CARD_ID", "message": "Invalid card ID format."},
            )
        card = await self._repo.get_by_id(card_uuid, user_id)
        if card is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "CARD_NOT_FOUND", "message": "Card not found."},
            )
        return card

    # ── Webhook: VISA card transaction notification ───────────────────────────

    async def handle_visa_deposit_webhook(self, our_reference: str, payload: dict) -> None:
        """
        Process inbound VISA gateway callback for a card deposit.
        Looks up the pending transaction by external_reference (our TXN reference).
        On SUCCESSFUL: credits account, marks txn success.
        On FAILED: marks txn failed.
        Duplicate callbacks silently ignored.
        CRITICAL: never raises — caller always returns HTTP 200.
        """
        from modules.transactions.repository import TransactionRepository
        from modules.accounts.service import AccountService

        raw_status = payload.get("status", "").upper()
        if raw_status in ("SUCCESSFUL", "SUCCESS", "APPROVED"):
            gateway_status = "SUCCESSFUL"
        elif raw_status in ("PENDING", "PROCESSING"):
            gateway_status = "PENDING"
        else:
            gateway_status = "FAILED"

        txn_repo = TransactionRepository(self.db)
        txn = await txn_repo.get_by_external_reference(our_reference)
        if txn is None:
            logger.warning("VISA webhook: no txn for reference=%s", our_reference)
            return

        if txn.status in ("success", "failed", "reversed"):
            logger.info("VISA webhook: duplicate ignored txn_id=%s status=%s", txn.id, txn.status)
            return

        now = datetime.now(tz=timezone.utc)

        if gateway_status == "SUCCESSFUL":
            acct_service = AccountService(self.db)
            await acct_service.apply_balance_delta(txn.credit_account_id, txn.amount)
            await txn_repo.update(txn, status="success", completed_at=now)
            await write_audit_log(
                self.db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_SUCCESS",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": txn.channel,
                    "amount": txn.amount,
                    "reference": our_reference,
                    "card_token": payload.get("cardToken"),
                    "last_four": payload.get("lastFour"),
                },
            )
            await self.db.commit()
            logger.info("VISA webhook: deposit success txn_id=%s amount=%d", txn.id, txn.amount)

        elif gateway_status == "FAILED":
            await txn_repo.update(txn, status="failed", completed_at=now)
            await write_audit_log(
                self.db,
                actor_id=txn.initiated_by,
                action="DEPOSIT_FAILED",
                entity_type="transaction",
                entity_id=txn.id,
                metadata={
                    "channel": txn.channel,
                    "amount": txn.amount,
                    "reference": our_reference,
                    "reason": payload.get("failureReason"),
                },
            )
            await self.db.commit()
            # TODO Milestone 6.2: push/SMS notification (FR-040)
            logger.info("VISA webhook: deposit failed txn_id=%s", txn.id)

        else:
            logger.info("VISA webhook: status=%s reference=%s — no action", gateway_status, our_reference)
