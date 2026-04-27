"""
Inbound webhooks from payment providers.

MTN MoMo callback:
  POST /api/v1/webhooks/mtn-momo
  Headers: X-Reference-Id (UUID we generated), X-Signature (HMAC-SHA256)
  Body: JSON with status field (SUCCESSFUL | FAILED | PENDING)

Orange Money callback:
  POST /api/v1/webhooks/orange-money
  Headers: X-Orange-Signature (HMAC-SHA256), X-Order-Id (our TXN reference)
  Body: JSON with status field (SUCCESSFUL | FAILED | PENDING | CANCELLED | EXPIRED)

Security contract:
  - HMAC-SHA256 validated before any processing.
  - ALWAYS return HTTP 200 to providers, even on signature failure.
    Returning 4xx/5xx causes the provider to retry indefinitely.
  - Duplicate callbacks are silently discarded (idempotent in TransactionService).

CRITICAL: These endpoints are called by payment providers — no JWT auth.
"""

import json
import logging

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.mtn_momo import validate_mtn_callback_signature
from core.orange_money import validate_orange_callback_signature
from core.visa_gateway import validate_visa_webhook_signature

from modules.transactions.service import TransactionService
from modules.cards.service import CardService

logger = logging.getLogger("terahbank.webhooks")

router = APIRouter()


@router.post("/mtn-momo", status_code=200)
async def mtn_momo_webhook(
    request: Request,
    x_reference_id: str = Header(None, alias="X-Reference-Id", description="The UUID we sent as X-Reference-Id in the requesttopay call"),
    x_signature: str = Header(None, alias="X-Signature", description="HMAC-SHA256 of the raw request body"),
    db: AsyncSession = Depends(get_db),
):
    """
    MTN MoMo payment callback (UC-003).
    Always returns 200 — never 4xx/5xx (prevents MTN retry storm).
    Signature failure: logged and discarded silently.
    Duplicate callbacks: silently ignored (idempotent state machine).
    """
    body = await request.body()

    # 1. HMAC validation — constant-time comparison
    if not validate_mtn_callback_signature(body, x_signature or "", settings.MTN_MOMO_WEBHOOK_SECRET):
        logger.warning(
            "MTN webhook: invalid signature x_ref=%s — discarding (returning 200 to suppress retries)",
            x_reference_id,
        )
        return {"received": True}

    # 2. Parse body
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("MTN webhook: invalid JSON body x_ref=%s", x_reference_id)
        return {"received": True}

    # 3. X-Reference-Id is required for transaction lookup
    if not x_reference_id:
        logger.warning("MTN webhook: missing X-Reference-Id header")
        return {"received": True}

    # 4. Delegate to TransactionService state machine
    try:
        await TransactionService(db).handle_mtn_webhook(x_reference_id, payload)
    except Exception:
        # Never let an unhandled exception propagate — MTN would retry endlessly
        logger.exception("MTN webhook: unhandled error x_ref=%s", x_reference_id)

    return {"received": True}


@router.post("/orange-money", status_code=200)
async def orange_money_webhook(
    request: Request,
    x_order_id: str = Header(None, alias="X-Order-Id", description="Our TXN reference (order.id we sent in the pay request)"),
    x_signature: str = Header(None, alias="X-Orange-Signature", description="HMAC-SHA256 of the raw request body"),
    db: AsyncSession = Depends(get_db),
):
    """
    Orange Money payment callback (deposit + withdrawal).
    Always returns 200 — never 4xx/5xx (prevents Orange Money retry storm).
    Signature failure: logged and discarded silently.
    Duplicate callbacks: silently ignored (idempotent state machine).
    """
    body = await request.body()

    # 1. HMAC validation
    if not validate_orange_callback_signature(body, x_signature or "", settings.ORANGE_MONEY_WEBHOOK_SECRET):
        logger.warning(
            "Orange webhook: invalid signature order_id=%s — discarding (returning 200 to suppress retries)",
            x_order_id,
        )
        return {"received": True}

    # 2. Parse body
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Orange webhook: invalid JSON body order_id=%s", x_order_id)
        return {"received": True}

    # 3. Resolve order_id — prefer header, fall back to payload field
    order_id = x_order_id or payload.get("order_id") or payload.get("data", {}).get("order_id")
    if not order_id:
        logger.warning("Orange webhook: missing order_id")
        return {"received": True}

    # 4. Delegate to TransactionService state machine
    try:
        await TransactionService(db).handle_orange_webhook(order_id, payload)
    except Exception:
        logger.exception("Orange webhook: unhandled error order_id=%s", order_id)

    return {"received": True}


@router.post("/visa-card", status_code=200)
async def visa_card_webhook(
    request: Request,
    x_visa_signature: str = Header(None, alias="X-Visa-Signature", description="HMAC-SHA256 of the raw request body"),
    db: AsyncSession = Depends(get_db),
):
    """
    VISA card-issuing partner callback (deposit completion + card status events).
    Always returns 200 — never 4xx/5xx (prevents partner retry storm).
    Signature failure: logged and discarded silently.
    Duplicate callbacks: silently ignored (idempotent state machine in CardService).
    """
    body = await request.body()

    # 1. HMAC validation — constant-time comparison
    if not validate_visa_webhook_signature(body, x_visa_signature or "", settings.VISA_GATEWAY_WEBHOOK_SECRET):
        logger.warning("VISA webhook: invalid signature — discarding (returning 200 to suppress retries)")
        return {"received": True}

    # 2. Parse body
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("VISA webhook: invalid JSON body")
        return {"received": True}

    # 3. Resolve our_reference — the TXN reference we sent in createPaymentSession
    our_reference = (
        payload.get("reference")
        or payload.get("order_id")
        or payload.get("externalReference")
    )
    if not our_reference:
        logger.warning("VISA webhook: missing reference field in payload")
        return {"received": True}

    # 4. Delegate to CardService state machine
    try:
        await CardService(db).handle_visa_deposit_webhook(our_reference, payload)
    except Exception:
        logger.exception("VISA webhook: unhandled error reference=%s", our_reference)

    return {"received": True}
