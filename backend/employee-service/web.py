"""
Small HTTP-shaped helpers shared by every route module: building a Lambda
response, parsing the request body, and the two error types route handlers
raise for 400/404s (auth's 401/403 is AuthError, over in auth_service.py).
"""

import base64
import json


class ValidationError(Exception):
    """Raised for any 400-level input validation failure."""


class NotFoundError(Exception):
    """Raised when a referenced resource does not exist (404)."""


def response(status_code, body=None):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, default=str) if body is not None else "",
    }


def parse_body(event):
    raw = event.get("body")
    if not raw:
        return {}
    if event.get("isBase64Encoded"):
        # Lambda Function URLs (payload format 2.0) base64-encode the body
        # in some cases - local_server.py/test_manual.py never set this
        # flag, so this is a no-op for those.
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        raise ValidationError("Request body must be valid JSON")
    if not isinstance(parsed, dict):
        raise ValidationError("Request body must be a JSON object")
    return parsed
