def test_voice_session_lifecycle(client):
    started=client.post(
        "/api/v1/voice/sessions",
        json={"direction":"INBOUND","caller":"web-customer","provider":"BROWSER_SPEECH"},
    )
    assert started.status_code==201
    assert started.json()["provider"]=="BROWSER_SPEECH"
    ref=started.json()["session_ref"]

    turn=client.post(
        f"/api/v1/voice/sessions/{ref}/turn",
        json={"text":"Where can I buy sports shoes?"},
    )
    assert turn.status_code==200
    assert turn.json()["intent"]=="store_search"
    assert turn.json()["answer"]
    assert "USER:" in turn.json()["session"]["transcript"]
    assert "ENESKO:" in turn.json()["session"]["transcript"]

    completed=client.patch(
        f"/api/v1/voice/sessions/{ref}/complete",
        json={},
    )
    assert completed.status_code==200
    assert completed.json()["status"]=="COMPLETED"

    closed_turn=client.post(
        f"/api/v1/voice/sessions/{ref}/turn",
        json={"text":"Can you still hear me?"},
    )
    assert closed_turn.status_code==409
