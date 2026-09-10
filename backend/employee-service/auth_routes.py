"""
POST /auth/login - the one route that isn't scoped to a resource. Actual
JWT creation/validation lives in auth_service.py; this just wires a login
attempt to it.
"""

import auth_service as auth
import postgres_service as db
from auth_service import AuthError
from serializers import serialize_employee
from web import ValidationError, parse_body, response


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
        "employee": serialize_employee(employee, employee),
    })
