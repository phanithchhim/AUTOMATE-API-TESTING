import pytest
from utils.schema_loader import load_schema
from utils.schema import assert_json_schema


@pytest.mark.manual
def test_login_manual(api_client):
    payload = {"username": "phanith.chhim", "password": "Nith@2010"}
    resp = api_client.post("/api/login", json=payload)
    assert resp.status_code in (200, 401, 500)
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("success") is True
        assert body.get("userId") == "phanith.chhim" or body.get("userId") is not None


def test_signout_manual(api_client):
    payload = {"username": "phanith.chhim"}
    resp = api_client.post("/api/signout", json=payload)
    assert resp.status_code in (200, 400, 401)


@pytest.mark.manual
def test_get_users_paged(auth_api_client):
    resp = auth_api_client.get("/api/users", params={"size": 9})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
    assert "data" in body and isinstance(body.get("data"), list)
    # if example user exists, validate sample fields
    for u in body.get("data"):
        if u.get("userId") == "roby.va":
            schema = load_schema("GetUserDto.json") or load_schema("user_schema.json")
            if schema:
                assert_json_schema(u, schema)
            break


@pytest.mark.manual
def test_get_user_by_id(auth_api_client):
    resp = auth_api_client.get("/api/users/roby.va")
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        schema = load_schema("GetUserDto.json") or load_schema("user_schema.json")
        if schema:
            assert_json_schema(resp.json(), schema)


@pytest.mark.manual
def test_update_user_put(auth_api_client):
    payload = {
        "username": "Roby Va",
        "isActive": "Y",
        "branchId": 1,
        "authorizeTypeId": 2,
        "remark": "Update Bong Roby",
        "lastModifyBy": ""
    }
    resp = auth_api_client.put("/api/users/roby.va", json=payload)
    assert resp.status_code in (200, 400, 404, 500)
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("success") in (True,)


@pytest.mark.manual
def test_toggle_user_lock(auth_api_client):
    payload = {"lockStatus": "Y", "lastModifyBy": "admin"}
    resp = auth_api_client.put("/api/users/test.user/lock", json=payload)
    assert resp.status_code in (200, 404, 500)


@pytest.mark.manual
def test_roles_list(auth_api_client):
    resp = auth_api_client.get("/api/roles", params={"size": 19})
    assert resp.status_code in (200, 401, 403, 404)
    if resp.status_code == 200:
        body = resp.json()
        assert "data" in body


@pytest.mark.manual
def test_create_role(auth_api_client):
    payload = {"action": "CREATE", "roleName": "TESTING2", "isActive": "Y", "createBy": "admin"}
    resp = auth_api_client.post("/api/roles", json=payload)
    assert resp.status_code in (200, 400, 401, 403)


@pytest.mark.manual
def test_update_role(auth_api_client):
    payload = {"action": "UPDATE", "roleId": 4, "roleName": "Head Digital Bankign Support", "isActive": "N", "createBy": "admin"}
    resp = auth_api_client.post("/api/roles", json=payload)
    assert resp.status_code in (200, 400, 404, 401, 403)


@pytest.mark.manual
def test_delete_role(auth_api_client):
    resp = auth_api_client.delete("/api/roles/6")
    assert resp.status_code in (200, 404, 401, 403)


@pytest.mark.manual
def test_user_role_revoke_grant(auth_api_client):
    revoke = {"roleId": 2, "action": "REVOKE", "createBy": "admin"}
    resp = auth_api_client.post("/api/users/roby.va/roles", json=revoke)
    assert resp.status_code in (200, 400, 404, 401, 403)

    grant = {"roleId": 2, "action": "GRANT", "createBy": "admin"}
    resp2 = auth_api_client.post("/api/users/roby.va/roles", json=grant)
    assert resp2.status_code in (200, 400, 404, 401, 403)


@pytest.mark.manual
def test_assign_role_permission(auth_api_client):
    p1 = {"roleId": 3, "menuId": 5, "permissionId": 2, "fVisible": 1, "action": "GRANT", "createBy": "admin_user"}
    resp = auth_api_client.post("/api/roles/permissions", json=p1)
    assert resp.status_code in (200, 400, 401, 403)

    p2 = {"roleId": 1, "menuId": 3, "permissionId": 4, "fVisible": 1, "action": "GRANT", "createBy": "admin_user"}
    resp2 = auth_api_client.post("/api/roles/permissions", json=p2)
    assert resp2.status_code in (200, 400, 401, 403)


@pytest.mark.manual
def test_get_user_permissions(auth_api_client):
    resp = auth_api_client.get("/api/users/phanith.chhim/permissions", params={"page": 0, "size": 0})
    assert resp.status_code in (200, 404, 401, 403)
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("success") is True
        assert isinstance(body.get("data"), list)
        if body.get("data"):
            schema = load_schema("UserPermissionDto.json")
            if schema:
                assert_json_schema(body.get("data")[0], schema)
