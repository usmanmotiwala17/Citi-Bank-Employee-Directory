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

ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_ID = "robert.chen@acme.com", "adminpass123", 1
BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD, BANKING_MANAGER_ID = "sarah.johnson@acme.com", "managerpass123", 3
TECH_MANAGER_EMAIL, TECH_MANAGER_PASSWORD, TECH_MANAGER_ID = "emily.davis@acme.com", "managerpass123", 4
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

def test_login_admin():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    return token is not None


def test_admin_sees_all_employees():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, body = call("GET", "/employees", token=token)
    return status == 200 and isinstance(body, list) and len(body) == 17


def test_all_roles_see_company_wide_directory():
    """Viewing is company-wide for every role now - only managing is scoped
    (see test_employee_cannot_edit_another_employee /
    test_manager_cannot_edit_employee_in_other_department below)."""
    for email, password in (
        (ADMIN_EMAIL, ADMIN_PASSWORD),
        (BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD),
        (BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD),
    ):
        token = login(email, password)
        status, body = call("GET", "/employees", token=token)
        department_ids = {row["department_id"] for row in body if row["department_id"] is not None}
        if status != 200 or len(department_ids) < 2:
            return False
    return True


def test_employee_can_view_another_employee():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, _ = call("GET", f"/employees/{TECH_EMPLOYEE_ID}", token=token)
    return status == 200


def test_manager_can_view_employee_in_other_department():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("GET", f"/employees/{TECH_EMPLOYEE_ID}", token=token)
    return status == 200


def test_manager_can_view_own_department_employee():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=token)
    return status == 200


def test_manager_can_edit_direct_report_contact_fields():
    """A manager can edit phone/email/is_active - but only these - for
    someone whose manager_id actually points at them."""
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call(
        "PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token,
        body={"phone": "555-3000", "email": "carol.white@acme.com", "is_active": True},
    )
    return status == 200


def test_manager_can_edit_own_phone_directly():
    """Unlike an Employee, a Manager can edit their own phone straight
    through PUT /employees/:id - no change-request/approval needed."""
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, body = call("PUT", f"/employees/{BANKING_MANAGER_ID}", token=token, body={"phone": "212-555-8000"})
    return status == 200 and body.get("phone") == "212-555-8000"


def test_manager_cannot_edit_job_title_of_direct_report():
    """job_title is no longer manager-editable - only phone/email/is_active
    (and manager_notes, via its own separate rule) are."""
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token, body={"job_title": "Should Fail"})
    return status == 403


def test_manager_cannot_reassign_department():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=token, body={"department_id": 2})
    return status == 403


def test_employee_cannot_edit_another_employee():
    """Viewing another employee is allowed; editing them is not."""
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, _ = call("PUT", f"/employees/{TECH_EMPLOYEE_ID}", token=token, body={"job_title": "Should Fail"})
    return status == 403


def test_manager_cannot_edit_employee_who_is_not_their_direct_report():
    """Steven Lewis reports to Emily Davis, not Sarah Johnson - even though
    a department-based rule might have let Sarah in before, Sarah gets no
    edit access at all here, not even a field (phone) she'd normally be
    allowed to touch on her own direct reports."""
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("PUT", f"/employees/{TECH_EMPLOYEE_ID}", token=token, body={"phone": "555-0000"})
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


def test_admin_can_create_with_department():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
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


def test_admin_cannot_create_admin_with_department():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "Bad",
            "last_name": "Admin",
            "email": "bad-admin-test@acme.com",
            "password": "whatever123",
            "role": "ADMIN",
            "department_id": 1,
        },
    )
    return status == 400


def test_directory_tree_admin_only():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call("GET", "/directory-tree", token=token)
    return status == 200


def test_directory_tree_forbidden_for_manager():
    token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call("GET", "/directory-tree", token=token)
    return status == 403


def test_create_department():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call(
        "POST", "/departments", token=token,
        body={"name": "Wealth Management", "description": "Investment advisory and wealth planning services"},
    )
    return status == 201


def test_list_departments():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call("GET", "/departments", token=token)
    return status == 200


def test_non_admin_cannot_create_department():
    token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status, _ = call("POST", "/departments", token=token, body={"name": "Should Fail"})
    return status == 403


# ---------------------------------------------------------------------------
# Single active Admin
# ---------------------------------------------------------------------------

def test_admin_cannot_create_second_admin():
    token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    status, _ = call(
        "POST", "/employees", token=token,
        body={
            "first_name": "Second",
            "last_name": "Admin",
            "email": "second-admin-test@acme.com",
            "password": "whatever123",
            "role": "ADMIN",
        },
    )
    return status == 400


# ---------------------------------------------------------------------------
# manager_notes - private to Admin/direct manager, and org-structure links
# ---------------------------------------------------------------------------

def test_employee_never_sees_own_manager_notes():
    manager_token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    call(
        "PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=manager_token,
        body={"manager_notes": "Test note from manager"},
    )

    employee_token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    _, self_view = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=employee_token)
    _, self_list = call("GET", "/employees", token=employee_token)

    return "manager_notes" not in self_view and "manager_notes" not in self_list[0]


