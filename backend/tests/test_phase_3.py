def test_case_lifecycle_and_notification(client, admin_headers):
    created = client.post("/api/v1/cases", json={
        "case_type": "LOST_FOUND",
        "summary": "Lost black backpack",
        "description": "Black backpack last seen near the food court.",
        "channel": "web",
        "contact": "customer@example.invalid",
        "item_description": "Black backpack",
        "last_seen_location": "Food Court",
        "distinguishing_features": "Small white tag",
    })
    assert created.status_code == 201
    reference = created.json()["reference"]
    assert reference.startswith("ENK-")

    updated = client.patch(f"/api/v1/cases/{reference}/status", headers=admin_headers, json={
        "status": "IN_PROGRESS", "note": "Assigned to customer service", "actor": "ops-test"
    })
    assert updated.status_code == 200
    assert updated.json()["status"] == "IN_PROGRESS"

    notifications = client.get("/api/v1/notifications", headers=admin_headers)
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


def test_case_rejects_unknown_lifecycle_status(client, admin_headers):
    created = client.post("/api/v1/cases", json={
        "case_type": "CUSTOMER_ASSISTANCE",
        "summary": "Lifecycle validation",
        "description": "Verify that Category 2 accepts only the supported request states.",
        "channel": "web",
    })
    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/cases/{created.json()['reference']}/status",
        headers=admin_headers,
        json={
            "status": "INVESTIGATING",
            "note": "Unsupported status should be rejected.",
            "actor": "ops-test",
        },
    )
    assert response.status_code == 422
