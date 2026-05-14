"""
FCM push notification client via Firebase Admin SDK.
Skips silently when credentials are not configured.
"""
import logging
from typing import Any

logger = logging.getLogger("terahbank.push")

_firebase_app = None


def _get_app():
    """Lazy-initialise Firebase Admin app (only when credentials are configured)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    from core.config import settings

    if not settings.FCM_CREDENTIALS_PATH or not settings.FCM_PROJECT_ID:
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialised (project=%s)", settings.FCM_PROJECT_ID)
    except Exception as exc:
        logger.warning("Firebase Admin SDK init failed: %s — push notifications disabled", exc)
        _firebase_app = None

    return _firebase_app


async def send_push(token: str, title: str, body: str, data: dict[str, Any] | None = None) -> bool:
    """
    Send a push notification to a single device token.
    Returns True on success, False if skipped or failed (non-fatal).
    """
    app = _get_app()
    if app is None:
        logger.debug("FCM not configured — push skipped: %s", title)
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            android=messaging.AndroidConfig(priority="high"),
        )
        messaging.send(message, app=app)
        logger.info("Push sent (token=...%s): %s", token[-8:], title)
        return True
    except Exception as exc:
        logger.error("Push delivery failed: %s", exc)
        return False


async def send_push_multicast(
    tokens: list[str], title: str, body: str, data: dict[str, Any] | None = None
) -> int:
    """Send to multiple tokens. Returns count of successful sends."""
    if not tokens:
        return 0

    app = _get_app()
    if app is None:
        return 0

    try:
        from firebase_admin import messaging

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            tokens=tokens,
            android=messaging.AndroidConfig(priority="high"),
        )
        response = messaging.send_each_for_multicast(message, app=app)
        logger.info("Push multicast: %d/%d succeeded", response.success_count, len(tokens))
        return response.success_count
    except Exception as exc:
        logger.error("Push multicast failed: %s", exc)
        return 0