def test_manager_can_write_and_read_report_manager_notes():
    manager_token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, _ = call(
        "PUT", f"/employees/{BANKING_EMPLOYEE_ID}", token=manager_token,
        body={"manager_notes": "Strong performer, ready for more responsibility."},
    )
    if status != 200:
        return False

    _, body = call("GET", f"/employees/{BANKING_EMPLOYEE_ID}", token=manager_token)
    return body.get("manager_notes") == "Strong performer, ready for more responsibility."


def test_employee_can_view_any_manager_but_never_sees_manager_notes():
    employee_token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    status_own, own_manager = call("GET", f"/employees/{BANKING_MANAGER_ID}", token=employee_token)

    tech_employee_token = login(TECH_EMPLOYEE_EMAIL, TECH_EMPLOYEE_PASSWORD)
    status_unrelated, unrelated_manager = call("GET", f"/employees/{BANKING_MANAGER_ID}", token=tech_employee_token)

    return (
        status_own == 200
        and "manager_notes" not in own_manager
        and own_manager.get("direct_reports") is not None
        and status_unrelated == 200
        and "manager_notes" not in unrelated_manager
    )


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


def test_manager_change_request_list_scoped_to_direct_reports():
    """Sarah manages Carol (Banking) but not Steven (Tech, reports to
    Emily) - Sarah's pending-requests list should include Carol's request
    and never Steven's, even though older code scoped this by department."""
    carol_token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    _, carol_request = call(
        "POST", "/change-requests", token=carol_token, body={"field": "phone", "value": "212-555-7001"},
    )

    steven_token = login(TECH_EMPLOYEE_EMAIL, TECH_EMPLOYEE_PASSWORD)
    _, steven_request = call(
        "POST", "/change-requests", token=steven_token, body={"field": "phone", "value": "813-555-7002"},
    )

    manager_token = login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD)
    status, requests = call("GET", "/change-requests", token=manager_token)
    request_ids = {r["id"] for r in requests}

    # Clean up Steven's leftover pending request so it doesn't linger for
    # other tests/manual poking around - Emily is the one who can act on it.
    call("PUT", f"/change-requests/{steven_request['id']}", token=login(TECH_MANAGER_EMAIL, TECH_MANAGER_PASSWORD), body={"status": "rejected"})

    return status == 200 and carol_request["id"] in request_ids and steven_request["id"] not in request_ids


def test_manager_cannot_approve_unrelated_employees_request():
    """Even with a valid request id in hand, an unrelated manager can't
    approve/reject it - this isn't just a UI-hidden list, it's enforced on
    the PUT itself."""
    carol_token = login(BANKING_EMPLOYEE_EMAIL, BANKING_EMPLOYEE_PASSWORD)
    _, created = call(
        "POST", "/change-requests", token=carol_token, body={"field": "phone", "value": "212-555-7003"},
    )

    tech_manager_token = login(TECH_MANAGER_EMAIL, TECH_MANAGER_PASSWORD)
    status, _ = call(
        "PUT", f"/change-requests/{created['id']}", token=tech_manager_token, body={"status": "approved"},
    )

    # Clean up with the actual manager so the request doesn't stay pending.
    call("PUT", f"/change-requests/{created['id']}", token=login(BANKING_MANAGER_EMAIL, BANKING_MANAGER_PASSWORD), body={"status": "rejected"})

    return status == 403


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
    test_login_admin,
    test_admin_sees_all_employees,
    test_all_roles_see_company_wide_directory,
    test_employee_can_view_another_employee,
    test_manager_can_view_employee_in_other_department,
    test_manager_can_view_own_department_employee,
    test_manager_can_edit_direct_report_contact_fields,
    test_manager_can_edit_own_phone_directly,
    test_manager_cannot_edit_job_title_of_direct_report,
    test_manager_cannot_reassign_department,
    test_employee_cannot_edit_another_employee,
    test_manager_cannot_edit_employee_who_is_not_their_direct_report,
    test_employee_cannot_create,
    test_manager_cannot_create,
    test_admin_can_create_with_department,
    test_admin_cannot_create_admin_with_department,
    test_directory_tree_admin_only,
    test_directory_tree_forbidden_for_manager,
    test_create_department,
    test_list_departments,
    test_non_admin_cannot_create_department,
    test_admin_cannot_create_second_admin,
    test_employee_never_sees_own_manager_notes,
    test_manager_can_write_and_read_report_manager_notes,
    test_employee_can_view_any_manager_but_never_sees_manager_notes,
    test_employee_can_edit_only_skills,
    test_employee_can_submit_change_request,
    test_employee_cannot_view_change_requests,
    test_manager_approving_change_request_updates_phone,
    test_manager_change_request_list_scoped_to_direct_reports,
    test_manager_cannot_approve_unrelated_employees_request,
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
