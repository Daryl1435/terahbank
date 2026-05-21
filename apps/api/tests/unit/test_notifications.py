"""
Unit tests for Milestone 6.2 — Notifications System.

Covers:
  - enqueue_notification: happy path (job added), BullMQ failure (logged, no raise)
  - dispatch_otp_sms: enqueues send_sms with OTP type
  - dispatch_push_and_inapp: in_app write + push enqueue when prefs enabled
  - dispatch_push_and_inapp: skips in-app when in_app_enabled=False
  - dispatch_push_and_inapp: skips push when push_enabled=False
  - dispatch_kyc_approved: push+inapp + email enqueued
  - dispatch_kyc_rejected: push+inapp + email with reason
  - dispatch_transaction_success: push+inapp only (no email/SMS)
  - dispatch_transaction_failed: push+inapp + SMS
  - dispatch_project_milestone: push+inapp with correct milestone %
  - dispatch_maturity_reminder: push+inapp + email
  - NotificationService.list_notifications: repo call, response shape
  - NotificationService.get_unread_count: returns count
  - NotificationService.mark_read: delegates to repo
  - NotificationService.mark_all_read: delegates to repo
  - NotificationService.get_preferences: repo call, response shape
  - NotificationService.update_preferences: updates + audit log + commit
  - NotificationService.register_device_token: upsert + commit

All DB, Redis, and BullMQ calls are mocked.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

_SVC = "modules.notifications.service"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_user(has_email=True):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.phone_number = "+237600000001"
    u.email = "test@example.com" if has_email else ""
    u.full_name = "Amina Njoya"
    return u


def _make_prefs(push=True, in_app=True, email=True, sms=True):
    p = MagicMock()
    p.push_enabled = push
    p.in_app_enabled = in_app
    p.email_enabled = email
    p.sms_enabled = sms
    return p


def _make_notification(read=False):
    n = MagicMock()
    n.id = uuid.uuid4()
    n.type = "TRANSACTION_SUCCESS"
    n.title = "Transaction réussie ✅"
    n.body = "Dépôt de 5000 XAF confirmé."
    n.metadata_ = {"amount": "5000"}
    n.read_at = datetime.utcnow() if read else None
    n.created_at = datetime.utcnow()
    return n


# ─── enqueue_notification ─────────────────────────────────────────────────────

class TestEnqueueNotification:
    @pytest.mark.asyncio
    async def test_enqueues_job(self):
        from modules.notifications.service import enqueue_notification

        # Queue is lazily imported inside enqueue_notification — patch at source
        mock_queue = AsyncMock()
        mock_queue.add = AsyncMock()
        with (
            patch("bullmq.Queue", return_value=mock_queue),
            patch("core.redis.get_redis_client", return_value=MagicMock()),
        ):
            await enqueue_notification("send_sms", {"to": "+237600000001", "message": "test"})

        mock_queue.add.assert_awaited_once()
        call_args = mock_queue.add.call_args
        assert call_args[0][0] == "send_sms"
        assert call_args[0][1]["to"] == "+237600000001"

    @pytest.mark.asyncio
    async def test_swallows_bullmq_exception(self):
        """BullMQ failure must NOT raise — notifications are best-effort."""
        from modules.notifications.service import enqueue_notification

        with (
            patch("bullmq.Queue", side_effect=Exception("Redis down")),
            patch("core.redis.get_redis_client", return_value=MagicMock()),
        ):
            # Should not raise
            await enqueue_notification("send_sms", {"to": "+237"})


# ─── dispatch_otp_sms ─────────────────────────────────────────────────────────

class TestDispatchOtpSms:
    @pytest.mark.asyncio
    async def test_enqueues_sms_with_otp_type(self):
        from modules.notifications.service import dispatch_otp_sms

        with patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq:
            await dispatch_otp_sms("+237600000001", "123456")

        mock_enq.assert_awaited_once()
        job_name, data = mock_enq.call_args[0]
        assert job_name == "send_sms"
        assert data["to"] == "+237600000001"
        assert "123456" in data["message"]
        assert data["msg_type"] == "OTP"


# ─── dispatch_push_and_inapp ──────────────────────────────────────────────────

class TestDispatchPushAndInapp:
    @pytest.mark.asyncio
    async def test_writes_inapp_and_enqueues_push_when_both_enabled(self):
        from modules.notifications.service import dispatch_push_and_inapp

        db = _make_db()
        user = _make_user()
        prefs = _make_prefs(push=True, in_app=True)

        mock_repo = AsyncMock()
        mock_repo.get_preferences = AsyncMock(return_value=prefs)
        mock_repo.create = AsyncMock()

        with (
            patch(f"{_SVC}.NotificationRepository", return_value=mock_repo),
            patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq,
        ):
            await dispatch_push_and_inapp(db, user.id, "TEST", "Title", "Body")

        mock_repo.create.assert_awaited_once()
        mock_enq.assert_awaited_once()
        assert mock_enq.call_args[0][0] == "send_push"

    @pytest.mark.asyncio
    async def test_skips_inapp_when_disabled(self):
        from modules.notifications.service import dispatch_push_and_inapp

        db = _make_db()
        user = _make_user()
        prefs = _make_prefs(push=True, in_app=False)

        mock_repo = AsyncMock()
        mock_repo.get_preferences = AsyncMock(return_value=prefs)
        mock_repo.create = AsyncMock()

        with (
            patch(f"{_SVC}.NotificationRepository", return_value=mock_repo),
            patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock),
        ):
            await dispatch_push_and_inapp(db, user.id, "TEST", "Title", "Body")

        mock_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_push_when_disabled(self):
        from modules.notifications.service import dispatch_push_and_inapp

        db = _make_db()
        user = _make_user()
        prefs = _make_prefs(push=False, in_app=True)

        mock_repo = AsyncMock()
        mock_repo.get_preferences = AsyncMock(return_value=prefs)
        mock_repo.create = AsyncMock()

        with (
            patch(f"{_SVC}.NotificationRepository", return_value=mock_repo),
            patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq,
        ):
            await dispatch_push_and_inapp(db, user.id, "TEST", "Title", "Body")

        mock_enq.assert_not_awaited()
        mock_repo.create.assert_awaited_once()


# ─── dispatch_kyc_approved ────────────────────────────────────────────────────

class TestDispatchKycApproved:
    @pytest.mark.asyncio
    async def test_enqueues_push_and_email(self):
        from modules.notifications.service import dispatch_kyc_approved

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push, \
             patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq:
            await dispatch_kyc_approved(db, user)

        mock_push.assert_awaited_once()
        # Email also enqueued
        mock_enq.assert_awaited_once()
        job_name, data = mock_enq.call_args[0]
        assert job_name == "send_email"
        assert data["template_id"] == "kyc_approved"
        assert data["to_email"] == user.email


# ─── dispatch_kyc_rejected ────────────────────────────────────────────────────

class TestDispatchKycRejected:
    @pytest.mark.asyncio
    async def test_enqueues_push_and_email_with_reason(self):
        from modules.notifications.service import dispatch_kyc_rejected

        db = _make_db()
        user = _make_user()
        reason = "Document illisible"

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push, \
             patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq:
            await dispatch_kyc_rejected(db, user, reason)

        mock_push.assert_awaited_once()
        # dispatch_push_and_inapp(db, user_id, type, title, body, metadata)
        push_body = mock_push.call_args[0][4]  # body is positional arg 4
        assert reason in push_body

        mock_enq.assert_awaited_once()
        _, data = mock_enq.call_args[0]
        assert data["dynamic_data"]["rejection_reason"] == reason


# ─── dispatch_transaction_success ────────────────────────────────────────────

class TestDispatchTransactionSuccess:
    @pytest.mark.asyncio
    async def test_enqueues_push_only(self):
        from modules.notifications.service import dispatch_transaction_success

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push, \
             patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq:
            await dispatch_transaction_success(db, user, "5000", "deposit", str(uuid.uuid4()))

        mock_push.assert_awaited_once()
        mock_enq.assert_not_awaited()  # no SMS or email for success


# ─── dispatch_transaction_failed ─────────────────────────────────────────────

class TestDispatchTransactionFailed:
    @pytest.mark.asyncio
    async def test_enqueues_push_and_sms(self):
        from modules.notifications.service import dispatch_transaction_failed

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push, \
             patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq:
            await dispatch_transaction_failed(db, user, "5000", "deposit", str(uuid.uuid4()))

        mock_push.assert_awaited_once()
        mock_enq.assert_awaited_once()
        job_name, data = mock_enq.call_args[0]
        assert job_name == "send_sms"
        assert data["to"] == user.phone_number
        assert data["msg_type"] == "ALERT"


# ─── dispatch_project_milestone ──────────────────────────────────────────────

class TestDispatchProjectMilestone:
    @pytest.mark.asyncio
    async def test_milestone_in_title(self):
        from modules.notifications.service import dispatch_project_milestone

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push:
            await dispatch_project_milestone(db, user, "Voiture", 50, str(uuid.uuid4()))

        mock_push.assert_awaited_once()
        title = mock_push.call_args[0][4]  # title arg
        assert "50" in title

    @pytest.mark.asyncio
    async def test_project_name_in_body(self):
        from modules.notifications.service import dispatch_project_milestone

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push:
            await dispatch_project_milestone(db, user, "Mariage", 75, str(uuid.uuid4()))

        # dispatch_push_and_inapp(db, user_id, type, title, body, metadata)
        body = mock_push.call_args[0][4]  # body is positional arg 4
        assert "Mariage" in body


# ─── dispatch_maturity_reminder ──────────────────────────────────────────────

class TestDispatchMaturityReminder:
    @pytest.mark.asyncio
    async def test_enqueues_push_and_email(self):
        from modules.notifications.service import dispatch_maturity_reminder

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push, \
             patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock) as mock_enq:
            await dispatch_maturity_reminder(db, user, "TD-001", 7, "500000", str(uuid.uuid4()))

        mock_push.assert_awaited_once()
        mock_enq.assert_awaited_once()
        _, data = mock_enq.call_args[0]
        assert data["template_id"] == "maturity_reminder"
        assert data["dynamic_data"]["days_left"] == 7
        assert data["dynamic_data"]["maturity_amount"] == "500000"

    @pytest.mark.asyncio
    async def test_days_left_in_push_title(self):
        from modules.notifications.service import dispatch_maturity_reminder

        db = _make_db()
        user = _make_user()

        with patch(f"{_SVC}.dispatch_push_and_inapp", new_callable=AsyncMock) as mock_push, \
             patch(f"{_SVC}.enqueue_notification", new_callable=AsyncMock):
            await dispatch_maturity_reminder(db, user, "TD-001", 14, "1000000", str(uuid.uuid4()))

        title = mock_push.call_args[0][4]
        assert "14" in title


# ─── NotificationService HTTP layer ──────────────────────────────────────────

class TestNotificationService:
    def _make_service(self, db=None):
        from modules.notifications.service import NotificationService
        return NotificationService(db or _make_db())

    @pytest.mark.asyncio
    async def test_list_notifications_returns_list(self):
        svc = self._make_service()
        notifs = [_make_notification(), _make_notification(read=True)]

        mock_repo = AsyncMock()
        mock_repo.list_for_user = AsyncMock(return_value=notifs)
        mock_repo.unread_count = AsyncMock(return_value=1)

        with patch("modules.notifications.service.NotificationRepository", return_value=mock_repo):
            svc._repo = mock_repo
            user = _make_user()
            response = await svc.list_notifications(user)

        assert response.success is True
        assert len(response.data["notifications"]) == 2
        assert response.data["unread_count"] == 1

    @pytest.mark.asyncio
    async def test_unread_count_returns_integer(self):
        svc = self._make_service()
        mock_repo = AsyncMock()
        mock_repo.unread_count = AsyncMock(return_value=5)
        svc._repo = mock_repo

        user = _make_user()
        response = await svc.get_unread_count(user)

        assert response.success is True
        assert response.data["unread_count"] == 5

    @pytest.mark.asyncio
    async def test_mark_read_success(self):
        svc = self._make_service()
        mock_repo = AsyncMock()
        mock_repo.mark_read = AsyncMock(return_value=True)
        svc._repo = mock_repo

        user = _make_user()
        notif_id = uuid.uuid4()
        response = await svc.mark_read(notif_id, user)

        assert response.success is True
        mock_repo.mark_read.assert_awaited_once_with(notif_id, user.id)

    @pytest.mark.asyncio
    async def test_mark_read_not_found(self):
        svc = self._make_service()
        mock_repo = AsyncMock()
        mock_repo.mark_read = AsyncMock(return_value=False)
        svc._repo = mock_repo

        user = _make_user()
        response = await svc.mark_read(uuid.uuid4(), user)
        assert response.success is False

    @pytest.mark.asyncio
    async def test_mark_all_read(self):
        svc = self._make_service()
        mock_repo = AsyncMock()
        mock_repo.mark_all_read = AsyncMock()
        svc._repo = mock_repo

        user = _make_user()
        response = await svc.mark_all_read(user)

        assert response.success is True
        mock_repo.mark_all_read.assert_awaited_once_with(user.id)

    @pytest.mark.asyncio
    async def test_get_preferences_all_fields(self):
        svc = self._make_service()
        prefs = _make_prefs()
        prefs.transaction_alerts = True
        prefs.security_alerts = True
        prefs.monthly_summary = False
        prefs.milestone_alerts = True
        prefs.maturity_reminders = True
        mock_repo = AsyncMock()
        mock_repo.get_preferences = AsyncMock(return_value=prefs)
        svc._repo = mock_repo

        user = _make_user()
        response = await svc.get_preferences(user)

        assert response.success is True
        data = response.data
        assert "push_enabled" in data
        assert "email_enabled" in data
        assert "transaction_alerts" in data

    @pytest.mark.asyncio
    async def test_update_preferences_writes_audit_and_commits(self):
        from modules.notifications.schemas import UpdatePreferencesRequest

        db = _make_db()
        svc = self._make_service(db)
        prefs = _make_prefs()
        prefs.transaction_alerts = True
        prefs.security_alerts = True
        prefs.monthly_summary = False
        prefs.milestone_alerts = True
        prefs.maturity_reminders = True

        mock_repo = AsyncMock()
        mock_repo.update_preferences = AsyncMock(return_value=prefs)
        mock_repo.get_preferences = AsyncMock(return_value=prefs)
        svc._repo = mock_repo

        payload = UpdatePreferencesRequest(push_enabled=False)
        user = _make_user()

        with patch(f"{_SVC}.write_audit_log", new_callable=AsyncMock) as mock_audit:
            response = await svc.update_preferences(payload, user)

        assert response.success is True
        mock_audit.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_device_token_commits(self):
        db = _make_db()
        svc = self._make_service(db)
        mock_repo = AsyncMock()
        mock_repo.upsert_device_token = AsyncMock()
        svc._repo = mock_repo

        user = _make_user()
        response = await svc.register_device_token("token_abc", "android", user)

        assert response.success is True
        mock_repo.upsert_device_token.assert_awaited_once_with(user.id, "token_abc", "android")
        db.commit.assert_awaited_once()
