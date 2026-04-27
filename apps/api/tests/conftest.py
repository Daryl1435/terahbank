import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from core.database import Base, get_db
from main import app

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/terahbank_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── External service mocks ─────────────────────────────────────────────────────
# Always mock external APIs — never call real providers in tests

@pytest.fixture
def mock_mtn_momo(mocker):
    return mocker.patch("modules.transactions.service.mtn_momo_client")


@pytest.fixture
def mock_sendgrid(mocker):
    return mocker.patch("modules.notifications.service.sendgrid_client")


@pytest.fixture
def mock_s3(mocker):
    return mocker.patch("modules.kyc.service.s3_client")


@pytest.fixture
def mock_fcm(mocker):
    return mocker.patch("modules.notifications.service.fcm_client")
