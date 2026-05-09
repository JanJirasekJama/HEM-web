from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.bootstrap import bootstrap_core
from app.core.config import Settings
from app.core.database import Base, get_db
from app.main import create_app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSessionLocal() as db:
        bootstrap_core(db)
        yield db
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session, tmp_path: Path) -> Generator[TestClient, None, None]:
    settings = Settings(
        app_env="test",
        database_url="sqlite+pysqlite://",
        redis_url="memory://test",
        file_storage_root=tmp_path / "files",
        secret_key="test-secret",
    )
    app = create_app(settings)

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def admin_auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": "admin", "password": "061004"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}

