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

VALID_ROLES = ("employee", "manager", "admin")


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
    return PG_CONN


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
    "manager_id, bio, role, is_active, created_at"
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
        "SELECT id, role, is_active, token_version FROM employees WHERE id = %s",
        (employee_id,),
        fetchone=True,
    )


def list_employees():
    return _execute(
        f"SELECT {EMPLOYEE_FULL_COLUMNS} FROM employees ORDER BY id",
        fetchall=True,
    )


def list_direct_reports(manager_id):
    return _execute(
        f"SELECT {EMPLOYEE_FULL_COLUMNS} FROM employees WHERE manager_id = %s ORDER BY id",
        (manager_id,),
        fetchall=True,
    )


def create_employee(data, hashed_password):
    row = _execute(
        f"""
        INSERT INTO employees
            (first_name, last_name, email, phone, job_title, department_id,
             manager_id, bio, hashed_password, role, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            data.get("role", "employee"),
            data.get("is_active", True),
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
