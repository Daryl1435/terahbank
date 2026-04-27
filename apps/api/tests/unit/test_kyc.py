"""
KYC unit tests — gate enforcement, rejection reason storage, upload validation.
All external deps (S3, DB) are mocked.
"""

import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(kyc_status="pending", account_status="active"):
    user = MagicMock()
    user.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user.kyc_status = kyc_status
    user.account_status = account_status
    user.full_name = "Amina Njoya"
    user.email = "amina@example.com"
    user.phone_number = "+237600000001"
    return user


def _make_upload_file(content_type="image/jpeg", size_bytes=1024):
    """Simulate a FastAPI UploadFile."""
    data = b"x" * size_bytes
    f = MagicMock()
    f.content_type = content_type
    f.read = AsyncMock(return_value=data)
    return f


def _make_document(
    doc_id=None,
    user_id=None,
    document_type="national_id",
    status="pending",
    rejection_reason=None,
):
    doc = MagicMock()
    doc.id = doc_id or uuid.UUID("00000000-0000-0000-0000-000000000002")
    doc.user_id = user_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
    doc.document_type = document_type
    doc.status = status
    doc.rejection_reason = rejection_reason
    doc.uploaded_at = MagicMock()
    return doc


# ── KYC Gate Enforcement ───────────────────────────────────────────────────────

class TestKYCGate:
    """require_kyc_approved must return 403 when kyc_status != 'approved'."""

    @pytest.mark.asyncio
    async def test_pending_user_blocked(self):
        from core.dependencies import require_kyc_approved

        user = _make_user(kyc_status="pending")
        with pytest.raises(HTTPException) as exc:
            await require_kyc_approved(user=user)
        assert exc.value.status_code == 403
        assert exc.value.detail["code"] == "KYC_REQUIRED"

    @pytest.mark.asyncio
    async def test_rejected_user_blocked(self):
        from core.dependencies import require_kyc_approved

        user = _make_user(kyc_status="rejected")
        with pytest.raises(HTTPException) as exc:
            await require_kyc_approved(user=user)
        assert exc.value.status_code == 403
        assert exc.value.detail["code"] == "KYC_REQUIRED"

    @pytest.mark.asyncio
    async def test_approved_user_passes(self):
        from core.dependencies import require_kyc_approved

        user = _make_user(kyc_status="approved")
        result = await require_kyc_approved(user=user)
        assert result is user


# ── KYC Document Upload ────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestKYCUpload:

    async def _run_upload(self, user, file, document_type, mock_repo=None, mock_s3=None):
        from modules.kyc.service import KYCService

        db = AsyncMock()
        svc = KYCService(db)

        if mock_repo:
            svc._repo = mock_repo
        else:
            default_repo = AsyncMock()
            default_repo.create_document = AsyncMock(return_value=_make_document())
            svc._repo = default_repo

        with patch("modules.kyc.service.s3_client", new_callable=lambda: lambda: AsyncMock()) as s3, \
             patch("modules.kyc.service.write_audit_log", new_callable=AsyncMock):
            if mock_s3 is not None:
                s3.side_effect = mock_s3
            return await svc.upload_document(user, file, document_type)

    async def test_valid_jpeg_upload_succeeds(self):
        from modules.kyc.service import KYCService

        user = _make_user()
        file = _make_upload_file(content_type="image/jpeg")
        doc = _make_document()

        db = AsyncMock()
        svc = KYCService(db)
        svc._repo = AsyncMock()
        svc._repo.create_document = AsyncMock(return_value=doc)

        with patch("modules.kyc.service.s3_client", new=AsyncMock()), \
             patch("modules.kyc.service.write_audit_log", new=AsyncMock()):
            result = await svc.upload_document(user, file, "national_id")

        assert result.success is True
        assert result.data["document_id"] == str(doc.id)
        assert result.data["status"] == "pending"

    async def test_invalid_content_type_rejected(self):
        from modules.kyc.service import KYCService

        user = _make_user()
        file = _make_upload_file(content_type="image/gif")  # not allowed

        db = AsyncMock()
        svc = KYCService(db)
        svc._repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await svc.upload_document(user, file, "national_id")
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "INVALID_FILE_TYPE"

    async def test_invalid_document_type_rejected(self):
        from modules.kyc.service import KYCService

        user = _make_user()
        file = _make_upload_file(content_type="image/jpeg")

        db = AsyncMock()
        svc = KYCService(db)
        svc._repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await svc.upload_document(user, file, "drivers_license")  # not in enum
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "INVALID_DOCUMENT_TYPE"

    async def test_oversized_file_rejected(self):
        from modules.kyc.service import KYCService
        from core.config import settings

        user = _make_user()
        max_bytes = settings.KYC_MAX_FILE_SIZE_MB * 1024 * 1024
        # read() returns 1 byte more than the limit to trigger the check
        file = MagicMock()
        file.content_type = "application/pdf"
        file.read = AsyncMock(return_value=b"x" * (max_bytes + 1))

        db = AsyncMock()
        svc = KYCService(db)
        svc._repo = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await svc.upload_document(user, file, "passport")
        assert exc.value.status_code == 413
        assert exc.value.detail["code"] == "FILE_TOO_LARGE"

    async def test_s3_key_contains_user_and_doc_type(self):
        """Verify the S3 key follows kyc/{user_id}/{doc_type}/{uuid}.ext pattern."""
        from modules.kyc.service import KYCService

        user = _make_user()
        file = _make_upload_file(content_type="image/png")
        doc = _make_document()

        captured_key = []

        async def capture_s3(key, data, content_type):
            captured_key.append(key)

        db = AsyncMock()
        svc = KYCService(db)
        svc._repo = AsyncMock()
        svc._repo.create_document = AsyncMock(return_value=doc)

        with patch("modules.kyc.service.s3_client", new=capture_s3), \
             patch("modules.kyc.service.write_audit_log", new=AsyncMock()):
            await svc.upload_document(user, file, "passport")

        assert len(captured_key) == 1
        key = captured_key[0]
        assert key.startswith(f"kyc/{user.id}/passport/")
        assert key.endswith(".png")


