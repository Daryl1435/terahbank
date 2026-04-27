# Insurance product catalog from partner APIs.
# Products cached in Redis: insurance:catalog, 6-hour TTL.
# Referral flow: initiate enrollment → create pending record → redirect to partner.
# Renewal reminders via BullMQ scheduled job (30d and 7d before expiry).

import logging
import secrets
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.schemas import TerahResponse

from .repository import InsuranceRepository
from .schemas import (
    CancelPolicyResponseData,
    EnrollmentRequest,
    EnrollmentResponseData,
    InsuranceProductItem,
    PolicyDetailData,
    PolicyItem,
    PolicyListResponseData,
    ProductListResponseData,
)

logger = logging.getLogger("terahbank.insurance")

# ── Mock partner product catalog ──────────────────────────────────────────────
# In production: fetched from partner APIs at startup, cached in Redis 6h.
# Key: insurance:catalog | TTL: 21600s

_PARTNER_ENROLLMENT_BASE = "https://partners.terahbank.com/enroll"

MOCK_CATALOG: list[dict] = [
    {
        "product_id":          "nsia-health-pro",
        "partner_id":          "nsia",
        "name":                "NSIA Santé Pro",
        "description":         "Assurance santé de base couvrant consultations, médicaments et hospitalisation.",
        "policy_type":         "health",
        "monthly_premium_xaf": 2_500,
        "max_coverage_xaf":    500_000,
        "commission_xaf":      500,
        "features": [
            "Consultations médicales illimitées",
            "Médicaments remboursés à 80%",
            "Hospitalisation jusqu'à 500 000 XAF/an",
        ],
    },
    {
        "product_id":          "nsia-health-plus",
        "partner_id":          "nsia",
        "name":                "NSIA Santé Plus",
        "description":         "Couverture santé étendue avec soins dentaires et optique.",
        "policy_type":         "health",
        "monthly_premium_xaf": 5_000,
        "max_coverage_xaf":    2_000_000,
        "commission_xaf":      1_000,
        "features": [
            "Tout le forfait Pro",
            "Soins dentaires remboursés à 60%",
            "Optique jusqu'à 75 000 XAF/an",
            "Évacuation médicale Cameroun",
        ],
    },
    {
        "product_id":          "axa-device-guard",
        "partner_id":          "axa",
        "name":                "AXA Device Guard",
        "description":         "Protection contre le vol et la casse accidentelle de votre smartphone.",
        "policy_type":         "device",
        "monthly_premium_xaf": 1_500,
        "max_coverage_xaf":    150_000,
        "commission_xaf":      300,
        "features": [
            "Vol couvert (signalement police requis)",
            "Casse accidentelle de l'écran",
            "Remplacement sous 72h",
        ],
    },
    {
        "product_id":          "axa-device-pro",
        "partner_id":          "axa",
        "name":                "AXA Device Pro",
        "description":         "Protection étendue pour smartphones et tablettes, y compris la perte.",
        "policy_type":         "device",
        "monthly_premium_xaf": 3_000,
        "max_coverage_xaf":    300_000,
        "commission_xaf":      600,
        "features": [
            "Tout le forfait Guard",
            "Perte couverte (déclaration requise)",
            "Couvre smartphone + tablette",
            "Remplacement sous 24h à Yaoundé et Douala",
        ],
    },
    {
        "product_id":          "cima-micro-vie",
        "partner_id":          "cima",
        "name":                "CIMA Micro Vie",
        "description":         "Assurance vie micro — versement en cas de décès ou d'invalidité totale.",
        "policy_type":         "micro",
        "monthly_premium_xaf": 1_000,
        "max_coverage_xaf":    200_000,
        "commission_xaf":      200,
        "features": [
            "Capital décès 200 000 XAF",
            "Invalidité permanente totale",
            "Sans examen médical",
        ],
    },
    {
        "product_id":          "cima-micro-plus",
        "partner_id":          "cima",
        "name":                "CIMA Micro Plus",
        "description":         "Couverture vie étendue avec rente mensuelle en cas d'incapacité de travail.",
        "policy_type":         "micro",
        "monthly_premium_xaf": 2_000,
        "max_coverage_xaf":    500_000,
        "commission_xaf":      400,
        "features": [
            "Capital décès 500 000 XAF",
            "Rente mensuelle incapacité: 25 000 XAF",
            "Invalidité partielle couverte",
            "Sans examen médical",
        ],
    },
]

