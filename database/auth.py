from werkzeug.security import generate_password_hash


def hash_password(plain: str) -> str:
    """Return a scrypt-hashed version of `plain` for storage in users.password_hash."""
    return generate_password_hash(plain)
