"""
Who can view/manage/see-notes-about whom.

Role model (replaces the old admin/manager/employee hierarchy, which scoped
a manager to their direct reports via manager_id):
  ADMIN    - full access to every employee and department: can view and
             manage (create/edit/deactivate) anyone.
  MANAGER  - can manage (edit job title / active status, deactivate)
             employees within their own department only.
  EMPLOYEE - can edit only their own profile (skills/availability - phone
             changes go through a manager/admin-approved change request).

Viewing is deliberately NOT scoped the same way as managing: every
authenticated employee can view every other employee's profile, company-
wide, read-only (see _can_view) - that's what lets the directory link any
employee to any other profile. manager_notes is the one exception, staying
restricted to the ADMIN and the subject's own direct manager regardless of
viewer (see _can_view_manager_notes below). _can_manage is the actual
(much narrower) gate on who can edit what.
"""


def _can_view(viewer, employee_row):
    """Every authenticated employee can view every other employee's profile,
    read-only - see _can_manage for the separate, narrower rule on editing."""
    return True


def _can_manage(viewer, employee_row):
    """Manage = deactivate, or approve/reject their change requests. Far
    narrower than viewing: ADMIN can manage anyone, a MANAGER can manage
    only their own department's people, and no one else can manage anyone
    but themselves (self-service is handled separately with a narrower set
    of fields). Kept department-scoped deliberately - see _is_direct_manager
    below for the stricter, manager_id-based rule used for editing a
    profile's own fields."""
    if viewer["role"] == "ADMIN":
        return True
    if viewer["role"] == "MANAGER" and employee_row["department_id"] == viewer["department_id"]:
        return True
    return False


def _is_direct_manager(viewer, employee_row):
    """True only if viewer is literally employee_row's own manager (their
    manager_id, not just "a manager in the same department"). Used to scope
    which profile fields a MANAGER can edit on someone else's record -
    narrower and more precise than _can_manage's department-based rule."""
    return viewer["role"] == "MANAGER" and employee_row["manager_id"] == viewer["id"]


def _can_view_manager_notes(viewer, employee_row):
    if viewer["role"] == "ADMIN":
        return True
    return viewer["id"] == employee_row["manager_id"]
