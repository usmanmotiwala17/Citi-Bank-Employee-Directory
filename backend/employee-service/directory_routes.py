"""
GET /directory-tree: Admins -> departments -> their managers/employees.

The old version grouped by manager_id (admin -> their managers -> their
employees). Management is now scoped by department instead, so the tree is
grouped by department instead of by manager_id chains. Company-wide, so
it's ADMIN-only - a MANAGER already gets their department's employees from
GET /employees.
"""

import auth_service as auth
import postgres_service as db
from web import response


def directory_tree_route(event, user):
    auth.require_role(user, ["ADMIN"])

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

    admins = [brief(row) for row in rows if row["role"] == "ADMIN"]

    dept_tree = []
    for department in departments:
        dept_rows = [row for row in rows if row["department_id"] == department["id"]]
        dept_tree.append({
            "department": department["name"],
            "managers": [brief(row) for row in dept_rows if row["role"] == "MANAGER"],
            "employees": [brief(row) for row in dept_rows if row["role"] == "EMPLOYEE"],
        })

    return response(200, {"admins": admins, "departments": dept_tree})
