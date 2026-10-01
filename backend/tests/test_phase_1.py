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
    assert len(stores.json()) >= 50
    assert len(facilities.json()) == 0
    assert all(store["data_status"] in {"PUBLIC_VERIFIED", "PUBLIC_REFERENCE"} for store in stores.json())
    assert all(store["source_name"] for store in stores.json())
    assert all(store["verification_confidence"] in {"HIGH", "MEDIUM"} for store in stores.json())
    assert stores.json()[0]["discovery_priority"] >= stores.json()[-1]["discovery_priority"]


def test_customer_relevant_anchor_stores_are_present(client):
    stores = client.get("/api/v1/stores").json()
    names = {store["name"] for store in stores}
    required = {
        "Shoprite",
        "Silverbird Cinemas",
        "Miniso",
        "Samsung Experience Store",
        "iStore",
        "Pointek",
        "HealthPlus Pharmacy",
        "Medplus Pharmacy",
        "Adidas",
        "Nike Store Ikeja City Mall",
        "Ocean Basket",
    }
    assert required.issubset(names)


def test_exact_unit_metadata_is_kept_when_publicly_supported(client):
    stores = {store["name"]: store for store in client.get("/api/v1/stores").json()}
    assert stores["Miniso"]["unit"] == "Shop 19+20"
    assert stores["iStore"]["unit"] == "Shop L62"
    assert stores["Pointek"]["unit"] == "Shop L28"
    assert stores["HealthPlus Pharmacy"]["unit"] == "Shop L29"
    assert stores["Ocean Basket"]["unit"] == "Shop U06"
    assert stores["Ocean Basket"]["location_confidence"] == "EXACT_UNIT"


def test_category_filter(client):
    response = client.get("/api/v1/stores?category=Sports")
    assert response.status_code == 200
    names = {row["name"] for row in response.json()}
    assert {"Adidas", "Nike Store Ikeja City Mall", "Sports World"}.issubset(names)
