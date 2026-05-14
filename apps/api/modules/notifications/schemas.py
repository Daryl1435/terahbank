from datetime import datetime
from pydantic import BaseModel


# ── Inbound ───────────────────────────────────────────────────────────────────

class UpdatePreferencesRequest(BaseModel):
    push_enabled: bool | None = None
    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    in_app_enabled: bool | None = None
    transaction_alerts: bool | None = None
    security_alerts: bool | None = None
    monthly_summary: bool | None = None
    milestone_alerts: bool | None = None
    maturity_reminders: bool | None = None


class RegisterDeviceTokenRequest(BaseModel):
    token: str
    platform: str = "android"   # android | ios


# ── Outbound ──────────────────────────────────────────────────────────────────

class NotificationData(BaseModel):
    notification_id: str
    type: str
    title: str
    body: str
    metadata: dict
    read: bool
    created_at: datetime


class NotificationListData(BaseModel):
    notifications: list[NotificationData]
    unread_count: int


class PreferencesData(BaseModel):
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    in_app_enabled: bool
    transaction_alerts: bool
    security_alerts: bool
    monthly_summary: bool
    milestone_alerts: bool
    maturity_reminders: bool


class UnreadCountData(BaseModel):
    unread_count: int


# ── BullMQ job payloads (internal, used by notification_processor) ────────────

class PushPayload(BaseModel):
    user_id: str
    title: str
    body: str
    data: dict = {}


class EmailPayload(BaseModel):
    to_email: str
    to_name: str
    template_id: str
    dynamic_data: dict = {}


class SMSPayload(BaseModel):
    to: str          # E.164
    message: str
    msg_type: str = "ALERT"   # OTP | ALERT | REMINDER
