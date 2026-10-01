def test_access_qr_generates_svg(client):
    response = client.get(
        "/api/v1/access/qr.svg",
        params={"url": "https://enesko.example/customer"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert b"<svg" in response.content


def test_access_qr_rejects_unsafe_url(client):
    response = client.get(
        "/api/v1/access/qr.svg",
        params={"url": "javascript:alert(1)"},
    )
    assert response.status_code == 422
