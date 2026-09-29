def test_category3_phase_manifest(client):
    response=client.get("/api/v1/category3/status")
    assert response.status_code==200
    body=response.json()
    assert body["category"]==3
    assert body["implementation_status"]=="COMPLETE"
    assert len(body["phases"])==8
    assert all(item["status"]=="IMPLEMENTED" for item in body["phases"])


def test_category3_capabilities_and_grounding(client):
    capabilities=client.get("/api/v1/assistant/capabilities")
    assert capabilities.status_code==200
    body=capabilities.json()
    assert "voice" in body["channels"]
    assert "whatsapp" in body["channels"]
    assert "knowledge_retrieval" in body["tools"]

    grounded=client.post(
        "/api/v1/assistant/chat",
        json={"message":"Explain the data accuracy policy","channel":"web"},
    )
    assert grounded.status_code==200
    grounded_body=grounded.json()
    assert grounded_body["intent"]=="knowledge_query"
    assert grounded_body["sources"]
    assert grounded_body["sources"][0]["source_name"]


def test_category3_integration_status_is_truthful_when_unconfigured(client):
    response=client.get("/api/v1/integrations/status")
    assert response.status_code==200
    body=response.json()
    assert body["whatsapp"]["configured"] is False
    assert body["email"]["configured"] is False
    assert body["cinema"]["configured"] is False
    assert body["parking"]["configured"] is False
    assert body["voice"]["configured"] is True


def test_whatsapp_webhook_verification_and_inbound_assistant(client,admin_headers):
    verification=client.get(
        "/api/v1/channels/whatsapp/webhook",
        params={
            "hub.mode":"subscribe",
            "hub.verify_token":"test-verify-token",
            "hub.challenge":"12345",
        },
    )
    assert verification.status_code==200
    assert verification.text=="12345"

    inbound=client.post(
        "/api/v1/channels/whatsapp/webhook",
        json={
            "entry":[
                {
                    "changes":[
                        {
                            "value":{
                                "messages":[
                                    {
                                        "from":"2348000000000",
                                        "text":{"body":"Where can I buy sports shoes?"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )
    assert inbound.status_code==200
    assert inbound.json()["received"] is True
    assert inbound.json()["processed"]==1

    messages=client.get("/api/v1/channels/messages",headers=admin_headers)
    assert messages.status_code==200
    assert any(
        row["channel"]=="WHATSAPP"
        and row["direction"]=="INBOUND"
        and row["status"]=="RECEIVED"
        for row in messages.json()
    )


def test_email_inbound_requires_secret_and_routes_to_assistant(client,admin_headers):
    denied=client.post(
        "/api/v1/channels/email/inbound",
        json={
            "sender":"customer@example.com",
            "subject":"Help",
            "body":"I lost my black wallet at the food court",
        },
    )
    assert denied.status_code==401

    accepted=client.post(
        "/api/v1/channels/email/inbound",
        headers={"X-ENESKO-Webhook-Secret":"test-webhook-secret"},
        json={
            "sender":"customer@example.com",
            "subject":"Help",
            "body":"I lost my black wallet at the food court",
        },
    )
    assert accepted.status_code==200
    body=accepted.json()
    assert body["message"]["direction"]=="INBOUND"
    assert body["assistant"]["intent"]=="lost_found"
    assert body["reply"]["status"]=="NOT_CONFIGURED"

    messages=client.get("/api/v1/channels/messages",headers=admin_headers)
    assert any(
        row["channel"]=="EMAIL"
        and row["direction"]=="INBOUND"
        for row in messages.json()
    )


def test_category3_voice_turn_uses_shared_orchestration(client):
    started=client.post(
        "/api/v1/voice/sessions",
        json={"provider":"BROWSER_SPEECH"},
    )
    assert started.status_code==201
    ref=started.json()["session_ref"]

    turn=client.post(
        f"/api/v1/voice/sessions/{ref}/turn",
        json={"text":"How many parking spaces are free right now?"},
    )
    assert turn.status_code==200
    body=turn.json()
    assert body["intent"]=="parking"
    assert "will not guess" in body["answer"].lower()


def test_cinema_adapter_has_safe_unconfigured_release_path(client,admin_headers):
    status=client.get("/api/v1/cinema/integration-status")
    assert status.status_code==200
    assert status.json()["configured"] is False

    sync=client.post("/api/v1/cinema/sync",headers=admin_headers)
    assert sync.status_code==200
    body=sync.json()
    assert body["configured"] is False
    assert body["synced"]==0


def test_parking_adapter_has_safe_unconfigured_release_path(client,admin_headers):
    status=client.get("/api/v1/parking/integration-status")
    assert status.status_code==200
    assert status.json()["configured"] is False

    sync=client.post("/api/v1/parking/integration-sync",headers=admin_headers)
    assert sync.status_code==200
    body=sync.json()
    assert body["configured"] is False
    assert body["synced"]==0


def test_category3_integration_health_is_admin_protected(client,admin_headers):
    denied=client.get("/api/v1/integrations/health")
    assert denied.status_code==401

    response=client.get("/api/v1/integrations/health",headers=admin_headers)
    assert response.status_code==200
    body=response.json()
    assert body["status"]=="ok"
    assert body["providers"]["voice_web"]=="READY"
    assert body["verified_knowledge_documents"]>=1


def test_category3_spoken_navigation_invokes_existing_route_engine(client):
    started=client.post(
        "/api/v1/voice/sessions",
        json={"provider":"BROWSER_SPEECH"},
    )
    ref=started.json()["session_ref"]

    turn=client.post(
        f"/api/v1/voice/sessions/{ref}/turn",
        json={"text":"Take me to Samsung"},
    )
    assert turn.status_code==200
    body=turn.json()
    assert body["intent"]=="navigation"
    assert body["data"]["store"]["name"]=="Samsung Experience Store"
    assert body["data"]["route"]["from_node"]=="ICM-ENTRANCE-2"
    assert body["data"]["route"]["to_node"]=="ICM-SAMSUNG"
    assert body["data"]["route"]["steps"]
