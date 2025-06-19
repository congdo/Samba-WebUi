import jwt
from flask import request

def log(msg):
    """Log informational message."""
    print("[INFO]", msg, flush=True)

def error(msg):
    """Log error message."""
    print("[ERROR]", msg, flush=True)

def get_email_from_jwt():
    """Extract email from JWT token in CF_Authorization cookie."""
    token = request.cookies.get("CF_Authorization")
    if not token:
        return None
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("email")
    except Exception as e:
        error(f"JWT decode error: {e}")
        return None

def get_username_from_email(email):
    """
    Extracts the username part from an email and removes periods.
    e.g., 'cong.do@mozox.com' -> 'congdo'
    """
    if not email:
        return None
    username_part = email.split("@")[0]
    return username_part.replace(".", "")  # Remove periods