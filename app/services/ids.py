import re
import secrets

_ID_RE = re.compile(r"^[0-9a-f]{4,8}$")


def generate_id(length: int) -> str:
    """Cryptographically random lowercase-hex ID."""
    return secrets.token_hex(length)[:length]


def is_valid_id(value: str) -> bool:
    """Strict format check. Also what stops path traversal on the file store."""
    return bool(_ID_RE.fullmatch(value))
