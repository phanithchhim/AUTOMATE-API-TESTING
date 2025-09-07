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
def merged_config(config):
    """Return configuration overlayed with environment variables when present.

    Environment variables supported:
      - BASE_URL
      - AUTH_USERNAME
      - AUTH_PASSWORD
      - VERIFY_SSL (true/false)
      - DEFAULT_TIMEOUT
    """
    cfg = dict(config or {})
    # override with env vars when provided
    base = os.environ.get("BASE_URL")
    if base:
        cfg["base_url"] = base

    auth_user = os.environ.get("AUTH_USERNAME")
    auth_pass = os.environ.get("AUTH_PASSWORD")
    if auth_user or auth_pass:
        cfg.setdefault("auth", {})
        if auth_user:
            cfg["auth"]["username"] = auth_user
        if auth_pass:
            cfg["auth"]["password"] = auth_pass

    verify = os.environ.get("VERIFY_SSL")
    if verify is not None:
        cfg["verify_ssl"] = verify.lower() not in ("0", "false", "no")

    timeout = os.environ.get("DEFAULT_TIMEOUT")
    if timeout:
        cfg.setdefault("defaults", {})["timeout"] = int(timeout)

    return cfg


@pytest.fixture(scope="session")
def api_client(merged_config):
    """API client using merged configuration (config.yaml overlaid with env vars)."""
    cfg = merged_config
    client = APIClient(base_url=cfg.get("base_url"), timeout=cfg.get("defaults", {}).get("timeout", 10), verify=cfg.get("verify_ssl", True))
    return client


@pytest.fixture(scope="session")
def auth_api_client(merged_config):
    """Return an APIClient pre-authenticated via /api/login (uses config.auth)

    If login is successful and the response contains cookies (JSESSIONID), those cookies
    are copied into the session. If the response contains a bearer token in the JSON
    (e.g., token field), it is added to Authorization header.
    """
    client = APIClient(base_url=merged_config.get("base_url"), timeout=merged_config.get("defaults", {}).get("timeout", 10), verify=merged_config.get("verify_ssl", True))
    auth = merged_config.get("auth", {})
    username = auth.get("username")
    password = auth.get("password")
    if not username:
        pytest.skip("No auth username configured in config.yaml or AUTH_USERNAME env var")

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
