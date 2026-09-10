"""
Employee Directory service - AWS Lambda entry point.

Routes incoming API Gateway events to the appropriate handler based on
httpMethod + path, enforcing JWT auth and role-based permissions before
touching the database.
"""

import json
import logging
import re

from psycopg.errors import UniqueViolation

import auth_service as auth
import postgres_service as db
from auth_service import AuthError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VALID_ROLES = db.VALID_ROLES

EMPLOYEE_FIELDS = (
    "id", "first_name", "last_name", "email", "phone",
    "job_title", "department_id", "manager_id", "is_active",
    "bio", "role", "created_at", "skills", "location",
)

CHANGE_REQUEST_FIELDS = ("phone",)


class ValidationError(Exception):
    """Raised for any 400-level input validation failure."""


class NotFoundError(Exception):
    """Raised when a referenced resource does not exist (404)."""


# ---------------------------------------------------------------------------
# Response / request helpers
# ---------------------------------------------------------------------------

def response(status_code, body=None):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str) if body is not None else "",
    }


def parse_body(event):
    raw = event.get("body")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        raise ValidationError("Request body must be valid JSON")
    if not isinstance(parsed, dict):
        raise ValidationError("Request body must be a JSON object")
    return parsed


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
#
# Unlike the old admin/manager/employee version, there's no "public directory"
# tier anymore: if you're not allowed to see someone (see _can_view below),
# you don't get a trimmed-down record - you get a 403. So serialization no
# longer needs to branch on the viewer; it's just a flat field selection.

def serialize_employee(employee_row):
    return {field: employee_row[field] for field in EMPLOYEE_FIELDS}


def serialize_department(department_row):
    return {"id": department_row["id"], "name": department_row["name"], "description": department_row["description"]}


def serialize_change_request(request_row, employee_row):
    return {
        "id": request_row["id"],
        "employee_id": request_row["employee_id"],
        "employee_name": f"{employee_row['first_name']} {employee_row['last_name']}",
        "department_id": employee_row["department_id"],
        "field": request_row["field_name"],
        "requested_value": request_row["requested_value"],
        "current_value": employee_row.get(request_row["field_name"]),
        "status": request_row["status"],
        "created_at": request_row["created_at"],
        "reviewed_by": request_row["reviewed_by"],
        "reviewed_at": request_row["reviewed_at"],
    }


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
#
# Role model (replaces the old admin/manager/employee hierarchy, which scoped
# a manager to their direct reports via manager_id):
#   CEO      - full access to every employee and department.
#   MANAGER  - can view/manage employees within their own department only.
#   EMPLOYEE - can view their own profile only.

def _can_view(viewer, employee_row):
    if viewer["role"] == "CEO":
        return True
    if viewer["id"] == employee_row["id"]:
        return True
    if viewer["role"] == "MANAGER" and employee_row["department_id"] == viewer["department_id"]:
        return True
    return False


def _can_manage(viewer, employee_row):
    """Manage = update/deactivate. Same rule as viewing, minus self-service
    (self-service is handled separately with a narrower set of fields)."""
    if viewer["role"] == "CEO":
        return True
    if viewer["role"] == "MANAGER" and employee_row["department_id"] == viewer["department_id"]:
        return True
    return False


# ---------------------------------------------------------------------------
# Department validation (CEO -> no department, MANAGER/EMPLOYEE -> required)
# ---------------------------------------------------------------------------

def validate_skills(value):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("skills must be a list of strings")
    return value


def validate_department(role, department_id):
    if role not in VALID_ROLES:
        raise ValidationError(f"role must be one of {', '.join(VALID_ROLES)}")

    if role == "CEO":
        if department_id is not None:
            raise ValidationError("A CEO has company-wide access and must not be assigned to a single department (department_id must be null)")
        return

    if department_id is None:
        raise ValidationError(f"A '{role}' must have a department_id set")
    if db.get_department_by_id(department_id) is None:
        raise ValidationError("department_id does not reference an existing department")


# ---------------------------------------------------------------------------
# manager_id validation - each department has exactly one manager, and
# manager_id is meant to record who an employee actually reports to, not
# just any employee id.
# ---------------------------------------------------------------------------

