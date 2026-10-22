import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    base_url: str = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
    hash_length: int = int(os.getenv("HASH_LENGTH", "8"))
    bloom_key: str = os.getenv("BLOOM_KEY", "bf:short_codes")
    bloom_capacity: int = int(os.getenv("BLOOM_CAPACITY", "10000000"))
    bloom_error_rate: float = float(os.getenv("BLOOM_ERROR_RATE", "0.001"))
    max_suggestions: int = int(os.getenv("MAX_SUGGESTIONS", "3"))


settings = Settings()
