def test_operational_analytics(client, admin_headers):
    r=client.get("/api/v1/analytics/operations",headers=admin_headers)
    assert r.status_code==200
    body=r.json()
    assert "cases_total" in body and "tenant_requests" in body and body["data_status"]=="OPERATIONAL_DATABASE"
