def test_voice_session_lifecycle(client):
    r=client.post("/api/v1/voice/sessions",json={"direction":"INBOUND","caller":"demo"})
    assert r.status_code==201 and r.json()["provider"]=="NOT_CONFIGURED"
    ref=r.json()["session_ref"]
    c=client.patch(f"/api/v1/voice/sessions/{ref}/complete",json={"transcript":"Demo transcript","summary":"Demo summary"})
    assert c.status_code==200 and c.json()["status"]=="COMPLETED"
