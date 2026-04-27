"""
Unit test conftest — overrides the session-scoped create_tables fixture
so pure unit tests (financial calculations, validators, etc.) never attempt
a DB connection. These tests have no external dependencies.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def create_tables():  # type: ignore[override]
    """No-op override — unit tests do not need a database."""
    yield
