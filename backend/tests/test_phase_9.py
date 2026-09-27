def test_cinema_demo_and_integration_status(client):
    s=client.get("/api/v1/cinema/shows"); i=client.get("/api/v1/cinema/integration-status")
    assert s.status_code==200 and s.json()[0]["data_status"]=="DEMO"
    assert i.json()["configured"] is False and i.json()["live_data_available"] is False
