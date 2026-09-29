def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["implemented_phases"] == list(range(1, 14))


def test_mall_core(client):
    malls = client.get("/api/v1/malls")
    stores = client.get("/api/v1/stores")
    facilities = client.get("/api/v1/facilities")
    assert malls.status_code == 200
    assert malls.json()[0]["name"] == "Ikeja City Mall"
    assert len(stores.json()) == 5
    assert len(facilities.json()) == 0
    assert all(store["data_status"] == "PUBLIC_VERIFIED" for store in stores.json())
    assert all(store["source_name"] for store in stores.json())


def test_category_filter(client):
    response = client.get("/api/v1/stores?category=Sports")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert names == {"Adidas", "Nike Store Ikeja City Mall", "Sports World"}
