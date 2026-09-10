"""
/change-requests routes.

Employees can't edit their own phone number directly (see employee_routes'
allowed_fields) - instead they submit a request here, and their manager/the
Admin approves or rejects it. Approval is what actually updates the
employee row.
"""

import auth_service as auth
import postgres_service as db
from auth_service import AuthError
from permissions import _is_direct_manager
from serializers import serialize_change_request
from web import NotFoundError, ValidationError, parse_body, response

CHANGE_REQUEST_FIELDS = ("phone",)


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
    auth.require_role(user, ["ADMIN", "MANAGER"])
    if user["role"] == "ADMIN":
        rows = db.list_pending_change_requests()
    else:
        # Scoped to direct reports (manager_id == this manager), not
        # "anyone in my department" - see list_pending_change_requests_by_manager.
        rows = db.list_pending_change_requests_by_manager(user["id"])

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
    # Matches list_change_requests_route's scoping: Admin can review anyone's,
    # a Manager only their own direct reports' - not just enforced by what's
    # visible in their list, in case a request id is guessed/reused.
    if not (user["role"] == "ADMIN" or _is_direct_manager(user, target)):
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
