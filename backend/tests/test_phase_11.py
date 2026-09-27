def test_parking_adapter_safe_fallback(client):
    r=client.get("/api/v1/parking/integration-status")
    assert r.status_code==200 and r.json()["configured"] is False and r.json()["fallback"]=="staff_updated_phase10"
