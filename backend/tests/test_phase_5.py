def test_tenant_directory(client,tenant_headers):
    response=client.get("/api/v1/tenants",headers=tenant_headers)
    assert response.status_code==200 and any(t["name"]=="Test Tenant" for t in response.json())

def test_tenant_request_uses_unified_case_engine(client,tenant_headers):
    tenant=client.get("/api/v1/tenants",headers=tenant_headers).json()[0]
    response=client.post(f"/api/v1/tenants/{tenant['id']}/requests",headers=tenant_headers,json={"request_type":"MAINTENANCE","summary":"HVAC test request","description":"Automated tenant maintenance test request.","priority":"NORMAL"})
    assert response.status_code==201
    body=response.json();assert body["request_type"]=="MAINTENANCE" and body["case"]["case_type"]=="TENANT_MAINTENANCE"

def test_tenant_requests_list(client,tenant_headers):
    tenant=client.get("/api/v1/tenants",headers=tenant_headers).json()[0]
    client.post(f"/api/v1/tenants/{tenant['id']}/requests",headers=tenant_headers,json={"request_type":"MARKETING","summary":"Marketing test request","description":"Automated marketing support test request."})
    response=client.get(f"/api/v1/tenants/{tenant['id']}/requests",headers=tenant_headers)
    assert response.status_code==200 and response.json()

def test_tenant_announcements_documents_and_metrics(client,tenant_headers):
    tenant=client.get("/api/v1/tenants",headers=tenant_headers).json()[0]
    announcements=client.get(f"/api/v1/tenants/{tenant['id']}/announcements",headers=tenant_headers)
    documents=client.get(f"/api/v1/tenants/{tenant['id']}/documents",headers=tenant_headers)
    metrics=client.get(f"/api/v1/tenants/{tenant['id']}/metrics",headers=tenant_headers)
    assert announcements.status_code==200 and announcements.json()
    assert documents.status_code==200 and documents.json()
    assert metrics.status_code==200 and metrics.json()["tenant_id"]==tenant["id"]
