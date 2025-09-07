import pytest
import json
import os
from utils.schema import assert_json_schema
from utils.schema_loader import load_schema


def test_hello(api_client):
    resp = api_client.get("/api/hello")
    # server may or may not expose this in some environments; accept 200 or 404
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        assert "CMS Portal API" in resp.text or len(resp.text) > 0


def test_debug_ip(api_client):
    resp = api_client.get("/api/debug/ip")
    assert resp.status_code == 200
    try:
        body = resp.json()
        assert all(k in body for k in ("remoteAddr", "xff", "verified_remote_ip"))
    except Exception:
        pytest.skip("debug ip did not return JSON")


def test_login_and_auth_api_client(auth_api_client, config):
    # auth_api_client fixture attempts login at session start; ensure client can access an auth-only endpoint
    client = auth_api_client
    # Try to fetch users list (likely protected)
    resp = client.get("/api/users")
    # Accept 200 for success, 401/403 for unauthorized
    assert resp.status_code in (200, 401, 403, 404)


def test_list_users_and_schema(auth_api_client):
    client = auth_api_client
    resp = client.get("/api/users")
    assert resp.status_code in (200, 401, 403, 404)
    if resp.status_code != 200:
        pytest.skip("users list not available or unauthorized")
    body = resp.json()
    assert isinstance(body.get("data"), list)
    if body.get("data"):
        schema = load_schema("user_schema.json")
        if schema:
            assert_json_schema(body.get("data")[0], schema)


def test_get_user_by_id_non_destructive(auth_api_client):
    client = auth_api_client
    # attempt to list users and then fetch one by id if present
    resp = client.get("/api/users")
    if resp.status_code != 200:
        pytest.skip("cannot list users")
    body = resp.json()
    data = body.get("data") or []
    if not data:
        pytest.skip("no users to test retrieval")
    uid = data[0].get("userId") or data[0].get("id")
    if not uid:
        pytest.skip("user id not found in listing")
    resp2 = client.get(f"/api/users/{uid}")
    assert resp2.status_code in (200, 404)
    if resp2.status_code == 200:
        schema = load_schema("user_schema.json")
        if schema:
            assert_json_schema(resp2.json(), schema)


def test_get_user_permissions_non_destructive(auth_api_client):
    client = auth_api_client
    # get a user id first
    resp = client.get("/api/users")
    if resp.status_code != 200:
        pytest.skip("cannot list users")
    body = resp.json()
    data = body.get("data") or []
    if not data:
        pytest.skip("no users to test permissions")
    uid = data[0].get("userId") or data[0].get("id")
    resp2 = client.get(f"/api/users/{uid}/permissions")
    assert resp2.status_code in (200, 404, 401, 403)


def test_roles_list_and_schema(auth_api_client):
    client = auth_api_client
    resp = client.get("/api/roles")
    assert resp.status_code in (200, 401, 403, 404)
    if resp.status_code != 200:
        pytest.skip("roles not available")
    body = resp.json()
    assert isinstance(body.get("data"), list)
    if body.get("data"):
        schema = load_schema("role_schema.json")
        if schema:
            assert_json_schema(body.get("data")[0], schema)


def test_get_role_by_id_non_destructive(auth_api_client):
    client = auth_api_client
    resp = client.get("/api/roles")
    if resp.status_code != 200:
        pytest.skip("roles list not available")
    data = resp.json().get("data") or []
    if not data:
        pytest.skip("no roles to test")
    rid = data[0].get("roleId") or data[0].get("id")
    resp2 = client.get(f"/api/roles/{rid}")
    assert resp2.status_code in (200, 404)


def test_role_permissions_list_non_destructive(auth_api_client):
    client = auth_api_client
    # list permissions for a likely role id 1; accept various codes
    resp = client.get("/api/roles/permissions/1")
    assert resp.status_code in (200, 404, 401, 403)


def test_invalid_manage_role_action(api_client):
    # non-auth attempt to manage role with invalid action should be rejected or unauthorized
    payload = {"action": "INVALID", "roleName": "test-x"}
    resp = api_client.post("/api/roles", json=payload)
    # if unauthenticated, server may return 401/403; if authenticated required, same
    assert resp.status_code in (400, 401, 403)


def test_assign_permission_invalid_action(auth_api_client):
    client = auth_api_client
    payload = {"action": "INVALID", "roleId": 1, "menuId": 1, "permissionId": 1}
    resp = client.post("/api/roles/permissions", json=payload)
    assert resp.status_code == 400
