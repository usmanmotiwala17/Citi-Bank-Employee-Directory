"""
/employees routes: create, list, get, update, deactivate.
"""

from psycopg.errors import UniqueViolation

import auth_service as auth
import postgres_service as db
from auth_service import AuthError
from permissions import _can_manage, _can_view, _is_direct_manager
from serializers import _enrich_with_org_structure, serialize_employee
from validation import (
    validate_availability_status, validate_department, validate_manager_id,
    validate_single_admin, validate_skills,
)
from web import NotFoundError, ValidationError, parse_body, response


def create_employee_route(event, user):
    # Only the ADMIN can create new accounts - "manage within your department"
    # (MANAGER) covers viewing/editing/deactivating, not onboarding.
    auth.require_role(user, ["ADMIN"])
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

    validate_single_admin(role, is_active)

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
        "manager_notes": body.get("manager_notes"),
        "availability_status": validate_availability_status(body.get("availability_status", "available")),
    }

    try:
        created = db.create_employee(data, auth.hash_password(body["password"]))
    except UniqueViolation:
        raise ValidationError("Email already in use")

    return response(201, serialize_employee(created, user))


def list_employees_route(event, user):
    # Viewing is company-wide for every authenticated role (see _can_view) -
    # only managing/editing is scoped narrower, in update/delete routes below.
    rows = db.list_employees()
    return response(200, [serialize_employee(row, user) for row in rows])


def get_employee_route(event, user, employee_id):
    employee = db.get_employee_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found")
    if not _can_view(user, employee):
        raise AuthError("Not permitted to view this employee", status_code=403)
    payload = _enrich_with_org_structure(serialize_employee(employee, user), employee)
    return response(200, payload)


def update_employee_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    body = parse_body(event)
    if not body:
        raise ValidationError("Request body must include at least one field to update")

    # Determine which fields this actor is allowed to touch on this target.
    if user["role"] == "ADMIN":
        allowed_fields = {
            "first_name", "last_name", "email", "phone", "job_title",
            "department_id", "manager_id", "bio", "role", "is_active",
            "skills", "location", "manager_notes", "availability_status",
        }
    elif user["id"] == target["id"]:
        # Self-service: everyone can edit their own skills/availability,
        # regardless of role. A MANAGER additionally gets to edit their own
        # phone directly, no change-request needed - only for their own
        # record, not anyone else's (that's the elif below). manager_notes
        # is deliberately excluded for everyone here - nobody can write (or
        # even see) their own manager_notes, self-editing or not.
        allowed_fields = {"skills", "availability_status"}
        if user["role"] == "MANAGER":
            allowed_fields.add("phone")
    elif _is_direct_manager(user, target):
        # A MANAGER can only touch phone/email/is_active, and only for
        # employees whose manager_id is literally them - not "anyone in my
        # department" (that broader _can_manage rule still gates
        # deactivation, the one remaining place still scoped by department).
        # If they don't directly manage this person, they fall through to
        # the 403 below with no fields at all, not even these three.
        # manager_notes is included too - it's a distinct field with its own
        # always-on "direct manager" gate (see _can_view_manager_notes),
        # unaffected by this rule.
        allowed_fields = {"phone", "email", "is_active", "manager_notes"}
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
    if "manager_notes" in body:
        fields["manager_notes"] = body["manager_notes"]
    if "availability_status" in body:
        fields["availability_status"] = validate_availability_status(body["availability_status"])

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

    # Enforce the single-active-ADMIN rule whenever this update would itself
    # produce an active ADMIN (promoting someone, or reactivating one).
    if "role" in fields or "is_active" in fields:
        new_role = fields.get("role", target["role"])
        new_is_active = fields.get("is_active", target["is_active"])
        validate_single_admin(new_role, new_is_active, exclude_employee_id=target["id"])

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

    payload = _enrich_with_org_structure(serialize_employee(updated, user), updated)
    return response(200, payload)


def delete_employee_route(event, user, employee_id):
    target = db.get_employee_by_id(employee_id)
    if target is None:
        raise NotFoundError("Employee not found")

    if not _can_manage(user, target):
        raise AuthError("Not permitted to deactivate this employee", status_code=403)

    db.deactivate_employee(employee_id)
    return response(204)
