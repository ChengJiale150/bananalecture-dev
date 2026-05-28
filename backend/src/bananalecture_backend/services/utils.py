import secrets
from uuid import uuid4


def new_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid4())


_SHORT_ID_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def new_short_id(length: int = 8) -> str:
    """Generate a short, URL-safe, human-readable random ID.

    Uses a reduced alphabet that excludes visually confusing characters
    (0, o, 1, l, i) to improve readability.
    """
    return "".join(secrets.choice(_SHORT_ID_ALPHABET) for _ in range(length))
