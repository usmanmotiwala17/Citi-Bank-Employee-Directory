"""
Input validation for employee fields that need more than a type check:
role/department consistency, manager_id integrity, and the single-active-
admin rule.
"""

import postgres_service as db
from web import ValidationError

VALID_ROLES = db.VALID_ROLES

VALID_AVAILABILITY_STATUSES = ("available", "unavailable")


def validate_skills(value):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValidationError("skills must be a list of strings")
    return value


def validate_availability_status(value):
    if value not in VALID_AVAILABILITY_STATUSES:
        raise ValidationError(f"availability_status must be one of {', '.join(VALID_AVAILABILITY_STATUSES)}")
    return value


def validate_single_admin(role, is_active, exclude_employee_id=None):
    """There can only ever be one active ADMIN. Only checked when the change
    in question would itself produce an active ADMIN (promoting/creating one,
    or reactivating one) - demoting/deactivating the current ADMIN is always
    allowed and simply frees up the seat."""
    if role != "ADMIN" or not is_active:
        return
    for row in db.list_employees():
        if row["role"] == "ADMIN" and row["is_active"] and row["id"] != exclude_employee_id:
            raise ValidationError(
                "There is already an active Admin. Demote or deactivate them before creating or promoting another."
            )


def validate_department(role, department_id):
    if role not in VALID_ROLES:
        raise ValidationError(f"role must be one of {', '.join(VALID_ROLES)}")

    if role == "ADMIN":
        if department_id is not None:
            raise ValidationError("An ADMIN has company-wide access and must not be assigned to a single department (department_id must be null)")
        return

    if department_id is None:
        raise ValidationError(f"A '{role}' must have a department_id set")
    if db.get_department_by_id(department_id) is None:
        raise ValidationError("department_id does not reference an existing department")


# manager_id validation - each department has exactly one manager, and
# manager_id is meant to record who an employee actually reports to, not
# just any employee id.

def validate_manager_id(role, department_id, manager_id):
    if manager_id is None:
        return

    if role == "ADMIN":
        raise ValidationError("An ADMIN does not report to a manager (manager_id must be null)")

    manager = db.get_employee_by_id(manager_id)
    if manager is None:
        raise ValidationError("manager_id does not reference an existing employee")
    if manager["role"] != "MANAGER":
        raise ValidationError("manager_id must reference an employee with role 'MANAGER'")
    if department_id is not None and manager["department_id"] != department_id:
        raise ValidationError("manager_id must reference the manager of the same department")
