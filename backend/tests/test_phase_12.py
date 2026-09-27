def test_smart_parking_observation_is_source_labeled(client):
    r=client.post("/api/v1/parking/observations",json={"area_code":"DEMO-P1","source_type":"SIMULATED_SENSOR","occupied":20,"available":10,"confidence":90,"data_status":"DEMO"})
    assert r.status_code==201 and r.json()["source_type"]=="SIMULATED_SENSOR" and r.json()["data_status"]=="DEMO"
