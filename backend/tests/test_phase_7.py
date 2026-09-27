def test_channels_do_not_fake_delivery(client):
    w=client.post("/api/v1/channels/whatsapp/messages",json={"recipient":"+2340000000000","body":"Demo"})
    e=client.post("/api/v1/channels/email/messages",json={"recipient":"demo@example.invalid","subject":"Demo","body":"Demo"})
    assert w.status_code==202 and e.status_code==202
    assert w.json()["provider"]=="NOT_CONFIGURED" and w.json()["status"]=="QUEUED_DEMO"
