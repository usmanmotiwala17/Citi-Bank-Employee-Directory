"""
Manual smoke-test script for the Employee Directory service.

Not a pytest suite - just a readable set of functions you run directly
against your real local Postgres database (via start-dev.sh) to sanity
check that auth, RBAC, and the CRUD routes behave as expected.

Usage:
    python test_manual.py
"""

import json

from function import handler

# ---------------------------------------------------------------------------
# Seed data - adjust these to match whatever you actually seeded locally.
# ---------------------------------------------------------------------------

ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_ID = "admin@acme.com", "yourchosenpassword", 1
SARAH_EMAIL, SARAH_PASSWORD, SARAH_ID = "sarah@acme.com", "managerpass123", 2
CAROL_EMAIL, CAROL_PASSWORD, CAROL_ID = "carol@acme.com", "employeepass123", 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def call(method, path, token=None, body=None):
    """Builds a Lambda event, invokes handler(), pretty-prints the result."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    event = {
        "httpMethod": method,
        "path": path,
        "headers": headers,
        "body": json.dumps(body) if body is not None else None,
    }

    result = handler(event)
    status = result["statusCode"]

    try:
        parsed_body = json.loads(result["body"]) if result["body"] else None
    except (TypeError, ValueError):
        parsed_body = result["body"]

    print(f"  -> {method} {path}  [{status}]")
    print(f"     {json.dumps(parsed_body, indent=2)}")

    return status, parsed_body


def login(email, password):
    """Logs in and returns the access_token, or None if login failed."""
    status, body = call("POST", "/auth/login", body={"email": email, "password": password})
    if status != 200:
        print(f"     ! login failed for {email}")
        return None
    return body["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_login_admin():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    return token is not None


def test_hierarchy_violation():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "Bad",
            "last_name": "Hierarchy",
            "email": "hierarchy-test@acme.com",
            "password": "whatever123",
            "manager_id": ADMIN_ID,
        },
    )
    return status == 400


def test_directory_tree():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call("GET", "/directory-tree", token=token)
    return status == 200


def test_employee_cannot_create():
    token = login(CAROL_EMAIL, CAROL_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "Should",
            "last_name": "Fail",
            "email": "should-fail@acme.com",
            "password": "whatever123",
        },
    )
    return status == 403


def test_manager_can_view_own_report():
    token = login(SARAH_EMAIL, SARAH_PASSWORD)
    status, body = call("GET", f"/employees/{CAROL_ID}", token=token)
    has_full_detail = bool(body) and "bio" in body and "role" in body
    return status == 200 and has_full_detail


def test_manager_cannot_edit_others_report():
    token = login(SARAH_EMAIL, SARAH_PASSWORD)
    status, _ = call("PUT", f"/employees/{ADMIN_ID}", token=token, body={"job_title": "Hacked"})
    return status == 403


def test_get_employee_public_fields_only():
    token = login(CAROL_EMAIL, CAROL_PASSWORD)
    status, body = call("GET", f"/employees/{SARAH_ID}", token=token)
    fields_hidden = bool(body) and not any(f in body for f in ("bio", "role", "created_at"))
    return status == 200 and fields_hidden


def test_create_department():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call(
        "POST", "/departments", token=token,
        body={"name": "Engineering", "description": "Builds the product"},
    )
    return status == 201


def test_list_departments():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call("GET", "/departments", token=token)
    return status == 200


def test_non_admin_cannot_create_department():
    token = login(CAROL_EMAIL, CAROL_PASSWORD)
    status, _ = call("POST", "/departments", token=token, body={"name": "Should Fail"})
    return status == 403


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = (
    test_login_admin,
    test_hierarchy_violation,
    test_directory_tree,
    test_employee_cannot_create,
    test_manager_can_view_own_report,
    test_manager_cannot_edit_others_report,
    test_get_employee_public_fields_only,
    test_create_department,
    test_list_departments,
    test_non_admin_cannot_create_department,
)


if __name__ == "__main__":
    results = []

    for test in TESTS:
        print(f"\n=== {test.__name__} ===")
        try:
            passed = test()
        except Exception as e:
            print(f"     ! exception: {e}")
            passed = False
        results.append((test.__name__, passed))

    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    for name, passed in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    total = len(results)
    passed_count = sum(1 for _, passed in results if passed)
    print(f"\n{passed_count}/{total} passed")
