import os
import pytest
import yaml
from utils.http import APIClient


@pytest.fixture(scope="session")
def config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def api_client(config):
    client = APIClient(base_url=config.get("base_url"), timeout=config.get("defaults", {}).get("timeout", 10), verify=config.get("verify_ssl", True))
    return client


@pytest.fixture(scope="session")
def auth_api_client(config):
    """Return an APIClient pre-authenticated via /api/login (uses config.auth)

    If login is successful and the response contains cookies (JSESSIONID), those cookies
    are copied into the session. If the response contains a bearer token in the JSON
    (e.g., token field), it is added to Authorization header.
    """
    client = APIClient(base_url=config.get("base_url"), timeout=config.get("defaults", {}).get("timeout", 10), verify=config.get("verify_ssl", True))
    auth = config.get("auth", {})
    username = auth.get("username")
    password = auth.get("password")
    if not username:
        pytest.skip("No auth username configured in config.yaml")

    # Attempt login
    try:
        resp = client.post("/api/login", json={"username": username, "password": password})
    except Exception:
        # network error — return unauthenticated client
        return client

    # copy cookies
    client.set_cookies_from_response(resp)

    # if JSON body has a token or sessionId, use it
    try:
        body = resp.json()
        if isinstance(body, dict):
            token = body.get("token") or body.get("access_token")
            if token:
                client.set_bearer_token(token)
            session_id = body.get("sessionId") or body.get("session_id")
            if session_id:
                client.set_cookie("JSESSIONID", session_id)
    except Exception:
        pass

    return client
