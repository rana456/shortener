from typing import Optional

import redis
from redis.exceptions import ResponseError


class UrlRepository:
    """Redis key-value store (code -> long URL) + RedisBloom filter of used codes."""

    KEY_PREFIX = "url:"

    def __init__(self, client: redis.Redis, bloom_key: str, capacity: int, error_rate: float):
        self.r = client
        self.bloom_key = bloom_key
        self._ensure_bloom(capacity, error_rate)

    def _ensure_bloom(self, capacity: int, error_rate: float) -> None:
        try:
            self.r.bf().reserve(self.bloom_key, error_rate, capacity)
        except ResponseError as e:
            if "exists" not in str(e).lower():  # already created on a previous start
                raise

    def _key(self, code: str) -> str:
        return f"{self.KEY_PREFIX}{code}"

    def might_exist(self, code: str) -> bool:
        """Bloom check. False = definitely free. True = maybe taken (verify in DB)."""
        return bool(self.r.bf().exists(self.bloom_key, code))

    def exists(self, code: str) -> bool:
        """Bloom first (cheap), DB only when the filter says 'maybe'."""
        return self.might_exist(code) and bool(self.r.exists(self._key(code)))

    def save_if_absent(self, code: str, long_url: str) -> bool:
        """Atomic insert (SET NX). Returns False if another request took the code first."""
        created = bool(self.r.set(self._key(code), long_url, nx=True))
        if created:
            self.r.bf().add(self.bloom_key, code)
        return created

    def get(self, code: str) -> Optional[str]:
        if not self.might_exist(code):
            return None
        return self.r.get(self._key(code))