def validate_manager_id(role, department_id, manager_id):
    if manager_id is None:
        return

    if role == "CEO":
        raise ValidationError("A CEO does not report to a manager (manager_id must be null)")

    manager = db.get_employee_by_id(manager_id)
    if manager is None:
        raise ValidationError("manager_id does not reference an existing employee")
    if manager["role"] != "MANAGER":
        raise ValidationError("manager_id must reference an employee with role 'MANAGER'")
    if department_id is not None and manager["department_id"] != department_id:
        raise ValidationError("manager_id must reference the manager of the same department")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_route(event):
    body = parse_body(event)
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        raise ValidationError("email and password are required")

    employee = db.get_employee_by_email(email)
    if employee is None or not auth.verify_password(password, employee["hashed_password"]):
        raise AuthError("Invalid email or password", status_code=401)
    if not employee["is_active"]:
        raise AuthError("Account is inactive", status_code=401)

    token = auth.create_access_token(
        employee["id"], employee["role"], employee["department_id"], employee["token_version"]
    )
    return response(200, {
        "access_token": token,
        "token_type": "bearer",
        "employee": serialize_employee(employee),
    })


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

def create_employee_route(event, user):
    # Only the CEO can create new accounts - "manage within your department"
    # (MANAGER) covers viewing/editing/deactivating, not onboarding.
    auth.require_role(user, ["CEO"])
    body = parse_body(event)

    required_fields = ("first_name", "last_name", "email", "password")
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")

    email = body["email"].strip().lower()
    if "@" not in email:
        raise ValidationError("Invalid email address")

    role = body.get("role", "EMPLOYEE")
    department_id = body.get("department_id")
    validate_department(role, department_id)

    manager_id = body.get("manager_id")
    validate_manager_id(role, department_id, manager_id)

    is_active = body.get("is_active", True)
    if not isinstance(is_active, bool):
        raise ValidationError("is_active must be a boolean")

    data = {
        "first_name": body["first_name"],
        "last_name": body["last_name"],
        "email": email,
        "phone": body.get("phone"),
        "job_title": body.get("job_title"),
        "department_id": department_id,
        "manager_id": manager_id,
        "bio": body.get("bio"),
        "role": role,
        "is_active": is_active,
        "skills": validate_skills(body.get("skills")),
        "location": body.get("location"),
    }

    try:
        created = db.create_employee(data, auth.hash_password(body["password"]))
    except UniqueViolation:
        raise ValidationError("Email already in use")

    return response(201, serialize_employee(created))


def list_employees_route(event, user):
    if user["role"] == "CEO":
        rows = db.list_employees()
    elif user["role"] == "MANAGER":
        rows = db.list_employees_by_department(user["department_id"])
    else:  # EMPLOYEE - can only ever see themselves
        rows = [db.get_employee_by_id(user["id"])]
    return response(200, [serialize_employee(row) for row in rows])


def get_employee_route(event, user, employee_id):
    employee = db.get_employee_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    if not _can_view(user, employee):
        raise AuthError("Not permitted to view this employee", status_code=403)
    return response(200, serialize_employee(employee))


def update_employee_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    body = parse_body(event)
    if not body:
        raise ValidationError("Request body must include at least one field to update")

    # Determine which fields this actor is allowed to touch on this target.
    if user["role"] == "CEO":
        allowed_fields = {
            "first_name", "last_name", "email", "phone", "job_title",
            "department_id", "manager_id", "bio", "role", "is_active",
            "skills", "location",
        }
    elif user["id"] == target["id"]:
        allowed_fields = {"skills"}
    elif _can_manage(user, target):
        allowed_fields = {"job_title", "is_active"}
    else:
        raise AuthError("Not permitted to update this employee", status_code=403)

    disallowed = set(body.keys()) - allowed_fields
    if disallowed:
        raise AuthError(
            f"Not permitted to modify field(s): {', '.join(sorted(disallowed))}",
            status_code=403,
        )

    fields = {}
    if "first_name" in body:
        if not body["first_name"]:
            raise ValidationError("first_name cannot be empty")
        fields["first_name"] = body["first_name"]
    if "last_name" in body:
        if not body["last_name"]:
            raise ValidationError("last_name cannot be empty")
        fields["last_name"] = body["last_name"]
    if "email" in body:
        email = (body["email"] or "").strip().lower()
        if "@" not in email:
            raise ValidationError("Invalid email address")
        fields["email"] = email
    if "phone" in body:
        fields["phone"] = body["phone"]
    if "job_title" in body:
        fields["job_title"] = body["job_title"]
    if "bio" in body:
        fields["bio"] = body["bio"]
    if "is_active" in body:
        if not isinstance(body["is_active"], bool):
            raise ValidationError("is_active must be a boolean")
        fields["is_active"] = body["is_active"]
    if "department_id" in body:
        fields["department_id"] = body["department_id"]
    if "role" in body:
        fields["role"] = body["role"]
    if "manager_id" in body:
        fields["manager_id"] = body["manager_id"]
    if "skills" in body:
        fields["skills"] = validate_skills(body["skills"])
    if "location" in body:
        fields["location"] = body["location"]

    if not fields:
        raise ValidationError("No valid fields provided to update")

    # Re-validate department/manager rules whenever role, department_id, or
    # manager_id changes, merging with the target's current values for
    # whichever ones aren't changing - e.g. changing just the department
    # still needs to re-check that the existing manager_id still matches.
    if "role" in fields or "department_id" in fields or "manager_id" in fields:
        new_role = fields.get("role", target["role"])
        new_department_id = fields.get("department_id", target["department_id"])
        new_manager_id = fields.get("manager_id", target["manager_id"])
        validate_department(new_role, new_department_id)
        validate_manager_id(new_role, new_department_id, new_manager_id)

    try:
        updated = db.update_employee(target["id"], fields)
    except UniqueViolation:
        raise ValidationError("Email already in use")

    # A stale JWT would keep carrying the old role/department - invalidate it
    # immediately rather than waiting for it to expire.
    role_changed = "role" in fields and fields["role"] != target["role"]
    department_changed = "department_id" in fields and fields["department_id"] != target["department_id"]
    if role_changed or department_changed:
        db.bump_token_version(target["id"])

    return response(200, serialize_employee(updated))


