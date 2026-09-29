def login(client,password="EneskoLocal2026!"):
    return client.post(
        "/api/v1/auth/login",
        data={"username":"admin@enesko.local","password":password},
    )


def tenant_login(client,password="TenantLocal2026!"):
    return client.post(
        "/api/v1/auth/login",
        data={"username":"tenant@enesko.local","password":password},
    )


def test_category2_auth_and_me(client):
    r=login(client)
    assert r.status_code==200
    token=r.json()["access_token"]
    me=client.get(
        "/api/v1/auth/me",
        headers={"Authorization":f"Bearer {token}"},
    )
    assert me.status_code==200
    assert me.json()["role"]=="PLATFORM_SUPER_ADMIN"


def test_admin_requires_auth(client):
    assert client.get("/api/v1/admin/overview").status_code==401


def test_admin_overview_and_audit(client):
    token=login(client).json()["access_token"]
    h={"Authorization":f"Bearer {token}"}
    assert client.get("/api/v1/admin/overview",headers=h).status_code==200

    created=client.post(
        "/api/v1/activations",
        json={
            "applicant_name":"Audit Test",
            "contact":"audit@example.invalid",
            "title":"Audit",
            "description":"Audit trail test",
            "proposed_date":"2026-10-10",
        },
        headers=h,
    )
    assert created.status_code==201

    audit=client.get("/api/v1/admin/audit",headers=h)
    assert audit.status_code==200
    assert any(x["path"]=="/api/v1/activations" for x in audit.json())


def test_wrong_password_rejected(client):
    assert login(client,"wrong").status_code==401


def test_tenant_rbac_path(client):
    r=tenant_login(client)
    assert r.status_code==200
    h={"Authorization":f"Bearer {r.json()['access_token']}"}

    me=client.get("/api/v1/tenant-portal/me",headers=h)
    assert me.status_code==200
    assert me.json()["tenant_name"]=="Test Tenant"
    assert client.get("/api/v1/admin/overview",headers=h).status_code==403


def test_tenant_request_reaches_admin_operations_and_stays_tenant_scoped(client):
    admin_token=login(client).json()["access_token"]
    admin_headers={"Authorization":f"Bearer {admin_token}"}
    before=client.get("/api/v1/admin/overview",headers=admin_headers)
    assert before.status_code==200
    before_count=before.json()["tenant_requests"]

    tenant_token=tenant_login(client).json()["access_token"]
    tenant_headers={"Authorization":f"Bearer {tenant_token}"}
    tenants=client.get("/api/v1/tenants",headers=tenant_headers)
    assert tenants.status_code==200
    assert len(tenants.json())==1
    tenant=tenants.json()[0]

    created=client.post(
        f"/api/v1/tenants/{tenant['id']}/requests",
        headers=tenant_headers,
        json={
            "request_type":"FACILITIES",
            "summary":"Air-conditioning support",
            "description":"The tenant requires facilities support for an air-conditioning issue.",
            "priority":"HIGH",
        },
    )
    assert created.status_code==201
    created_body=created.json()
    assert created_body["case"]["case_type"]=="TENANT_FACILITIES"
    assert created_body["case"]["channel"]=="tenant_portal"

    own_requests=client.get(
        f"/api/v1/tenants/{tenant['id']}/requests",
        headers=tenant_headers,
    )
    assert own_requests.status_code==200
    assert any(
        item["case"]["reference"]==created_body["case"]["reference"]
        for item in own_requests.json()
    )

    forbidden=client.get(
        f"/api/v1/tenants/{tenant['id'] + 999}/requests",
        headers=tenant_headers,
    )
    assert forbidden.status_code==403

    after=client.get("/api/v1/admin/overview",headers=admin_headers)
    assert after.status_code==200
    assert after.json()["tenant_requests"]==before_count+1
