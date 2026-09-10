"""
Shapes DB rows into API response bodies.

Unlike the old admin/manager/employee version, there's no "public directory"
tier anymore: if you're not allowed to see someone (see permissions.py),
you don't get a trimmed-down record - you get a 403. So serialization
mostly doesn't branch on the viewer - it's a flat field selection - with one
deliberate exception: manager_notes, which must never appear in a response
served to the employee it's about, even though the rest of their own record
is fully visible to them.
"""

import postgres_service as db
from permissions import _can_view_manager_notes

EMPLOYEE_FIELDS = (
    "id", "first_name", "last_name", "email", "phone",
    "job_title", "department_id", "manager_id", "is_active",
    "bio", "role", "created_at", "skills", "location", "availability_status",
)


def serialize_employee(employee_row, viewer):
    data = {field: employee_row[field] for field in EMPLOYEE_FIELDS}
    if _can_view_manager_notes(viewer, employee_row):
        data["manager_notes"] = employee_row["manager_notes"]
    return data


def _brief(employee_row):
    """Minimal id/name/title shape used for org-structure links (manager, direct reports)."""
    return {
        "id": employee_row["id"],
        "first_name": employee_row["first_name"],
        "last_name": employee_row["last_name"],
        "job_title": employee_row["job_title"],
    }


def _enrich_with_org_structure(payload, employee_row):
    """Adds `manager` (if they report to one) and `direct_reports` (if they are one) to a serialized employee."""
    if employee_row["manager_id"] is not None:
        manager = db.get_employee_by_id(employee_row["manager_id"])
        if manager is not None:
            payload["manager"] = _brief(manager)
    if employee_row["role"] == "MANAGER":
        payload["direct_reports"] = [_brief(row) for row in db.list_employees_by_manager_id(employee_row["id"])]
    return payload


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
