"""
Manual smoke-test script for the Employee Directory service.

Not a pytest suite - just a readable set of functions you run directly
against your real local Postgres database (via start-dev.sh) to sanity
check that auth, RBAC, and the CRUD routes behave as expected.

Run seed_data.py first so these accounts exist:
    python3 seed_data.py
    python3 test_manual.py
"""

import json

from function import handler

# ---------------------------------------------------------------------------
# Seed data - matches seed_data.py. Adjust the IDs if you seeded in a
# different order (IDs are assigned by Postgres in insertion order).
# ---------------------------------------------------------------------------

CEO_EMAIL, CEO_PASSWORD, CEO_ID = "robert.chen@acme.com", "ceopass123", 1
BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD, BANKING_MANAGER_ID = "sarah.johnson@acme.com", "managerpass123", 3
TECH_MANAGER_EMAIL, TECH_MANAGER_PASSWORD = "emily.davis@acme.com", "managerpass123"
BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD, BANKING_EMPLOYEE_ID = "carol.white@acme.com", "employeepass123", 7
TECH_EMPLOYEE_EMAIL, TECH_EMPLOYEE_PASSWORD, TECH_EMPLOYEE_ID = "steven.lewis@acme.com", "employeepass123", 11


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

def test_login_ceo():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    return token is not None


def test_ceo_sees_all_employees():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    status, body = call("GET", "/employees", token=token)
    return status == 200 and isinstance(body, list) and len(body) == 18


def test_manager_sees_only_own_department():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, body = call("GET", "/employees", token=token)
    all_same_department = bool(body) and all(row["department_id"] == body[0]["department_id"] for row in body)
    return status == 200 and all_same_department


def test_employee_sees_only_self():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, body = call("GET", "/employees", token=token)
    return status == 200 and isinstance(body, list) and len(body) == 1 and body[0]["email"] == BANKING_EMPLOYEE_EMAIL


def test_employee_cannot_view_another_employee():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, _ = call("GET", f"/employees/{TECH_EMPLOYEE_ID}", token=token)
    return status == 403


def test_manager_cannot_view_other_department():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("GET", f"/employees/{TECH_EMPLOYEE_ID}", token=token)
    return status == 403


def test_manager_can_view_own_department_employee():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=token)
    return status == 200


def test_manager_can_edit_own_department_employee():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token, body={"job_title": "Senior Financial Analyst"})
    return status == 200


def test_manager_cannot_reassign_department():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token, body={"department_id": 2})
    return status == 403


def test_employee_cannot_create():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
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


def test_manager_cannot_create():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "Should",
            "last_name": "Fail",
            "email": "should-fail-2@acme.com",
            "password": "whatever123",
        },
    )
    return status == 403


def test_ceo_can_create_with_department():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "New",
            "last_name": "Hire",
            "email": "new-hire-test@acme.com",
            "password": "whatever123",
            "role": "EMPLOYEE",
            "department_id": 1,
        },
    )
    return status == 201


def test_ceo_cannot_create_ceo_with_department():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "Bad",
            "last_name": "Ceo",
            "email": "bad-ceo-test@acme.com",
            "password": "whatever123",
            "role": "CEO",
            "department_id": 1,
        },
    )
    return status == 400


def test_directory_tree_ceo_only():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    status, _ = call("GET", "/directory-tree", token=token)
    return status == 200


def test_directory_tree_forbidden_for_manager():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("GET", "/directory-tree", token=token)
    return status == 403


def test_create_department():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    status, _ = call(
        "POST", "/departments", token=token,
        body={"name": "Wealth Management", "description": "Investment advisory and wealth planning services"},
    )
    return status == 201


def test_list_departments():
    token = login(CEO_EMAIL, CEO_PASSWORD)
    status, _ = call("GET", "/departments", token=token)
    return status == 200


def test_non_ceo_cannot_create_department():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, _ = call("POST", "/departments", token=token, body={"name": "Should Fail"})
    return status == 403


# ---------------------------------------------------------------------------
# Skills self-edit / change requests
# ---------------------------------------------------------------------------

def test_employee_can_edit_only_skills():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status_skills, _ = call(
        "PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token,
        body={"skills": ["Merchandising", "Customer Service"]},
    )
    status_phone, _ = call(
        "PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token, body={"phone": "555-0000"},
    )
    status_bio, _ = call(
        "PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token, body={"bio": "hacked"},
    )
    return status_skills == 200 and status_phone == 403 and status_bio == 403


def test_employee_can_submit_change_request():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, body = call(
        "POST", "/change-requests", token=token, body={"field": "phone", "value": "555-1234"},
    )
    return status == 201 and body.get("status") == "pending"


def test_employee_cannot_view_change_requests():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, _ = call("GET", "/change-requests", token=token)
    return status == 403


def test_manager_approving_change_request_updates_phone():
    employee_token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    _, created = call(
        "POST", "/change-requests", token=employee_token, body={"field": "phone", "value": "555-2000"},
    )

    manager_token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, body = call(
        "PUT", f"/change-requests/{created['id']}", token=manager_token, body={"status": "approved"},
    )
    if status != 200 or body.get("status") != "approved":
        return False

    _, updated_employee = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=manager_token)
    return updated_employee.get("phone") == "555-2000"


def test_manager_rejecting_change_request_leaves_employee_unchanged():
    manager_token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    _, before = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=manager_token)
    phone_before = before.get("phone")

    employee_token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    _, created = call(
        "POST", "/change-requests", token=employee_token, body={"field": "phone", "value": "555-9999"},
    )

    status, body = call(
        "PUT", f"/change-requests/{created['id']}", token=manager_token, body={"status": "rejected"},
    )
    if status != 200 or body.get("status") != "rejected":
        return False

    _, after = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=manager_token)
    return after.get("phone") == phone_before


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = (
    test_login_ceo,
    test_ceo_sees_all_employees,
    test_manager_sees_only_own_department,
    test_employee_sees_only_self,
    test_employee_cannot_view_another_employee,
    test_manager_cannot_view_other_department,
    test_manager_can_view_own_department_employee,
    test_manager_can_edit_own_department_employee,
    test_manager_cannot_reassign_department,
    test_employee_cannot_create,
    test_manager_cannot_create,
    test_ceo_can_create_with_department,
    test_ceo_cannot_create_ceo_with_department,
    test_directory_tree_ceo_only,
    test_directory_tree_forbidden_for_manager,
    test_create_department,
    test_list_departments,
    test_non_ceo_cannot_create_department,
    test_employee_can_edit_only_skills,
    test_employee_can_submit_change_request,
    test_employee_cannot_view_change_requests,
    test_manager_approving_change_request_updates_phone,
    test_manager_rejecting_change_request_leaves_employee_unchanged,
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
