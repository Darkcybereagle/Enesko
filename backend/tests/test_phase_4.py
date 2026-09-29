def test_reference_route(client):
    response = client.get(
        "/api/v1/navigation/route",
        params={"from_node": "ICM-ENTRANCE-2", "to_node": "ICM-SAMSUNG"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_distance_m"] == 43.0
    assert len(body["steps"]) == 2
    assert body["data_status"] == "REFERENCE_MODEL"


def test_qr_location(client):
    response = client.get("/api/v1/map/qr/ENESKO-ICM-ENTRANCE-2")
    assert response.status_code == 200
    assert response.json()["code"] == "ICM-ENTRANCE-2"


def test_accessible_route(client):
    response = client.get(
        "/api/v1/navigation/route",
        params={
            "from_node": "ICM-ENTRANCE-2",
            "to_node": "ICM-SAMSUNG",
            "accessible_only": "true",
        },
    )
    assert response.status_code == 200
    assert response.json()["accessible_only"] is True
