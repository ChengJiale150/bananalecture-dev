from uuid import uuid4


def new_id() -> str:
    """Generate a UUID4 string."""
    return str(uuid4())
