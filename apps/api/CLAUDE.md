# TerahBank API — FastAPI Backend
Python 3.12 + FastAPI + PostgreSQL + Redis + BullMQ

## Module pattern (enforce on every new module)
```
modules/{name}/
├── router.py      ← HTTP only. No business logic.
├── service.py     ← Business logic. Calls repo. Writes audit logs.
├── repository.py  ← DB queries only. Raw SQLAlchemy.
├── models.py      ← ORM models. UUID PKs. BIGINT money. TIMESTAMPTZ times.
├── schemas.py     ← Pydantic v2 request/response models.
└── tests/
    ├── test_unit.py
    └── test_integration.py
```

## Response schema — always use this, no exceptions
```python
class TerahResponse(BaseModel):
    success: bool
    data: Any = None
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

## FastAPI dependency chain (standard for all protected routes)
```python
@router.post("/")
async def create_something(
    payload: CreateRequest,
    idempotency_key: str = Header(...),        # Required on all transaction routes
    user: User = Depends(get_current_user),    # JWT validation
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_kyc_approved),   # 403 if kyc_status != 'approved'
):
```

## Audit log — write before returning, always
```python
await write_audit_log(db,
    actor_id=user.id,
    action="TRANSFER_INITIATED",
    entity_type="transaction",
    entity_id=str(txn.id),
    metadata={"amount": payload.amount, "to": payload.recipient_id}
)
```

## Background jobs
- Use BullMQ via Redis for all slow/async work
- Payment jobs: `attempts=1` — NEVER auto-retry (double charge risk)
- Notification jobs: `attempts=3`, exponential backoff
- Use `/add-notification` skill when adding new notification types
- Use `/momo-integration` skill for Mobile Money flows

## Test rules
- Financial calculations: mandatory unit tests, no exceptions
- Every endpoint: auth test + validation test + happy path + error path
- External services (MoMo, SendGrid, S3): always mock in tests
- Run: `pytest tests/unit/ --cov=modules --cov-fail-under=80`

## Available skills for this module
- `/add-api-module` — scaffold a complete new module
- `/new-db-migration` — create an Alembic migration
- `/run-migrations` — run and verify migrations
- `/financial-calc` — correct patterns for XAF arithmetic
- `/momo-integration` — MTN MoMo / Orange Money flows
- `/add-notification` — add a new notification event
