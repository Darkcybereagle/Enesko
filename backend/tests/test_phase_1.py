def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["implemented_phases"] == [1, 2]


def test_mall_core(client):
    malls = client.get("/api/v1/malls")
    stores = client.get("/api/v1/stores")
    facilities = client.get("/api/v1/facilities")
    assert malls.status_code == 200
    assert malls.json()[0]["name"] == "Ikeja City Mall"
    assert len(stores.json()) == 3
    assert len(facilities.json()) == 2


def test_category_filter(client):
    response = client.get("/api/v1/stores?category=Sports")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Demo Sports Store"
