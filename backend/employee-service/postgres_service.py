"""
PostgreSQL database configuration and connection management for the Employee
Directory service.

This module handles PostgreSQL connection pooling using a module-level
variable to reuse a single connection across Lambda invocations (improving
performance and reducing cold start time), plus every query function used by
the Lambda handler (employees, departments, auth lookups).
"""

import os
from psycopg import connect
from psycopg.rows import dict_row

# ---------------------------------------------------------------------------
# Connection configuration
# ---------------------------------------------------------------------------

IS_LOCAL = os.getenv("IS_LOCAL", "false") == "true"

PG_CONFIG = (
    f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"user={os.getenv('POSTGRES_USER', 'test')} "
    f"password={os.getenv('POSTGRES_PASS', 'test')} "
    f"dbname={os.getenv('POSTGRES_NAME', 'test')} "
    f"connect_timeout=15"
    + ("" if IS_LOCAL else " sslmode=require")
)

# Module-level PostgreSQL connection for connection pooling across Lambda
# invocations. Persists between invocations within the same Lambda container.
PG_CONN = None

VALID_ROLES = ("EMPLOYEE", "MANAGER", "CEO")


def get_connection():
    """
    Returns a live, pooled PostgreSQL connection, creating one if needed.

    Connection pooling strategy:
    - First invocation: creates a new connection and stores it in PG_CONN.
    - Subsequent invocations: reuses the existing connection if still open.
    - On error: the caller is responsible for resetting PG_CONN via
      reset_connection() so the next invocation reconnects.
    """
    global PG_CONN
    if PG_CONN is None or PG_CONN.closed:
        PG_CONN = connect(PG_CONFIG, autocommit=True, row_factory=dict_row)
        _ensure_schema(PG_CONN)
    return PG_CONN


def _ensure_schema(conn):
    """
    There's no separate migration tool for this project - schema changes are
    applied as idempotent DDL here, run once per new pooled connection.
    """
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS skills TEXT[] NOT NULL DEFAULT '{}'")
        cur.execute("ALTER TABLE employees ADD COLUMN IF NOT EXISTS location TEXT")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS change_requests (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                field_name TEXT NOT NULL,
                requested_value TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                reviewed_by INTEGER REFERENCES employees(id),
                reviewed_at TIMESTAMPTZ
            )
            """
        )


def reset_connection():
    """Drops the pooled connection so the next call reconnects from scratch."""
    global PG_CONN
    PG_CONN = None


def _execute(query, params=None, fetchone=False, fetchall=False):
    """
    Small helper that runs a query against the pooled connection.

    Resets the pooled connection on failure so the next Lambda invocation
    doesn't keep reusing a broken connection/transaction.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            if fetchone:
                return cur.fetchone()
            if fetchall:
                return cur.fetchall()
            return None
    except Exception:
        reset_connection()
        raise


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

EMPLOYEE_FULL_COLUMNS = (
    "id, first_name, last_name, email, phone, job_title, department_id, "
    "manager_id, bio, role, is_active, created_at, skills, location"
)


def get_employee_by_id(employee_id):
    return _execute(
        f"SELECT {EMPLOYEE_FULL_COLUMNS} FROM employees WHERE id = %s",
        (employee_id,),
        fetchone=True,
    )


def get_employee_by_email(email):
    """Includes hashed_password/token_version - used only for login/auth, never returned to clients."""
    return _execute(
        f"SELECT {EMPLOYEE_FULL_COLUMNS}, hashed_password, token_version FROM employees WHERE email = %s",
        (email,),
        fetchone=True,
    )


def get_employee_auth_state(employee_id):
    """Minimal row used to validate a decoded JWT against current DB state."""
    return _execute(
        "SELECT id, role, department_id, is_active, token_version FROM employees WHERE id = %s",
        (employee_id,),
        fetchone=True,
    )


def list_employees():
    return _execute(
        f"SELECT {EMPLOYEE_FULL_COLUMNS} FROM employees ORDER BY id",
        fetchall=True,
    )


def list_employees_by_department(department_id):
    """Used to scope a MANAGER's view/management to their own department."""
    return _execute(
        f"SELECT {EMPLOYEE_FULL_COLUMNS} FROM employees WHERE department_id = %s ORDER BY id",
        (department_id,),
        fetchall=True,
    )


