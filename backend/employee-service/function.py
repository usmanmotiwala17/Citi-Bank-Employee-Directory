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

PUBLIC_EMPLOYEE_FIELDS = (
    "id", "first_name", "last_name", "email", "phone",
    "job_title", "department_id", "manager_id", "is_active",
)
FULL_EMPLOYEE_EXTRA_FIELDS = ("bio", "role", "created_at")


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
# Serialization (role-based field visibility)
# ---------------------------------------------------------------------------

def _can_view_full_detail(viewer, employee_row):
    if viewer["role"] == "admin":
        return True
    if viewer["id"] == employee_row["id"]:
        return True
    if viewer["role"] == "manager" and employee_row["manager_id"] == viewer["id"]:
        return True
    return False


def serialize_employee(employee_row, viewer):
    data = {field: employee_row[field] for field in PUBLIC_EMPLOYEE_FIELDS}
    if _can_view_full_detail(viewer, employee_row):
        for field in FULL_EMPLOYEE_EXTRA_FIELDS:
            data[field] = employee_row[field]
    return data


def serialize_department(department_row):
    return {"id": department_row["id"], "name": department_row["name"], "description": department_row["description"]}


# ---------------------------------------------------------------------------
# Hierarchy validation (admin -> null, manager -> admin, employee -> manager)
# ---------------------------------------------------------------------------

def validate_manager_hierarchy(role, manager_id, exclude_id=None):
    if role not in VALID_ROLES:
        raise ValidationError(f"role must be one of {', '.join(VALID_ROLES)}")

    if role == "admin":
        if manager_id is not None:
            raise ValidationError("Admins must not have a manager (manager_id must be null)")
        return

    if manager_id is None:
        raise ValidationError(f"A '{role}' must have a manager_id set")
    if exclude_id is not None and manager_id == exclude_id:
        raise ValidationError("manager_id cannot reference the employee itself")

    manager = db.get_employee_by_id(manager_id)
    if manager is None:
        raise ValidationError("manager_id does not reference an existing employee")

    required_manager_role = "admin" if role == "manager" else "manager"
    if manager["role"] != required_manager_role:
        raise ValidationError(
            f"A '{role}' must report to an employee with role '{required_manager_role}'"
        )


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

    token = auth.create_access_token(employee["id"], employee["role"], employee["token_version"])
    viewer = {"id": employee["id"], "role": employee["role"]}
    return response(200, {
        "access_token": token,
        "token_type": "bearer",
        "employee": serialize_employee(employee, viewer),
    })


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

def create_employee_route(event, user):
    auth.require_role(user, ["admin"])
    body = parse_body(event)

    required_fields = ("first_name", "last_name", "email", "password")
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")

    email = body["email"].strip().lower()
    if "@" not in email:
        raise ValidationError("Invalid email address")

    role = body.get("role", "employee")
    manager_id = body.get("manager_id")
    validate_manager_hierarchy(role, manager_id)

    department_id = body.get("department_id")
    if department_id is not None and db.get_department_by_id(department_id) is None:
        raise ValidationError("department_id does not reference an existing department")

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
    }

    try:
        created = db.create_employee(data, auth.hash_password(body["password"]))
    except UniqueViolation:
        raise ValidationError("Email already in use")

    return response(201, serialize_employee(created, user))


def list_employees_route(event, user):
    rows = db.list_employees()
    return response(200, [serialize_employee(row, user) for row in rows])


def get_employee_route(event, user, employee_id):
    employee = db.get_employee_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    return response(200, serialize_employee(employee, user))


def update_employee_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    body = parse_body(event)
    if not body:
        raise ValidationError("Request body must include at least one field to update")

    # Determine which fields this actor is allowed to touch on this target.
    if user["role"] == "admin":
        allowed_fields = {
            "first_name", "last_name", "email", "phone", "job_title",
            "department_id", "manager_id", "bio", "role", "is_active",
        }
    elif user["id"] == target["id"]:
        allowed_fields = {"phone", "bio"}
    elif user["role"] == "manager" and target["manager_id"] == user["id"]:
        allowed_fields = {"job_title", "department_id", "is_active"}
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
        department_id = body["department_id"]
        if department_id is not None and db.get_department_by_id(department_id) is None:
            raise ValidationError("department_id does not reference an existing department")
        fields["department_id"] = department_id
    if "role" in body:
        fields["role"] = body["role"]
    if "manager_id" in body:
        fields["manager_id"] = body["manager_id"]

    if not fields:
        raise ValidationError("No valid fields provided to update")

    # Re-validate the hierarchy rules whenever role or manager_id changes,
    # merging with the target's current values for whichever one isn't changing.
    if "role" in fields or "manager_id" in fields:
        new_role = fields.get("role", target["role"])
        new_manager_id = fields.get("manager_id", target["manager_id"])
        validate_manager_hierarchy(new_role, new_manager_id, exclude_id=target["id"])

    try:
        updated = db.update_employee(target["id"], fields)
    except UniqueViolation:
        raise ValidationError("Email already in use")

    # A stale JWT would keep carrying the old role - invalidate it immediately.
    if "role" in fields and fields["role"] != target["role"]:
        db.bump_token_version(target["id"])

    return response(200, serialize_employee(updated, user))


def delete_employee_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    is_own_direct_report = user["role"] == "manager" and target["manager_id"] == user["id"]
    if user["role"] != "admin" and not is_own_direct_report:
        raise AuthError("Not permitted to deactivate this employee", status_code=403)

    db.deactivate_employee(employee_id)
    return response(204)


def list_reports_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    is_own_team = user["role"] == "manager" and user["id"] == employee_id
    if user["role"] != "admin" and not is_own_team:
        raise AuthError("Not permitted to view these reports", status_code=403)

    rows = db.list_direct_reports(employee_id)
    return response(200, [serialize_employee(row, user) for row in rows])


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

def create_department_route(event, user):
    auth.require_role(user, ["admin"])
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
    auth.require_role(user, ["admin"])
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
    auth.require_role(user, ["admin"])
    existing = db.get_department_by_id(department_id)
    if existing is None:
        raise NotFoundError("Department not found")

    db.delete_department(department_id)
    return response(204)


# ---------------------------------------------------------------------------
# Directory tree: admins -> their managers -> their employees
# ---------------------------------------------------------------------------

def directory_tree_route(event, user):
    rows = db.list_employees()

    reports_by_manager = {}
    for row in rows:
        reports_by_manager.setdefault(row["manager_id"], []).append(row)

    def build_node(employee_row):
        return {
            "id": employee_row["id"],
            "first_name": employee_row["first_name"],
            "last_name": employee_row["last_name"],
            "email": employee_row["email"],
            "role": employee_row["role"],
            "job_title": employee_row["job_title"],
            "reports": [build_node(child) for child in reports_by_manager.get(employee_row["id"], [])],
        }

    tree = [build_node(row) for row in rows if row["role"] == "admin"]
    return response(200, tree)


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
    ("GET", re.compile(r"^/employees/(?P<id>\d+)/reports$"), True, list_reports_route),
    ("GET", re.compile(r"^/employees/(?P<id>\d+)$"), True, get_employee_route),
    ("PUT", re.compile(r"^/employees/(?P<id>\d+)$"), True, update_employee_route),
    ("DELETE", re.compile(r"^/employees/(?P<id>\d+)$"), True, delete_employee_route),
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
