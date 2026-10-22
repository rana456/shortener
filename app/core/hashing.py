import hashlib
import string

BASE62_ALPHABET = string.digits + string.ascii_letters  # 0-9a-zA-Z


def base62_encode(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while num:
        num, rem = divmod(num, 62)
        chars.append(BASE62_ALPHABET[rem])
    return "".join(reversed(chars))


def hash_url(long_url: str, length: int = 8) -> str:
    """Deterministic short code: SHA-256 of the URL -> base62 -> first `length` chars.

    8 base62 chars = 62^8 ~= 2.18e14 possible codes.
    """
    digest = hashlib.sha256(long_url.strip().encode("utf-8")).digest()
    return base62_encode(int.from_bytes(digest, "big"))[:length]
