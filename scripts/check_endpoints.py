#!/usr/bin/env python3
"""Check common API endpoints and print HTTP status + response body.

Usage: python scripts/check_endpoints.py [-u USER] [-p PASS] [--base-url URL]
"""
import argparse
import os
import sys
import json
from textwrap import shorten
import glob
import xml.etree.ElementTree as ET

try:
    import requests
except Exception:
    print("The 'requests' library is required. Install with: pip install requests")
    sys.exit(1)
try:
    from utils import schema_loader
except Exception:
    schema_loader = None
try:
    from jsonschema import validate as jsonschema_validate, ValidationError
except Exception:
    jsonschema_validate = None
    ValidationError = Exception


ENDPOINTS = [
    ("GET", "/api/hello"),
    ("GET", "/api/debug/ip"),
    ("GET", "/api/users"),
    ("GET", "/api/users/phanith.chhim"),
    ("GET", "/api/users/phanith.chhim/permissions"),
    ("GET", "/api/roles"),
    ("GET", "/api/roles/permissions/1"),
]

# map endpoints to expected schema filenames (optional). Keys are tuples (METHOD, PATH)
# If path contains variables use placeholder like /api/users/{id}
SCHEMA_MAP = {
    ("GET", "/api/hello"): "HelloResponse.json",
    ("GET", "/api/users"): "GetUsersRequest.json",
    ("GET", "/api/users/{id}"): "GetUserDto.json",
    ("GET", "/api/users/{id}/permissions"): "UserPermissionDto.json",
    ("GET", "/api/roles"): "role_schema.json",
    ("POST", "/api/login"): "LoginResponse.json",
}

# For list endpoints that return {"data": [...] }, validate each item against ITEM_SCHEMA_MAP
ITEM_SCHEMA_MAP = {
    ("GET", "/api/users"): "GetUserDto.json",
    ("GET", "/api/roles"): "RoleDto.json",
    ("GET", "/api/users/{id}/permissions"): "UserPermissionDto.json",
}


def pretty_print_resp(r):
    try:
        body = r.json()
        body_str = json.dumps(body, indent=2)
    except Exception:
        body_str = r.text or "<empty>"
    print(f"HTTP {r.status_code}")
    print(shorten(body_str, 2000))


