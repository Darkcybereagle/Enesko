def test_store_finder(client):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Where can I buy sports shoes?", "channel": "web"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "store_search"
    assert body["data"]["stores"][0]["name"] == "Demo Sports Store"


def test_live_parking_is_not_invented(client):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "How many parking spaces are free right now?", "channel": "web"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["intent"] == "parking"
    assert body["needs_human"] is True
    assert "will not guess" in body["answer"].lower()


def test_lost_found_foundation(client):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "I lost my black bag at the food court", "channel": "voice"},
    )
    body = response.json()
    assert body["intent"] == "lost_found"
    assert body["needs_human"] is True
    assert body["data"]["workflow"] == "lost_found_intake"


def test_verified_knowledge(client):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"message": "Explain the data accuracy policy", "channel": "web"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["intent"] == "knowledge_query"
    assert body["sources"]