def delete_employee_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    if not _can_manage(user, target):
        raise AuthError("Not permitted to deactivate this employee", status_code=403)

    db.deactivate_employee(employee_id)
    return response(204)


# ---------------------------------------------------------------------------
# Change requests
#
# Employees can't edit their own phone number directly (see allowed_fields
# above) - instead they submit a request here, and their manager/the CEO
# approves or rejects it. Approval is what actually updates the employee row.
# ---------------------------------------------------------------------------

def create_change_request_route(event, user):
    body = parse_body(event)
    field = body.get("field")
    value = body.get("value")
    if field not in CHANGE_REQUEST_FIELDS:
        raise ValidationError(f"field must be one of {', '.join(CHANGE_REQUEST_FIELDS)}")
    if not value:
        raise ValidationError("value is required")

    created = db.create_change_request(user["id"], field, value)
    employee = db.get_employee_by_id(user["id"])
    return response(201, serialize_change_request(created, employee))


def list_change_requests_route(event, user):
    auth.require_role(user, ["CEO", "MANAGER"])
    if user["role"] == "CEO":
        rows = db.list_pending_change_requests()
    else:
        rows = db.list_pending_change_requests_by_department(user["department_id"])

    results = []
    for row in rows:
        employee = db.get_employee_by_id(row["employee_id"])
        results.append(serialize_change_request(row, employee))
    return response(200, results)


def update_change_request_route(event, user, request_id):
    request_row = db.get_change_request_by_id(request_id)
    if request_row is None:
        raise NotFoundError("Change request not found")

    target = db.get_employee_by_id(request_row["employee_id"])
    if target is None:
        raise NotFoundError("Employee not found")
    if not _can_manage(user, target):
        raise AuthError("Not permitted to review this change request", status_code=403)
    if request_row["status"] != "pending":
        raise ValidationError("This change request has already been reviewed")

    body = parse_body(event)
    status = body.get("status")
    if status not in ("approved", "rejected"):
        raise ValidationError("status must be 'approved' or 'rejected'")

    if status == "approved":
        db.update_employee(target["id"], {request_row["field_name"]: request_row["requested_value"]})
        target = db.get_employee_by_id(target["id"])

    updated_request = db.update_change_request(request_id, status, user["id"])
    return response(200, serialize_change_request(updated_request, target))


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

def create_department_route(event, user):
    auth.require_role(user, ["CEO"])
    body = parse_body(event)
    name = (body.get("name") or "").strip()
    if not name:
        raise ValidationError("name is required")

    try:
        created = db.create_department(name, body.get("description"))
    except UniqueViolation:
        raise ValidationError("Department name already in use")

    return response(201, serialize_department(created))


def list_departments_route(event, user):
    rows = db.list_departments()
    return response(200, [serialize_department(row) for row in rows])


def get_department_route(event, user, department_id):
    department = db.get_department_by_id(department_id)
    if department is None:
        raise NotFoundError("Department not found")
    return response(200, serialize_department(department))


def update_department_route(event, user, department_id):
    auth.require_role(user, ["CEO"])
    existing = db.get_department_by_id(department_id)
    if existing is None:
        raise NotFoundError("Department not found")

    body = parse_body(event)
    fields = {}
    if "name" in body:
        name = (body["name"] or "").strip()
        if not name:
            raise ValidationError("name cannot be empty")
        fields["name"] = name
    if "description" in body:
        fields["description"] = body["description"]

    if not fields:
        raise ValidationError("No valid fields provided to update")

    try:
        updated = db.update_department(department_id, fields)
    except UniqueViolation:
        raise ValidationError("Department name already in use")

    return response(200, serialize_department(updated))