def do_req(session, method, url, json_body=None):
    try:
        if method == "GET":
            r = session.get(url, timeout=5)
        elif method == "POST":
            r = session.post(url, json=json_body, timeout=5)
        else:
            r = session.request(method, url, timeout=5)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    # return minimal structured result
    result = {"ok": True, "status_code": r.status_code}
    try:
        result["body"] = r.json()
    except Exception:
        result["body_text"] = r.text or ""
    result["raw_resp"] = r
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-u", "--user", help="username for login/signout")
    p.add_argument("-p", "--pass", dest="passwd", help="password for login")
    p.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:8000"))
    p.add_argument("-v", "--verbose", action="store_true", help="Always print response bodies (default: only failures)")
    p.add_argument("--strict", action="store_true", help="Exit non-zero if any schema validation fails")
    p.add_argument("--latest-report", action="store_true", help="Print the latest generated report and exit")
    args = p.parse_args()

    # --latest-report: print latest JSON report and exit
    if args.latest_report:
        rpt_dir = os.path.join(os.getcwd(), "reports")
        if not os.path.isdir(rpt_dir):
            print("No reports directory found")
            sys.exit(0)
        files = sorted(glob.glob(os.path.join(rpt_dir, "check_endpoints_*.json")), reverse=True)
        if not files:
            print("No report files found")
            sys.exit(0)
        latest = files[0]
        with open(latest) as f:
            print(f.read())
        sys.exit(0)

    base = args.base_url.rstrip("/")
    # use retry-capable session from utils.http
    try:
        from utils.http import get_session_with_retries
        sess = get_session_with_retries()
    except Exception:
        sess = requests.Session()

    report = {"base_url": base, "results": [], "summary": {} }
    failures = []
    schema_failures = 0

    def print_ok(msg):
        GREEN = "\033[92m"
        RESET = "\033[0m"
        print(f"{GREEN}{msg}{RESET}")

    def print_fail(msg):
        RED = "\033[91m"
        RESET = "\033[0m"
        print(f"{RED}{msg}{RESET}")

    def print_body(entry):
        # prefer structured JSON body
        try:
            if "body" in entry and entry["body"] is not None:
                print(json.dumps(entry["body"], indent=2))
            elif "body_text" in entry:
                print(entry["body_text"])
        except Exception:
            # fallback safe print
            try:
                print(str(entry.get("body") or entry.get("body_text") or "<no body>"))
            except Exception:
                print("<unprintable body>")

    def header_line(method, path, status_code, ok):
        GREEN = "\033[92m"
        RED = "\033[91m"
        RESET = "\033[0m"
        badge = f"[{ 'OK' if ok else 'FAIL' }]"
        color = GREEN if ok else RED
        return f"{color}{badge} {method} {path} - HTTP {status_code}{RESET}"

    tools_available = (schema_loader is not None and jsonschema_validate is not None)
    if not tools_available:
        print_fail("Schema validation disabled: missing jsonschema or schema loader")
    print(f"Checking endpoints at {base}\n")
    success_count = 0
    fail_count = 0
    # helper to find schema for a path, supports simple {id} placeholders
    def find_schema_for(method, path):
        # exact match
        key = (method, path)
        if key in SCHEMA_MAP:
            return SCHEMA_MAP[key]
        # try pattern matches
        for (m, ptn), schema_name in SCHEMA_MAP.items():
            if m != method:
                continue
            # simple placeholder match: replace {id} with wildcard
            ptn_parts = ptn.split('/')
            path_parts = path.split('/')
            if len(ptn_parts) != len(path_parts):
                continue
            ok = True
            for a, b in zip(ptn_parts, path_parts):
                if a.startswith('{') and a.endswith('}'):
                    continue
                if a != b:
                    ok = False
                    break
            if ok:
                return schema_name
        return None

    for method, path in ENDPOINTS:
        full_url = f"{base}{path}"
        res = do_req(sess, method, full_url)
        entry = {"method": method, "path": path, "url": full_url}
        if not res:
            print_fail(header_line(method, path, "-", False))
            entry["ok"] = False
            entry["error"] = "request_failed"
            report["results"].append(entry)
            fail_count += 1
            failures.append({"method": method, "path": path, "reason": "request_failed"})
            continue
        entry.update({k: v for k, v in res.items() if k != "raw_resp"})
        status = res.get("status_code")
        # basic success criteria: 200-299
        if status and 200 <= status < 300:
            print_ok(header_line(method, path, status, True))
            entry["ok"] = True
            success_count += 1
            # print JSON response on success only if verbose
            if args.verbose:
                print_body(entry)
        else:
            print_fail(header_line(method, path, status, False))
            entry["ok"] = False
            fail_count += 1
            # print JSON or text response on failure
            print_body(entry)
            failures.append({"method": method, "path": path, "reason": f"http_{status}"})

        # try schema validation if available
        schema_name = find_schema_for(method, path)
        # prepare body for validation attempts
        body = entry.get("body")
        if body is None:
            try:
                body = json.loads(entry.get("body_text", "{}"))
            except Exception:
                body = None

        if schema_name and tools_available:
            schema = schema_loader.load_schema(schema_name)
            if schema is None:
                entry["schema"] = {"name": schema_name, "found": False}
            else:
                entry["schema"] = {"name": schema_name, "found": True}
                try:
                    if body is None:
                        # If the schema expects a plain string, validate against the raw text body
                        if entry.get("body_text") is not None and isinstance(schema, dict) and (
                            schema.get("type") == "string" or (
                                isinstance(schema.get("type"), list) and "string" in schema.get("type")
                            )
                        ):
                            try:
                                jsonschema_validate(instance=entry.get("body_text"), schema=schema)
                                entry["schema"]["valid"] = True
                                print_ok(f"Schema {schema_name} OK (validated against plain-text body)")
                            except ValidationError as e:
                                entry["schema"]["valid"] = False
                                entry["schema"]["error"] = str(e)
                                print_fail(f"Schema {schema_name} FAILED: {e}")
                                print_body(entry)
                        else:
                            entry["schema"]["valid"] = False
                            entry["schema"]["error"] = "no_json_body"
                            print_fail("Response has no JSON body for schema validation")
                    else:
                        # if response is a wrapper with data list, validate items if we have an item schema
                        if isinstance(body, dict) and isinstance(body.get("data"), list):
                            # try exact mapping then generic fallback
                            item_schema_name = ITEM_SCHEMA_MAP.get((method, path)) or ITEM_SCHEMA_MAP.get((method, path.split('/')[0]))
                            # fallback: derive item schema from request schema name if possible
                            if not item_schema_name and schema_name and schema_name.lower().endswith('request.json'):
                                item_schema_guess = schema_name.replace('Request.json', 'Dto.json')
                                if schema_loader.load_schema(item_schema_guess):
                                    item_schema_name = item_schema_guess

                            if item_schema_name:
                                item_schema = schema_loader.load_schema(item_schema_name)
                                item_results = []
                                all_ok = True
                                for idx, item in enumerate(body.get('data', [])):
                                    try:
                                        jsonschema_validate(instance=item, schema=item_schema)
                                        item_results.append({"index": idx, "ok": True})
                                    except ValidationError as ie:
                                        item_results.append({"index": idx, "ok": False, "error": str(ie)})
                                        all_ok = False
                                entry['schema']['item_schema'] = item_schema_name
                                entry['schema']['items'] = item_results
                                if all_ok:
                                    entry["schema"]["valid"] = True
                                    print_ok(f"All items validate against {item_schema_name}")
                                else:
                                    entry["schema"]["valid"] = False
                                    print_fail(f"Some items failed validation against {item_schema_name}")
                                    for it in item_results:
                                        if not it.get('ok'):
                                            print_fail(f" item[{it['index']}] error: {it.get('error')}")
                            else:
                                # no item schema known, validate wrapper directly
                                jsonschema_validate(instance=body, schema=schema)
                                entry["schema"]["valid"] = True
                                print_ok(f"Schema {schema_name} OK")
                        else:
                            jsonschema_validate(instance=body, schema=schema)
                            entry["schema"]["valid"] = True
                            print_ok(f"Schema {schema_name} OK")
                except ValidationError as e:
                    entry["schema"]["valid"] = False
                    entry["schema"]["error"] = str(e)
                    print_fail(f"Schema {schema_name} FAILED: {e}")
                    print_body(entry)

        # fallback: if no mapped schema or mapped schema failed, try all schemas
        if tools_available and (not entry.get("schema") or not entry["schema"].get("valid")):
            try:
                schema_dir = os.path.join(os.path.dirname(schema_loader.__file__), "schemas")
                matches = []
                if os.path.isdir(schema_dir):
                    for fname in os.listdir(schema_dir):
                        if not fname.lower().endswith('.json'):
                            continue
                        try:
                            s = schema_loader.load_schema(fname)
                            if s is None:
                                continue
                            if body is None:
                                continue
                            try:
                                jsonschema_validate(instance=body, schema=s)
                                matches.append(fname)
                            except ValidationError:
                                continue
                        except Exception:
                            continue
                if matches:
                    # choose the first match to avoid noisy multiple matches
                    entry.setdefault("schema", {})["fallback_match"] = matches[0]
                    entry["schema"]["valid"] = True
                    print_ok(f"Response matches schema: {matches[0]} (first match)")
                else:
                    entry.setdefault("schema", {})
                    if not entry["schema"].get("valid"):
                        entry["schema"].setdefault("fallback_matches", [])
                        entry["schema"]["valid"] = False
                        if not entry["schema"].get("error"):
                            entry["schema"]["error"] = "no_matching_schema"
                        print_fail("No schema matched the response")
                        if args.verbose:
                            print_body(entry)
                        failures.append({"method": method, "path": path, "reason": "no_matching_schema"})
                        schema_failures += 1
            except Exception as e:
                entry.setdefault("schema", {})["error"] = f"schema_search_failed: {e}"
                print_fail(f"Schema search failed: {e}")
        elif schema_name:
            entry["schema"] = {"name": schema_name, "available_tools": False}
            print_fail("Schema present but schema validation tools unavailable")

        print()
        report["results"].append(entry)

    # login/signout flow
    login_payload = {"username": args.user or "phanith.chhim", "password": args.passwd or "Nith@2010"}
    print("==> POST /api/login")
    res = do_req(sess, "POST", f"{base}/api/login", json_body=login_payload)
    entry = {"method": "POST", "path": "/api/login", "url": f"{base}/api/login"}
    if not res:
        print_fail("Login request failed")
        entry["ok"] = False
        entry["error"] = "login_failed"
        report["results"].append(entry)
    else:
        entry.update({k: v for k, v in res.items() if k != "raw_resp"})
        status = res.get("status_code")
        if status and 200 <= status < 300:
            print_ok(f"HTTP {status} OK")
            entry["ok"] = True
            print_body(entry)
        else:
            print_fail(f"HTTP {status} FAIL")
            entry["ok"] = False
            print_body(entry)
        # validate login response schema if present
        schema_name = SCHEMA_MAP.get(("POST", "/api/login"))
        if schema_name and schema_loader and jsonschema_validate:
            schema = schema_loader.load_schema(schema_name)
            if schema:
                try:
                    body = entry.get("body")
                    jsonschema_validate(instance=body or {}, schema=schema)
                    print_ok(f"Schema {schema_name} OK")
                    entry.setdefault("schema", {})["valid"] = True
                except ValidationError as e:
                    print_fail(f"Schema {schema_name} FAILED: {e}")
                    entry.setdefault("schema", {})["valid"] = False
                    entry["schema"]["error"] = str(e)
        report["results"].append(entry)

    print("== Summary ==")
    print_ok(f"Success: {success_count}")
    if fail_count:
        print_fail(f"Failure: {fail_count}")
    # compact failures list
    if failures:
        print() 
        print("Failures:")
        for f in failures:
            print_fail(f" - {f['method']} {f['path']}: {f['reason']}")
    report["summary"] = {"success": success_count, "failure": fail_count}

    # write report
    os.makedirs("reports", exist_ok=True)
    import datetime
    fn = f"reports/check_endpoints_{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    try:
        with open(fn, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Report written to {fn}")
    except Exception as e:
        print_fail(f"Failed to write report: {e}")

    # also write a simple JUnit XML report for CI
    try:
        testsuite = ET.Element('testsuite', name='check_endpoints', tests=str(len(report['results'])))
        for e in report['results']:
            tc_name = f"{e.get('method')} {e.get('path')}"
            tc = ET.SubElement(testsuite, 'testcase', classname='check_endpoints', name=tc_name)
            # mark failure on HTTP error or schema invalid
            if not e.get('ok'):
                failure = ET.SubElement(tc, 'failure', message=e.get('error', 'http_error'))
                failure.text = json.dumps(e.get('body') or e.get('body_text') or {})
            else:
                schema = e.get('schema') or {}
                if schema and schema.get('valid') is False:
                    failure = ET.SubElement(tc, 'failure', message=schema.get('error', 'schema_validation_failed'))
                    failure.text = json.dumps(schema)
        tree = ET.ElementTree(testsuite)
        junit_fn = fn.replace('.json', '.xml').replace('check_endpoints_', 'check_endpoints_junit_')
        tree.write(junit_fn, encoding='utf-8', xml_declaration=True)
        print(f"JUnit report written to {junit_fn}")
    except Exception as e:
        print_fail(f"Failed to write JUnit report: {e}")

    # honor --strict: non-zero exit if any schema failures were recorded
    if args.strict:
        if schema_failures > 0:
            print_fail(f"Strict mode: {schema_failures} schema failures detected — exiting non-zero")
            sys.exit(2)
        else:
            print_ok("Strict mode: no schema failures detected")


if __name__ == "__main__":
    main()
