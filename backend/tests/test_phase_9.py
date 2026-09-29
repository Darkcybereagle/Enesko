def test_cinema_official_reference_and_integration_status(client):
    shows = client.get("/api/v1/cinema/shows")
    status = client.get("/api/v1/cinema/integration-status")
    assert shows.status_code == 200
    assert shows.json() == []
    assert status.status_code == 200
    body = status.json()
    assert body["configured"] is False
    assert body["live_data_available"] is False
    assert body["cinema_name"] == "Silverbird Cinemas, Ikeja City Mall"
    assert body["official_booking_url"].startswith("https://silverbirdcinemas.com/")
