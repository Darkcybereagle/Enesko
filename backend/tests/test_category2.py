def login(client,password="EneskoDemo2026!"):
    return client.post("/api/v1/auth/login",data={"username":"admin@enesko.local","password":password})
def test_category2_auth_and_me(client):
    r=login(client);assert r.status_code==200
    token=r.json()["access_token"]
    me=client.get("/api/v1/auth/me",headers={"Authorization":f"Bearer {token}"})
    assert me.status_code==200 and me.json()["role"]=="PLATFORM_SUPER_ADMIN"
def test_admin_requires_auth(client):
    assert client.get("/api/v1/admin/overview").status_code==401
def test_admin_overview_and_audit(client):
    token=login(client).json()["access_token"];h={"Authorization":f"Bearer {token}"}
    assert client.get("/api/v1/admin/overview",headers=h).status_code==200
    client.post("/api/v1/activations",json={"applicant_name":"Audit Test","contact":"demo@example.invalid","title":"Audit","description":"Audit trail test","proposed_date":"DEMO"},headers=h)
    audit=client.get("/api/v1/admin/audit",headers=h)
    assert audit.status_code==200 and any(x["path"]=="/api/v1/activations" for x in audit.json())
def test_wrong_password_rejected(client):
    assert login(client,"wrong").status_code==401
