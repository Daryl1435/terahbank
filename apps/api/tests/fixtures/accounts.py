import uuid
from datetime import datetime, date
from modules.accounts.models import Account


def make_standard_account(balance: int = 500000, **kwargs) -> Account:
    """Default balance: 5,000 XAF (500000 smallest units)."""
    return Account(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        account_type="standard",
        account_number=f"STD{uuid.uuid4().hex[:10].upper()}",
        balance=balance,
        status="active",
        created_at=datetime.utcnow(),
        **kwargs,
    )


def make_project_account(target: int = 10000000, current: int = 2500000, **kwargs) -> Account:
    """Default: 25% funded — should trigger first milestone notification."""
    return Account(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        account_type="project",
        account_number=f"PRJ{uuid.uuid4().hex[:10].upper()}",
        balance=current,
        target_amount=target,
        target_date=date(2027, 1, 1),
        status="active",
        created_at=datetime.utcnow(),
        **kwargs,
    )


def make_term_deposit(balance: int = 20000000, **kwargs) -> Account:
    """Default: 200,000 XAF (minimum term deposit)."""
    return Account(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        account_type="term_deposit",
        account_number=f"TD{uuid.uuid4().hex[:10].upper()}",
        balance=balance,
        status="active",
        maturity_date=date(2027, 1, 1),
        created_at=datetime.utcnow(),
        **kwargs,
    )
