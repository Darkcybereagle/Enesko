import os
from pathlib import Path

TEST_DB = Path("test_enesko.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["APP_ENV"] = "test"
os.environ["WHATSAPP_API_VERSION"] = ""
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = ""
os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
os.environ["WHATSAPP_APP_SECRET"] = ""
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["INBOUND_WEBHOOK_SECRET"] = "test-webhook-secret"
os.environ["CINEMA_FEED_URL"] = ""
os.environ["PARKING_FEED_URL"] = ""

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
    r=client.post("/api/v1/auth/login",data={"username":"admin@enesko.local","password":"EneskoLocal2026!"})
    return {"Authorization":f"Bearer {r.json()['access_token']}"}

@pytest.fixture
def tenant_headers(client):
    r=client.post("/api/v1/auth/login",data={"username":"tenant@enesko.local","password":"TenantLocal2026!"})
    return {"Authorization":f"Bearer {r.json()['access_token']}"}
