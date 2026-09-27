def test_operational_analytics(client):
    r=client.get("/api/v1/analytics/operations")
    assert r.status_code==200
    body=r.json()
    assert "cases_total" in body and "tenant_requests" in body and body["data_status"]=="OPERATIONAL_DATABASE"
