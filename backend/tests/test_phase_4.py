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


def test_reference_map_includes_three_entrance_anchors_and_vertical_core(client):
    nodes = client.get("/api/v1/map/nodes")
    assert nodes.status_code == 200
    by_code = {row["code"]: row for row in nodes.json()}
    assert {"ICM-ENTRANCE-1", "ICM-ENTRANCE-2", "ICM-ENTRANCE-3"}.issubset(by_code)
    assert "ICM-VERTICAL-CORE-G" in by_code
    assert "ICM-VERTICAL-CORE-T" in by_code
    assert all(
        by_code[code]["data_status"] == "REFERENCE_MODEL"
        for code in ("ICM-ENTRANCE-1", "ICM-ENTRANCE-2", "ICM-ENTRANCE-3")
    )


def test_reference_route_reaches_top_floor_tenant_anchor(client):
    response = client.get(
        "/api/v1/navigation/route",
        params={
            "from_node": "ICM-ENTRANCE-2",
            "to_node": "ICM-OCEAN-BASKET",
            "accessible_only": "true",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["to_node"] == "ICM-OCEAN-BASKET"
    assert body["data_status"] == "REFERENCE_MODEL"
    assert len(body["steps"]) >= 4