_CATALOG_BY_ID: dict[str, dict] = {p["product_id"]: p for p in MOCK_CATALOG}


def _days_until_expiry(expiry: date) -> int | None:
    delta = expiry - date.today()
    return delta.days if delta.days >= 0 else None


def _to_policy_item(policy, monthly_premium_xaf: int = 0) -> PolicyItem:
    return PolicyItem(
        policy_id=str(policy.id),
        partner_id=policy.partner_id,
        policy_type=policy.policy_type,
        policy_number=policy.policy_number,
        product_name=policy.product_name,
        status=policy.status,
        start_date=policy.start_date,
        expiry_date=policy.expiry_date,
        monthly_premium_xaf=monthly_premium_xaf,
        days_until_expiry=_days_until_expiry(policy.expiry_date),
    )


class InsuranceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._repo = InsuranceRepository(db)

    # ── Product catalog (FR-042) ──────────────────────────────────────────────

    async def list_products(self) -> TerahResponse:
        """Return available insurance products. Redis-cached 6h in production."""
        try:
            from core.redis import get_redis_client
            rc = get_redis_client()
            cached = await rc.get("insurance:catalog")
            if cached:
                import json
                products_data = json.loads(cached)
                items = [InsuranceProductItem(**p) for p in products_data]
                return TerahResponse(
                    success=True,
                    data=ProductListResponseData(products=items).model_dump(mode="json"),
                )
        except Exception:
            logger.debug("Redis cache miss for insurance:catalog — serving from mock")

        # Serve from mock catalog and cache
        items = [
            InsuranceProductItem(
                product_id=p["product_id"],
                partner_id=p["partner_id"],
                name=p["name"],
                description=p["description"],
                policy_type=p["policy_type"],
                monthly_premium_xaf=p["monthly_premium_xaf"],
                max_coverage_xaf=p["max_coverage_xaf"],
                features=p["features"],
            )
            for p in MOCK_CATALOG
        ]

        try:
            import json
            from core.redis import get_redis_client
            rc = get_redis_client()
            payload = [i.model_dump(mode="json") for i in items]
            await rc.setex("insurance:catalog", 21_600, json.dumps(payload))  # 6h TTL
        except Exception:
            pass

        return TerahResponse(
            success=True,
            data=ProductListResponseData(products=items).model_dump(mode="json"),
        )

    # ── Enrollment / referral (FR-043) ────────────────────────────────────────

    async def initiate_enrollment(
        self,
        payload: EnrollmentRequest,
        user_id: UUID,
    ) -> TerahResponse:
        """
        Initiate insurance policy enrollment.
        Creates a policy record and returns a redirect URL to the partner's enrollment page.
        In production: partner confirms via webhook → policy activated.
        In current implementation: policy is set to active immediately (simulated confirmation).
        """
        product = _CATALOG_BY_ID.get(payload.product_id)
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "PRODUCT_NOT_FOUND", "message": "Insurance product not found."},
            )

        today = date.today()
        expiry = today.replace(year=today.year + 1)  # 12-month policy

        # Generate policy number: {PARTNER}-{8-char hex}
        policy_number = f"{product['partner_id'].upper()}-{secrets.token_hex(4).upper()}"

        # Build partner redirect URL with a session reference
        session_ref = secrets.token_urlsafe(16)
        redirect_url = (
            f"{_PARTNER_ENROLLMENT_BASE}/{product['partner_id']}"
            f"?product={product['product_id']}&ref={session_ref}"
        )

        policy = await self._repo.create_policy(
            user_id=user_id,
            partner_id=product["partner_id"],
            policy_type=product["policy_type"],
            product_name=product["name"],
            policy_number=policy_number,
            status="active",  # simulated: partner confirmation immediate
            start_date=today,
            expiry_date=expiry,
            commission_amount=product["commission_xaf"],
        )

        await write_audit_log(
            self.db,
            actor_id=user_id,
            actor_type="user",
            action="INSURANCE_POLICY_ENROLLED",
            entity_type="insurance_policy",
            entity_id=policy.id,
            metadata={
                "product_id": product["product_id"],
                "partner_id": product["partner_id"],
                "policy_type": product["policy_type"],
                "commission_xaf": product["commission_xaf"],
            },
        )

        await self.db.commit()

        logger.info(
            "Insurance enrollment: user=%s product=%s policy=%s",
            user_id, product["product_id"], policy.id,
        )

        return TerahResponse(
            success=True,
            data=EnrollmentResponseData(
                policy_id=str(policy.id),
                partner_id=policy.partner_id,
                policy_type=policy.policy_type,
                policy_number=policy.policy_number,
                product_name=policy.product_name,
                status=policy.status,
                redirect_url=redirect_url,
                start_date=policy.start_date,
                expiry_date=policy.expiry_date,
            ).model_dump(mode="json"),
            message="Inscription enregistrée. Complétez l'activation chez notre partenaire.",
        )

    # ── Policy dashboard (FR-044) ─────────────────────────────────────────────

    async def list_user_policies(self, user_id: UUID) -> TerahResponse:
        """FR-044: Return user's insurance policies with expiry countdown."""
        policies = await self._repo.list_policies_for_user(user_id)
        items = []
        for policy in policies:
            product = _CATALOG_BY_ID.get(
                next((k for k, v in _CATALOG_BY_ID.items() if v["partner_id"] == policy.partner_id
                      and v["policy_type"] == policy.policy_type), ""),
                None,
            )
            monthly_premium = product["monthly_premium_xaf"] if product else 0
            items.append(_to_policy_item(policy, monthly_premium))

        return TerahResponse(
            success=True,
            data=PolicyListResponseData(
                policies=items,
                total=len(items),
            ).model_dump(mode="json"),
        )

    async def get_policy(self, policy_id: str, user_id: UUID) -> TerahResponse:
        try:
            pid = UUID(policy_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_POLICY_ID", "message": "Invalid policy ID."},
            )

        policy = await self._repo.get_policy(pid, user_id)
        if policy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "POLICY_NOT_FOUND", "message": "Policy not found."},
            )

        product = _CATALOG_BY_ID.get(
            next((k for k, v in _CATALOG_BY_ID.items() if v["partner_id"] == policy.partner_id
                  and v["policy_type"] == policy.policy_type), ""),
            None,
        )
        monthly_premium = product["monthly_premium_xaf"] if product else 0

        return TerahResponse(
            success=True,
            data=PolicyDetailData(
                policy_id=str(policy.id),
                partner_id=policy.partner_id,
                policy_type=policy.policy_type,
                policy_number=policy.policy_number,
                product_name=policy.product_name,
                status=policy.status,
                start_date=policy.start_date,
                expiry_date=policy.expiry_date,
                monthly_premium_xaf=monthly_premium,
                days_until_expiry=_days_until_expiry(policy.expiry_date),
                commission_amount=policy.commission_amount,
                created_at=policy.created_at.isoformat(),
            ).model_dump(mode="json"),
        )

    async def cancel_policy(self, policy_id: str, user_id: UUID) -> TerahResponse:
        try:
            pid = UUID(policy_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "INVALID_POLICY_ID", "message": "Invalid policy ID."},
            )

        policy = await self._repo.get_policy(pid, user_id)
        if policy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "POLICY_NOT_FOUND", "message": "Policy not found."},
            )

        if policy.status != "active":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "POLICY_NOT_ACTIVE", "message": "Only active policies can be cancelled."},
            )

        await self._repo.update_policy(policy, status="cancelled")

        await write_audit_log(
            self.db,
            actor_id=user_id,
            actor_type="user",
            action="INSURANCE_POLICY_CANCELLED",
            entity_type="insurance_policy",
            entity_id=policy.id,
            metadata={"policy_number": policy.policy_number, "partner_id": policy.partner_id},
        )

        await self.db.commit()

        return TerahResponse(
            success=True,
            data=CancelPolicyResponseData(
                policy_id=str(policy.id),
                status="cancelled",
            ).model_dump(),
            message="Police d'assurance résiliée.",
        )
