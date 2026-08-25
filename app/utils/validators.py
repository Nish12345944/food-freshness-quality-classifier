import re

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,80}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LEN = 8


def validate_registration(username: str, email: str, password: str) -> list[str]:
    errors = []
    if not USERNAME_RE.match(username or ""):
        errors.append("Username must be 3–80 characters (letters, numbers, underscores).")
    if email and not EMAIL_RE.match(email):
        errors.append("Invalid email address.")
    if not password or len(password) < MIN_PASSWORD_LEN:
        errors.append(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    return errors


def validate_login(username: str, password: str) -> list[str]:
    errors = []
    if not username:
        errors.append("Username is required.")
    if not password:
        errors.append("Password is required.")
    return errors