def create_employee(data, hashed_password):
    row = _execute(
        f"""
        INSERT INTO employees
            (first_name, last_name, email, phone, job_title, department_id,
             manager_id, bio, hashed_password, role, is_active, skills, location)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING {EMPLOYEE_FULL_COLUMNS}
        """,
        (
            data["first_name"],
            data["last_name"],
            data["email"],
            data.get("phone"),
            data.get("job_title"),
            data.get("department_id"),
            data.get("manager_id"),
            data.get("bio"),
            hashed_password,
            data.get("role", "EMPLOYEE"),
            data.get("is_active", True),
            data.get("skills") or [],
            data.get("location"),
        ),
        fetchone=True,
    )
    return row


def update_employee(employee_id, fields):
    """
    Updates only the given fields (dict of column -> value) on an employee.
    Returns the updated row, or None if the employee did not exist.
    """
    if not fields:
        return get_employee_by_id(employee_id)

    set_clause = ", ".join(f"{col} = %s" for col in fields)
    params = list(fields.values()) + [employee_id]
    return _execute(
        f"""
        UPDATE employees SET {set_clause}
        WHERE id = %s
        RETURNING {EMPLOYEE_FULL_COLUMNS}
        """,
        params,
        fetchone=True,
    )


def deactivate_employee(employee_id):
    """Soft delete: sets is_active = false."""
    return _execute(
        f"""
        UPDATE employees SET is_active = false
        WHERE id = %s
        RETURNING {EMPLOYEE_FULL_COLUMNS}
        """,
        (employee_id,),
        fetchone=True,
    )


def bump_token_version(employee_id):
    """Increments token_version, invalidating previously issued JWTs (used when role changes)."""
    return _execute(
        "UPDATE employees SET token_version = token_version + 1 WHERE id = %s",
        (employee_id,),
    )


# ---------------------------------------------------------------------------
# Change requests
# ---------------------------------------------------------------------------

CHANGE_REQUEST_COLUMNS = (
    "id, employee_id, field_name, requested_value, status, "
    "created_at, reviewed_by, reviewed_at"
)


def create_change_request(employee_id, field_name, requested_value):
    return _execute(
        f"""
        INSERT INTO change_requests (employee_id, field_name, requested_value)
        VALUES (%s, %s, %s)
        RETURNING {CHANGE_REQUEST_COLUMNS}
        """,
        (employee_id, field_name, requested_value),
        fetchone=True,
    )


def get_change_request_by_id(request_id):
    return _execute(
        f"SELECT {CHANGE_REQUEST_COLUMNS} FROM change_requests WHERE id = %s",
        (request_id,),
        fetchone=True,
    )


def list_pending_change_requests():
    return _execute(
        f"SELECT {CHANGE_REQUEST_COLUMNS} FROM change_requests WHERE status = 'pending' ORDER BY created_at",
        fetchall=True,
    )


def list_pending_change_requests_by_department(department_id):
    return _execute(
        f"""
        SELECT cr.id, cr.employee_id, cr.field_name, cr.requested_value, cr.status,
               cr.created_at, cr.reviewed_by, cr.reviewed_at
        FROM change_requests cr
        JOIN employees e ON e.id = cr.employee_id
        WHERE cr.status = 'pending' AND e.department_id = %s
        ORDER BY cr.created_at
        """,
        (department_id,),
        fetchall=True,
    )


def update_change_request(request_id, status, reviewed_by):
    return _execute(
        f"""
        UPDATE change_requests
        SET status = %s, reviewed_by = %s, reviewed_at = now()
        WHERE id = %s
        RETURNING {CHANGE_REQUEST_COLUMNS}
        """,
        (status, reviewed_by, request_id),
        fetchone=True,
    )


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

DEPARTMENT_COLUMNS = "id, name, description"


def get_department_by_id(department_id):
    return _execute(
        f"SELECT {DEPARTMENT_COLUMNS} FROM departments WHERE id = %s",
        (department_id,),
        fetchone=True,
    )


def list_departments():
    return _execute(
        f"SELECT {DEPARTMENT_COLUMNS} FROM departments ORDER BY id",
        fetchall=True,
    )


def create_department(name, description):
    return _execute(
        f"""
        INSERT INTO departments (name, description)
        VALUES (%s, %s)
        RETURNING {DEPARTMENT_COLUMNS}
        """,
        (name, description),
        fetchone=True,
    )


def update_department(department_id, fields):
    if not fields:
        return get_department_by_id(department_id)

    set_clause = ", ".join(f"{col} = %s" for col in fields)
    params = list(fields.values()) + [department_id]
    return _execute(
        f"""
        UPDATE departments SET {set_clause}
        WHERE id = %s
        RETURNING {DEPARTMENT_COLUMNS}
        """,
        params,
        fetchone=True,
    )


def delete_department(department_id):
    return _execute(
        "DELETE FROM departments WHERE id = %s RETURNING id",
        (department_id,),
        fetchone=True,
    )