def delete_department_route(event, user, department_id):
    auth.require_role(user, ["CEO"])
    existing = db.get_department_by_id(department_id)
    if existing is None:
        raise NotFoundError("Department not found")

    db.delete_department(department_id)
    return response(204)


# ---------------------------------------------------------------------------
# Directory tree: CEOs -> departments -> their managers/employees
# ---------------------------------------------------------------------------
#
# The old version grouped by manager_id (admin -> their managers -> their
# employees). Management is now scoped by department instead, so the tree is
# grouped by department instead of by manager_id chains. Company-wide, so
# it's CEO-only - a MANAGER already gets their department's employees from
# GET /employees.

def directory_tree_route(event, user):
    auth.require_role(user, ["CEO"])

    rows = db.list_employees()
    departments = db.list_departments()

    def brief(employee_row):
        return {
            "id": employee_row["id"],
            "first_name": employee_row["first_name"],
            "last_name": employee_row["last_name"],
            "email": employee_row["email"],
            "role": employee_row["role"],
            "job_title": employee_row["job_title"],
        }

    ceos = [brief(row) for row in rows if row["role"] == "CEO"]

    dept_tree = []
    for department in departments:
        dept_rows = [row for row in rows if row["department_id"] == department["id"]]
        dept_tree.append({
            "department": department["name"],
            "managers": [brief(row) for row in dept_rows if row["role"] == "MANAGER"],
            "employees": [brief(row) for row in dept_rows if row["role"] == "EMPLOYEE"],
        })

    return response(200, {"ceos": ceos, "departments": dept_tree})


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

# (method, path regex, requires_auth, handler)
# Handlers either take (event, user) or (event, user, id) - id groups are
# captured from the path and passed as extra positional args, in order.
ROUTES = (
    ("POST", re.compile(r"^/auth/login$"), False, login_route),
    ("POST", re.compile(r"^/employees$"), True, create_employee_route),
    ("GET", re.compile(r"^/employees$"), True, list_employees_route),
    ("GET", re.compile(r"^/employees/(?P<id>\d+)$"), True, get_employee_route),
    ("PUT", re.compile(r"^/employees/(?P<id>\d+)$"), True, update_employee_route),
    ("DELETE", re.compile(r"^/employees/(?P<id>\d+)$"), True, delete_employee_route),
    ("POST", re.compile(r"^/change-requests$"), True, create_change_request_route),
    ("GET", re.compile(r"^/change-requests$"), True, list_change_requests_route),
    ("PUT", re.compile(r"^/change-requests/(?P<id>\d+)$"), True, update_change_request_route),
    ("POST", re.compile(r"^/departments$"), True, create_department_route),
    ("GET", re.compile(r"^/departments$"), True, list_departments_route),
    ("GET", re.compile(r"^/departments/(?P<id>\d+)$"), True, get_department_route),
    ("PUT", re.compile(r"^/departments/(?P<id>\d+)$"), True, update_department_route),
    ("DELETE", re.compile(r"^/departments/(?P<id>\d+)$"), True, delete_department_route),
    ("GET", re.compile(r"^/directory-tree$"), True, directory_tree_route),
)


def handler(event=None, context=None):
    """
    Lambda entry point. Routes the request based on httpMethod + path,
    enforces auth/permissions, and maps errors to the correct status codes.
    """
    event = event or {}
    logger.debug("Received event: %s", event)

    method = (event.get("httpMethod") or "").upper()
    path = (event.get("path") or "").rstrip("/") or "/"

    for route_method, pattern, requires_auth, route_handler in ROUTES:
        if route_method != method:
            continue
        match = pattern.match(path)
        if not match:
            continue

        try:
            path_args = [int(value) for value in match.groups()]

            if not requires_auth:
                return route_handler(event, *path_args)

            user = auth.get_current_user(event)
            return route_handler(event, user, *path_args)

        except AuthError as e:
            return response(e.status_code, {"error": e.message})
        except ValidationError as e:
            return response(400, {"error": str(e)})
        except NotFoundError as e:
            return response(404, {"error": str(e)})
        except Exception as e:
            logger.error("Unhandled error in %s %s: %s", method, path, str(e))
            return response(500, {"error": "Internal server error"})

    return response(404, {"error": f"No route for {method} {path}"})


# Main entry point for local testing
if __name__ == "__main__":
    print(handler({"httpMethod": "POST", "path": "/auth/login", "body": json.dumps({"email": "a@b.com", "password": "x"})}))
