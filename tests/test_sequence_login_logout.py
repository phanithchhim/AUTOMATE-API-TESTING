import pytest


def test_login_signout_login_sequence(api_client, config):
    """Automated sequence: login, signout, then login again.

    Uses `api_client` fixture so it targets configured base_url. This test is
    deliberately small and self-contained to avoid running the larger manual
    tests.
    """
    auth = config.get("auth", {})
    username = auth.get("username")
    password = auth.get("password")

    if not username or not password:
        pytest.skip("No auth credentials in config.yaml")

    # First login
    resp1 = api_client.post("/api/login", json={"username": username, "password": password})
    assert resp1.status_code == 200
    # prefer token or cookie evidence
    try:
        body = resp1.json()
    except Exception:
        body = {}
    token = body.get("token") or body.get("access_token")
    session_id = None
    for c in getattr(api_client.session, "cookies", []):
        if c.name == "JSESSIONID":
            session_id = c.value
            break

    assert token or session_id, "login did not return token or cookie"

    # Signout
    resp2 = api_client.post("/api/signout", json={"username": username})
    assert resp2.status_code in (200, 400, 401)

    # Clear client cookies/headers to simulate fresh client, then login again
    api_client.session.cookies.clear()
    if "Authorization" in api_client.session.headers:
        api_client.session.headers.pop("Authorization")

    resp3 = api_client.post("/api/login", json={"username": username, "password": password})
    assert resp3.status_code == 200
    try:
        body2 = resp3.json()
    except Exception:
        body2 = {}
    token2 = body2.get("token") or body2.get("access_token")
    session_id2 = None
    for c in getattr(api_client.session, "cookies", []):
        if c.name == "JSESSIONID":
            session_id2 = c.value
            break

    assert token2 or session_id2, "second login did not return token or cookie"
