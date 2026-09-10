"""
Employee Directory service - AWS Lambda entry point.

Routes incoming API Gateway events to the appropriate handler based on
httpMethod + path, enforcing JWT auth and role-based permissions before
touching the database.

The actual route handlers live in their own modules by resource
(auth_routes, employee_routes, change_request_routes, department_routes,
directory_routes), with shared plumbing split out into web.py (HTTP
request/response helpers + error types), permissions.py (who can view/
manage/see-notes-about whom), validation.py (input validation), and
serializers.py (DB row -> API response shaping). This file is just the
router.
"""

import json
import logging
import re

import auth_service as auth
from auth_service import AuthError
from web import NotFoundError, ValidationError, response

from auth_routes import login_route
from employee_routes import (
    create_employee_route, delete_employee_route, get_employee_route,
    list_employees_route, update_employee_route,
)
from change_request_routes import (
    create_change_request_route, list_change_requests_route, update_change_request_route,
)
from department_routes import (
    create_department_route, delete_department_route, get_department_route,
    list_departments_route, update_department_route,
)
from directory_routes import directory_tree_route

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
