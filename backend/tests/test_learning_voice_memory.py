def _start_voice(client):
    response = client.post(
        "/api/v1/voice/sessions",
        json={"provider": "BROWSER_SPEECH"},
    )
    assert response.status_code == 201
    return response.json()["session_ref"]


def _turn(client, ref, text):
    response = client.post(
        f"/api/v1/voice/sessions/{ref}/turn",
        json={"text": text},
    )
    assert response.status_code == 200
    return response.json()


def test_voice_lost_found_is_a_stateful_interview_and_creates_case(client):
    ref = _start_voice(client)

    first = _turn(client, ref, "I lost something")
    assert first["intent"] == "lost_found"
    assert "what did you lose" in first["answer"].lower()
    assert first["memory"]["active_workflow"]["stage"] == "item"

    second = _turn(client, ref, "Black backpack")
    assert "colour" in second["answer"].lower()
    assert second["memory"]["active_workflow"]["stage"] == "features"

    third = _turn(client, ref, "Red Nike logo and a silver zip")
    assert "where" in third["answer"].lower()

    fourth = _turn(client, ref, "Near Ocean Basket")
    assert "what time" in fourth["answer"].lower()

    fifth = _turn(client, ref, "Around 7 PM")
    assert "phone number or email" in fifth["answer"].lower()

    sixth = _turn(client, ref, "08030000000")
    assert "should i submit" in sixth["answer"].lower()

    submitted = _turn(client, ref, "Yes")
    assert submitted["data"]["case_reference"].startswith("ENK-")
    reference = submitted["data"]["case_reference"]

    case = client.get(f"/api/v1/cases/{reference}")
    assert case.status_code == 200
    body = case.json()
    assert body["item_description"] == "Black backpack"
    assert body["distinguishing_features"] == "Red Nike logo and a silver zip"
    assert body["last_seen_location"] == "Near Ocean Basket"
    assert body["last_seen_time"] == "Around 7 PM"
    assert body["contact"] == "08030000000"


def test_voice_shopping_plan_memory_handles_follow_up_without_restarting(client):
    ref = _start_voice(client)

    planned = _turn(
        client,
        ref,
        "I want to buy sport shoe and want to eat then buy water",
    )
    assert planned["intent"] == "shopping_plan"
    assert planned["memory"]["shopping_plan_active"] is True

    follow_up = _turn(client, ref, "Which one first?")
    assert follow_up["intent"] == "shopping_plan"
    assert "next planned stop" in follow_up["answer"].lower()

    removed = _turn(client, ref, "Remove food")
    assert removed["intent"] == "shopping_plan"
    assert "removed food" in removed["answer"].lower()
    remaining = removed["data"]["shopping_plan"]["needs"]
    assert all("food" not in str(item["need"]).lower() for item in remaining)


def test_learning_pipeline_collects_only_anonymized_signals(client, admin_headers):
    ref = _start_voice(client)
    _turn(client, ref, "Where can I buy sports shoes?")

    status = client.get("/api/v1/learning/status", headers=admin_headers)
    assert status.status_code == 200
    body = status.json()
    assert body["learning_dataset_raw_customer_text_stored"] is False
    assert body["interaction_signals"] == 1
    assert body["active_model"] is None
    assert body["pipeline"][-1] == "ACTIVE_ENESKO_MODEL"


def test_learning_model_requires_training_testing_and_approval_before_prediction(client, admin_headers):
    for _ in range(12):
        ref = _start_voice(client)
        _turn(client, ref, "Where can I buy sports shoes?")
        _turn(client, ref, "What is the parking status right now?")

    trained = client.post("/api/v1/learning/train", headers=admin_headers)
    assert trained.status_code == 201
    candidate = trained.json()
    assert candidate["status"] == "TESTED"
    assert candidate["active"] is False
    assert candidate["training_event_count"] >= 24
    assert candidate["evaluation_score"] >= 0.50

    approved = client.post(
        f"/api/v1/learning/models/{candidate['id']}/approve",
        headers=admin_headers,
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    assert approved_body["status"] == "APPROVED"
    assert approved_body["active"] is True

    ref = _start_voice(client)
    predicted = _turn(client, ref, "Where can I buy sports shoes?")
    assert predicted["learning_suggestion"] == "parking"
    assert "approved anonymized enesko usage pattern" in predicted["answer"].lower()
