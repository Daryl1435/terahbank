import uuid
from datetime import datetime
from modules.auth.models import User
from core.security import hash_password


def make_approved_user(**kwargs) -> User:
    return User(
        id=uuid.uuid4(),
        full_name="Amina Njoya",
        phone_number="+237600000001",
        email="amina@terahbank.test",
        password_hash=hash_password("ValidPass1!"),
        kyc_status="approved",
        account_status="active",
        preferred_language="fr",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        **kwargs,
    )


def make_pending_kyc_user(**kwargs) -> User:
    return make_approved_user(kyc_status="pending", **kwargs)


def make_suspended_user(**kwargs) -> User:
    return make_approved_user(account_status="suspended", **kwargs)
