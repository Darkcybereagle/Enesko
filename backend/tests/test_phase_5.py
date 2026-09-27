def test_tenant_directory(client):
    response = client.get("/api/v1/tenants")
    assert response.status_code == 200
    assert any(t["name"] == "Demo Sports Tenant" for t in response.json())


def test_tenant_request_uses_unified_case_engine(client):
    tenants = client.get("/api/v1/tenants").json()
    tenant = next(t for t in tenants if t["name"] == "Demo Sports Tenant")
    response = client.post(f"/api/v1/tenants/{tenant['id']}/requests", json={
        "request_type": "MAINTENANCE", "summary": "Demo HVAC request",
        "description": "Development-only tenant maintenance request.", "priority": "NORMAL"
    })
    assert response.status_code == 201
    body = response.json()
    assert body["request_type"] == "MAINTENANCE"
    assert body["case"]["case_type"] == "TENANT_MAINTENANCE"
    assert body["case"]["reference"].startswith("ENK-")


def test_tenant_requests_list(client):
    tenant = client.get("/api/v1/tenants").json()[0]
    client.post(f"/api/v1/tenants/{tenant['id']}/requests", json={
        "request_type": "MARKETING", "summary": "Demo marketing request",
        "description": "Development-only marketing support request."
    })
    response = client.get(f"/api/v1/tenants/{tenant['id']}/requests")
    assert response.status_code == 200
    assert response.json()


def test_tenant_announcements_documents_and_metrics(client):
    tenant = client.get("/api/v1/tenants").json()[0]
    announcements = client.get(f"/api/v1/tenants/{tenant['id']}/announcements")
    documents = client.get(f"/api/v1/tenants/{tenant['id']}/documents")
    metrics = client.get(f"/api/v1/tenants/{tenant['id']}/metrics")
    assert announcements.status_code == 200 and announcements.json()
    assert documents.status_code == 200 and documents.json()
    assert metrics.status_code == 200
    assert metrics.json()["tenant_id"] == tenant["id"]
