import os
from pathlib import Path

TEST_DB = Path("test_enesko.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.seed import seed


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_headers(client):
    r=client.post("/api/v1/auth/login",data={"username":"admin@enesko.local","password":"EneskoDemo2026!"})
    return {"Authorization":f"Bearer {r.json()['access_token']}"}
