def test_channels_do_not_fake_delivery(client, admin_headers):
    whatsapp=client.post(
        "/api/v1/channels/whatsapp/messages",
        headers=admin_headers,
        json={"recipient":"+2340000000000","body":"Channel delivery test"},
    )
    email=client.post(
        "/api/v1/channels/email/messages",
        headers=admin_headers,
        json={
            "recipient":"channel-test@example.invalid",
            "subject":"Channel test",
            "body":"Channel delivery test",
        },
    )
    assert whatsapp.status_code==202
    assert email.status_code==202
    assert whatsapp.json()["provider"]=="NOT_CONFIGURED"
    assert whatsapp.json()["status"]=="NOT_CONFIGURED"
    assert email.json()["provider"]=="NOT_CONFIGURED"
    assert email.json()["status"]=="NOT_CONFIGURED"
