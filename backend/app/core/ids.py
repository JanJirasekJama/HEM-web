from uuid import uuid4


def new_id(prefix: str | None = None) -> str:
    raw = uuid4().hex
    return f"{prefix}_{raw}" if prefix else raw

