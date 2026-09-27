def test_demo_route(client):
    response = client.get("/api/v1/navigation/route", params={"from_node": "DEMO-ENTRANCE-1", "to_node": "DEMO-SPORTS-STORE"})
    assert response.status_code == 200
    body = response.json()
    assert body["total_distance_m"] == 43.0
    assert len(body["steps"]) == 2
    assert body["data_status"] == "DEMO"


def test_qr_location(client):
    response = client.get("/api/v1/map/qr/ENESKO-DEMO-ENTRANCE-1")
    assert response.status_code == 200
    assert response.json()["code"] == "DEMO-ENTRANCE-1"


def test_accessible_route(client):
    response = client.get("/api/v1/navigation/route", params={"from_node": "DEMO-ENTRANCE-1", "to_node": "DEMO-SPORTS-STORE", "accessible_only": "true"})
    assert response.status_code == 200
    assert response.json()["accessible_only"] is True
