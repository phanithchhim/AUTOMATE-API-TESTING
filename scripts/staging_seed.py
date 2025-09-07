"""
Idempotent staging seeding and teardown script.
Usage:
  python scripts/staging_seed.py        # seed
  python scripts/staging_seed.py --teardown   # teardown created resources

Requires env: STAGING_BASE_URL, STAGING_USERNAME, STAGING_PASSWORD
"""
import os
import sys
import json
import argparse
from utils.http import get_session_with_retries

# Optional helper; may not exist in older versions of utils.http
try:
    from utils.http import request_with_timeout_and_retry
except Exception:
    request_with_timeout_and_retry = None

BASE = os.environ.get("STAGING_BASE_URL")
USER = os.environ.get("STAGING_USERNAME")
PASS = os.environ.get("STAGING_PASSWORD")
PREFIX = os.environ.get("CI_TEST_PREFIX", "ci_test_")

if not BASE or not USER or not PASS:
    print("Missing STAGING_BASE_URL/STAGING_USERNAME/STAGING_PASSWORD environment variables", file=sys.stderr)
    sys.exit(2)

session = get_session_with_retries()

def _request(method, url, **kwargs):
    if request_with_timeout_and_retry:
        return request_with_timeout_and_retry(method, url, session=session, **kwargs)
    if 'timeout' not in kwargs:
        kwargs['timeout'] = 10
    return session.request(method=method, url=url, **kwargs)


def ensure_test_user(username):
    users_url = f"{BASE.rstrip('/')}/api/users"
    user_url = f"{users_url}/{username}"
    try:
        r = _request('GET', user_url)
        if r and getattr(r, 'status_code', None) == 200:
            print(f"User {username} exists, skipping create")
            return True
    except Exception:
        pass
    payload = {"username": username, "displayName": username, "email": f"{username}@example.invalid"}
    r2 = _request('POST', users_url, json=payload)
    print('create user', getattr(r2, 'status_code', 'err'), getattr(r2, 'text', ''))
    return getattr(r2, 'status_code', None) in (200, 201)


def ensure_test_role(role_name):
    roles_url = f"{BASE.rstrip('/')}/api/roles"
    try:
        r = _request('GET', roles_url)
        if r and getattr(r, 'status_code', None) == 200:
            try:
                data = r.json()
                for item in data.get('data', []):
                    if item.get('roleName') == role_name:
                        print(f"Role {role_name} exists")
                        return True
            except Exception:
                pass
    except Exception:
        pass
    payload = {'roleName': role_name}
    r2 = _request('POST', roles_url, json=payload)
    print('create role', getattr(r2, 'status_code', 'err'))
    return getattr(r2, 'status_code', None) in (200, 201)


def ensure_test_permission(perm_name):
    perms_url = f"{BASE.rstrip('/')}/api/permissions"
    try:
        p = _request('GET', perms_url)
        if p and getattr(p, 'status_code', None) == 200:
            try:
                pdata = p.json()
                for item in pdata.get('data', []):
                    if item.get('name') == perm_name:
                        print(f"Permission {perm_name} exists")
                        return True
            except Exception:
                pass
    except Exception:
        pass
    try:
        pr = _request('POST', perms_url, json={'name': perm_name})
        print('create perm', getattr(pr, 'status_code', 'err'))
        return getattr(pr, 'status_code', None) in (200, 201)
    except Exception:
        return False


def delete_test_user(username):
    url = f"{BASE.rstrip('/')}/api/users/{username}"
    try:
        r = session.request('DELETE', url, timeout=10)
        print(f"DELETE {url} -> {r.status_code}")
        return r.status_code in (200, 204, 404)
    except Exception as e:
        print('delete user error', e)
        return False


def delete_test_role(role_name):
    roles_url = f"{BASE.rstrip('/')}/api/roles"
    try:
        r = session.request('GET', roles_url, timeout=10)
        if r and getattr(r, 'status_code', None) == 200:
            try:
                data = r.json()
                for item in data.get('data', []):
                    if item.get('roleName') == role_name:
                        rid = item.get('roleId') or item.get('id')
                        if rid:
                            durl = f"{roles_url}/{rid}"
                            dr = session.request('DELETE', durl, timeout=10)
                            print(f"DELETE {durl} -> {dr.status_code}")
                            return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def delete_test_permission(perm_name):
    perms_url = f"{BASE.rstrip('/')}/api/permissions"
    try:
        r = session.request('GET', perms_url, timeout=10)
        if r and getattr(r, 'status_code', None) == 200:
            try:
                data = r.json()
                for item in data.get('data', []):
                    if item.get('name') == perm_name:
                        pid = item.get('permissionId') or item.get('id')
                        if pid:
                            durl = f"{perms_url}/{pid}"
                            dr = session.request('DELETE', durl, timeout=10)
                            print(f"DELETE {durl} -> {dr.status_code}")
                            return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--teardown', action='store_true', help='Delete seeded resources instead of creating')
    args = p.parse_args()

    if args.teardown:
        print('Running teardown...')
        test_user = PREFIX + 'user'
        delete_test_user(test_user)
        delete_test_role(PREFIX + 'role')
        delete_test_permission(PREFIX + 'perm')
        print('Teardown completed')
        return 0

    test_user = PREFIX + 'user'
    ok = ensure_test_user(test_user)
    if not ok:
        print('Failed to ensure test user', file=sys.stderr)
        sys.exit(1)
    # ensure a test role exists
    ensure_test_role(PREFIX + 'role')
    # ensure a permission exists
    ensure_test_permission(PREFIX + 'perm')
    print('Seeding completed')
    print(json.dumps({'seeded_user': test_user}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
