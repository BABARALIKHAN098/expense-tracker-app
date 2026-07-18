from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(plain: str) -> str:
    """Return a scrypt-hashed version of `plain` for storage in users.password_hash."""
    return generate_password_hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    """Return True iff `plain` matches the stored `password_hash`."""
    return check_password_hash(password_hash, plain)
