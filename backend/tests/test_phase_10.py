def test_parking_staff_status(client):
    r=client.patch("/api/v1/parking/DEMO-P1/status",json={"occupancy_status":"BUSY","expires_minutes":30})
    assert r.status_code==200 and r.json()["occupancy_status"]=="BUSY" and r.json()["data_status"]=="STAFF_VERIFIED"
