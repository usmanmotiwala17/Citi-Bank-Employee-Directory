"""
/departments routes: create, list, get, update, delete. All mutations are
Admin-only; listing/getting a single department is open to anyone
authenticated.
"""

from psycopg.errors import UniqueViolation

import auth_service as auth
import postgres_service as db
from serializers import serialize_department
from web import NotFoundError, ValidationError, parse_body, response


def create_department_route(event, user):
    auth.require_role(user, ["ADMIN"])
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
    auth.require_role(user, ["ADMIN"])
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
    auth.require_role(user, ["ADMIN"])
    existing = db.get_department_by_id(department_id)
    if existing is None:
        raise NotFoundError("Department not found")

    db.delete_department(department_id)
    return response(204)