# ── Admin KYC Decision ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestKYCDecision:

    async def _run_decision(self, user_id, payload, user=None, doc=None, admin=None):
        from modules.admin.service import AdminService
        from modules.admin.schemas import KYCDecisionRequest

        db = AsyncMock()
        svc = AdminService(db)
        svc._repo = AsyncMock()
        svc._repo.get_user_by_id = AsyncMock(return_value=user or _make_user())
        svc._repo.get_latest_pending_document = AsyncMock(return_value=doc or _make_document())
        svc._repo.update_document = AsyncMock(return_value=doc or _make_document())
        svc._repo.update_user = AsyncMock()

        with patch("modules.admin.service.write_audit_log", new=AsyncMock()):
            return await svc.make_kyc_decision(user_id, payload, admin)

    async def test_approve_updates_kyc_status(self):
        from modules.admin.schemas import KYCDecisionRequest

        user = _make_user(kyc_status="pending")
        db = AsyncMock()

        from modules.admin.service import AdminService

        svc = AdminService(db)
        svc._repo = AsyncMock()
        svc._repo.get_user_by_id = AsyncMock(return_value=user)
        svc._repo.get_latest_pending_document = AsyncMock(return_value=_make_document())
        svc._repo.update_document = AsyncMock()
        svc._repo.update_user = AsyncMock()

        payload = KYCDecisionRequest(decision="approved")

        with patch("modules.admin.service.write_audit_log", new=AsyncMock()):
            result = await svc.make_kyc_decision(str(user.id), payload)

        assert result.success is True
        assert result.data["kyc_status"] == "approved"
        # Verify user was updated with approved status
        svc._repo.update_user.assert_called_once_with(user, kyc_status="approved")

    async def test_reject_stores_rejection_reason(self):
        """FR-052: rejection reason must be persisted on the KYCDocument."""
        from modules.admin.schemas import KYCDecisionRequest
        from modules.admin.service import AdminService

        user = _make_user()
        doc = _make_document(status="pending")

        db = AsyncMock()
        svc = AdminService(db)
        svc._repo = AsyncMock()
        svc._repo.get_user_by_id = AsyncMock(return_value=user)
        svc._repo.get_latest_pending_document = AsyncMock(return_value=doc)
        svc._repo.update_document = AsyncMock(return_value=doc)
        svc._repo.update_user = AsyncMock()

        payload = KYCDecisionRequest(
            decision="rejected",
            rejection_reason="Document is blurry and unreadable.",
        )

        with patch("modules.admin.service.write_audit_log", new=AsyncMock()):
            result = await svc.make_kyc_decision(str(user.id), payload)

        assert result.success is True
        assert result.data["kyc_status"] == "rejected"

        # Verify the document was updated with the rejection reason
        call_kwargs = svc._repo.update_document.call_args
        update_fields = call_kwargs[1] if call_kwargs[1] else call_kwargs[0][1]
        # update_document(doc, **fields) — check fields dict
        _, kwargs = call_kwargs
        assert kwargs.get("rejection_reason") == "Document is blurry and unreadable."
        assert kwargs.get("status") == "rejected"

    async def test_reject_without_reason_fails(self):
        """rejection_reason is mandatory when decision=rejected."""
        from modules.admin.schemas import KYCDecisionRequest
        from modules.admin.service import AdminService

        user = _make_user()
        db = AsyncMock()
        svc = AdminService(db)
        svc._repo = AsyncMock()
        svc._repo.get_user_by_id = AsyncMock(return_value=user)
        svc._repo.get_latest_pending_document = AsyncMock(return_value=_make_document())

        payload = KYCDecisionRequest(decision="rejected", rejection_reason=None)

        with pytest.raises(HTTPException) as exc:
            await svc.make_kyc_decision(str(user.id), payload)
        assert exc.value.status_code == 422
        assert exc.value.detail["code"] == "REJECTION_REASON_REQUIRED"

    async def test_no_pending_document_returns_404(self):
        from modules.admin.schemas import KYCDecisionRequest
        from modules.admin.service import AdminService

        user = _make_user()
        db = AsyncMock()
        svc = AdminService(db)
        svc._repo = AsyncMock()
        svc._repo.get_user_by_id = AsyncMock(return_value=user)
        svc._repo.get_latest_pending_document = AsyncMock(return_value=None)

        payload = KYCDecisionRequest(decision="approved")

        with pytest.raises(HTTPException) as exc:
            await svc.make_kyc_decision(str(user.id), payload)
        assert exc.value.status_code == 404
        assert exc.value.detail["code"] == "NO_PENDING_DOCUMENT"

    async def test_audit_log_written_on_approval(self):
        from modules.admin.schemas import KYCDecisionRequest
        from modules.admin.service import AdminService

        user = _make_user()
        db = AsyncMock()
        svc = AdminService(db)
        svc._repo = AsyncMock()
        svc._repo.get_user_by_id = AsyncMock(return_value=user)
        svc._repo.get_latest_pending_document = AsyncMock(return_value=_make_document())
        svc._repo.update_document = AsyncMock()
        svc._repo.update_user = AsyncMock()

        payload = KYCDecisionRequest(decision="approved")

        with patch("modules.admin.service.write_audit_log", new=AsyncMock()) as mock_audit:
            await svc.make_kyc_decision(str(user.id), payload)

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs["action"] == "KYC_APPROVED"
        assert call_kwargs["actor_type"] == "admin"
