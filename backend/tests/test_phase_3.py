def test_case_lifecycle_and_notification(client):
    created = client.post("/api/v1/cases", json={
        "case_type": "LOST_FOUND",
        "summary": "Lost black backpack",
        "description": "Black backpack last seen near the demo food court.",
        "channel": "web",
        "contact": "demo@example.invalid",
        "item_description": "Black backpack",
        "last_seen_location": "Demo Food Court",
        "distinguishing_features": "Small white tag",
    })
    assert created.status_code == 201
    reference = created.json()["reference"]
    assert reference.startswith("ENK-")

    updated = client.patch(f"/api/v1/cases/{reference}/status", json={
        "status": "INVESTIGATING", "note": "Assigned to customer service", "actor": "demo-staff"
    })
    assert updated.status_code == 200
    assert updated.json()["status"] == "INVESTIGATING"

    notifications = client.get("/api/v1/notifications")
    assert notifications.status_code == 200
    assert any(item["case_id"] == created.json()["id"] for item in notifications.json())


def test_human_handoff_case_type_supported(client):
    response = client.post("/api/v1/cases", json={
        "case_type": "HUMAN_HANDOFF",
        "summary": "Customer requested an agent",
        "description": "Transfer context to customer service.",
        "channel": "voice",
    })
    assert response.status_code == 201
    assert response.json()["case_type"] == "HUMAN_HANDOFF"
