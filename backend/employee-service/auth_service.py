"""
Authentication/authorization helpers for the Employee Directory service:
password hashing, JWT creation/validation, and extracting the current user
from a Lambda event's Authorization header.
"""

import os
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

import postgres_service as db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# In production this MUST be overridden via the JWT_SECRET env var.
JWT_SECRET = os.getenv("JWT_SECRET", "local-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthError(Exception):
    """Raised for any authentication/authorization failure.

    `status_code` lets the handler map this straight to a 401 or 403 response.
    """

    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain_password):
    return pwd_context.hash(plain_password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT creation
# ---------------------------------------------------------------------------

def create_access_token(employee_id, role, token_version):
    """Builds a signed JWT for an authenticated employee."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(employee_id),
        "role": role,
        "token_version": token_version,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Extracting/validating the current user from a Lambda event
# ---------------------------------------------------------------------------

def _get_auth_header(event):
    """
    API Gateway may lower-case or preserve header casing depending on
    integration type, so check headers case-insensitively.
    """
    headers = (event or {}).get("headers") or {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            return value
    return None


def get_current_user(event):
    """
    Extracts and validates the JWT from the Authorization header of a Lambda
    event, then re-checks the referenced employee against the database.

    Returns:
        dict: {"id": int, "role": str}

    Raises:
        AuthError: 401 if the header/token is missing, malformed, expired,
                   or points to a token_version/active state that no longer
                   matches the database (e.g. after a role change or
                   deactivation).
    """
    auth_header = _get_auth_header(event)
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("Missing or invalid Authorization header")

    token = auth_header[len("Bearer "):].strip()
    if not token:
        raise AuthError("Missing bearer token")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise AuthError("Invalid or expired token")

    try:
        employee_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise AuthError("Invalid token subject")

    token_version = payload.get("token_version")
    role = payload.get("role")
    if token_version is None or role is None:
        raise AuthError("Malformed token payload")

    # Re-check against the database so a deactivated account, a changed
    # role, or an explicit logout-everywhere (token_version bump) is
    # enforced immediately instead of waiting for the token to expire.
    current = db.get_employee_auth_state(employee_id)
    if current is None or not current["is_active"]:
        raise AuthError("Account is inactive or no longer exists")
    if current["token_version"] != token_version or current["role"] != role:
        raise AuthError("Token is no longer valid, please log in again")

    return {"id": employee_id, "role": role}


def require_role(user, allowed_roles):
    """Raises a 403 AuthError if the user's role is not in allowed_roles."""
    if user["role"] not in allowed_roles:
        raise AuthError(
            f"Role '{user['role']}' is not permitted to perform this action",
            status_code=403,
        )
