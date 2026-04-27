from datetime import date
from typing import Literal

from pydantic import BaseModel


# ── Products ──────────────────────────────────────────────────────────────────

class InsuranceProductItem(BaseModel):
    product_id:           str
    partner_id:           str
    name:                 str
    description:          str
    policy_type:          Literal["health", "device", "micro"]
    monthly_premium_xaf:  int   # BIGINT — XAF units
    max_coverage_xaf:     int   # BIGINT — XAF units
    features:             list[str]

class ProductListResponseData(BaseModel):
    products: list[InsuranceProductItem]


# ── Enrollment ─────────────────────────────────────────────────────────────────

class EnrollmentRequest(BaseModel):
    product_id: str


class EnrollmentResponseData(BaseModel):
    policy_id:   str
    partner_id:  str
    policy_type: str
    policy_number: str
    product_name:  str
    status:      str
    redirect_url: str
    start_date:  date
    expiry_date: date


# ── Policies ──────────────────────────────────────────────────────────────────

class PolicyItem(BaseModel):
    policy_id:           str
    partner_id:          str
    policy_type:         str
    policy_number:       str
    product_name:        str
    status:              str
    start_date:          date
    expiry_date:         date
    monthly_premium_xaf: int
    days_until_expiry:   int | None

class PolicyListResponseData(BaseModel):
    policies: list[PolicyItem]
    total:    int


class PolicyDetailData(PolicyItem):
    commission_amount: int
    created_at: str


# ── Cancel ────────────────────────────────────────────────────────────────────

class CancelPolicyResponseData(BaseModel):
    policy_id: str
    status:    str
