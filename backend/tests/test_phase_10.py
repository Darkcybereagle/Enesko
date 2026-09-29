def test_parking_staff_status(client, admin_headers):
    response = client.patch(
        "/api/v1/parking/ICM-PARKING-MAIN/status",
        headers=admin_headers,
        json={"occupancy_status": "BUSY", "expires_minutes": 30},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "ICM Parking"
    assert body["occupancy_status"] == "BUSY"
    assert body["data_status"] == "STAFF_VERIFIED"
