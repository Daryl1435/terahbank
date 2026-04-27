from pydantic import BaseModel


class PushPayload(BaseModel):
    user_id: str
    fcm_token: str
    title: str
    body: str
    data: dict = {}


class EmailPayload(BaseModel):
    to: str
    template_id: str       # SendGrid template ID
    dynamic_data: dict = {}


class SMSPayload(BaseModel):
    to: str                # E.164 format
    message: str
    type: str = "ALERT"    # OTP | ALERT | REMINDER
