import base64
import hashlib
import hmac
from secrets import token_urlsafe

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    if stored_hash.startswith("$argon2"):
        try:
            ok = _password_hasher.verify(stored_hash, password)
            return ok, _password_hasher.check_needs_rehash(stored_hash)
        except (InvalidHashError, VerifyMismatchError):
            return False, False

    if stored_hash.startswith("pbkdf2-sha256$"):
        return _verify_legacy_pbkdf2(password, stored_hash), True

    if len(stored_hash) == 64:
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, stored_hash), True

    return False, False


def new_session_token() -> str:
    return token_urlsafe(48)


def new_csrf_token() -> str:
    return token_urlsafe(32)


def _verify_legacy_pbkdf2(password: str, stored_hash: str) -> bool:
    try:
        _, iterations, salt_b64, digest_b64 = stored_hash.split("$", 3)
        salt = _urlsafe_b64decode(salt_b64)
        expected = _urlsafe_b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))

