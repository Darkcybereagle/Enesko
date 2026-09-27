def test_activation_workflow(client, admin_headers):
    r=client.post("/api/v1/activations",json={"applicant_name":"Demo Brand","contact":"demo@example.invalid","title":"Demo Event","description":"Development test","proposed_date":"2026-10-10"})
    assert r.status_code==201
    ref=r.json()["reference"]
    u=client.patch(f"/api/v1/activations/{ref}/stage",headers=admin_headers,json={"current_stage":"MARKETING_REVIEW","status":"IN_REVIEW"})
    assert u.status_code==200 and u.json()["current_stage"]=="MARKETING_REVIEW"
