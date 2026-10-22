import re
import secrets
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from fastapi import Request

from app.core.config import Settings
from app.core.hashing import BASE62_ALPHABET, hash_url
from app.models.schemas import OriginalUrlResponse, ShortenResponse, Suggestion
from app.repositories.url_repository import UrlRepository

PREFIX_RE = re.compile(r"^[A-Za-z0-9]{1,20}$")


class ShortUrlNotFound(Exception):
    pass


class InvalidPrefix(ValueError):
    pass


class ShortenerService:
    def __init__(self, repo: UrlRepository, settings: Settings):
        self.repo = repo
        self.settings = settings

    # ---------- helpers ----------
    def _build_short_url(self, code: str) -> str:
        return f"{self.settings.base_url}/{code}"

    @staticmethod
    def _make_code(prefix: Optional[str], hash_code: str) -> str:
        return f"{prefix}-{hash_code}" if prefix else hash_code

    @staticmethod
    def _sanitize(text: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", text)[:20]

    def _server_prefixes(self, long_url: str) -> List[str]:
        """Fallback candidates: domain label, first path segment, random tokens."""
        parsed = urlparse(long_url)
        candidates = []
        host = parsed.hostname or ""
        labels = [l for l in host.split(".") if l and l != "www"]
        if labels:
            candidates.append(self._sanitize(labels[0]).lower())
        segments = [s for s in parsed.path.split("/") if s]
        if segments:
            candidates.append(self._sanitize(segments[0]).lower())
        candidates += ["".join(secrets.choice(BASE62_ALPHABET) for _ in range(3)) for _ in range(5)]
        return [c for c in candidates if c]

    def _available_suggestions(self, hash_code: str, prefixes: Iterable[str]) -> List[Suggestion]:
        out, seen = [], set()
        for p in prefixes:
            if p in seen or not PREFIX_RE.match(p):
                continue
            seen.add(p)
            code = self._make_code(p, hash_code)
            if not self.repo.exists(code):
                out.append(Suggestion(prefix=p, short_url=self._build_short_url(code)))
            if len(out) >= self.settings.max_suggestions:
                break
        return out

    @staticmethod
    def _extract_code(url_or_code: str) -> str:
        path = urlparse(url_or_code).path if "://" in url_or_code else url_or_code
        return path.strip("/").split("/")[-1]

    # ---------- public API ----------
    def shorten(self, long_url: str, suggestions: List[str], prefix: Optional[str] = None) -> ShortenResponse:
        if prefix is not None and not PREFIX_RE.match(prefix):
            raise InvalidPrefix("prefix must be 1-20 alphanumeric characters")

        hash_code = hash_url(long_url, self.settings.hash_length)
        code = self._make_code(prefix, hash_code)

        # Bloom says "definitely free" -> skip DB read. "Maybe" -> SET NX decides.
        if not self.repo.exists(code) and self.repo.save_if_absent(code, long_url):
            return ShortenResponse(created=True, code=code, short_url=self._build_short_url(code))

        # Taken: client suggestions first, then server-generated fallback.
        options = self._available_suggestions(hash_code, suggestions)
        if len(options) < self.settings.max_suggestions:
            taken = {s.prefix for s in options}
            extra = [p for p in self._server_prefixes(long_url) if p not in taken]
            options += self._available_suggestions(hash_code, extra)[: self.settings.max_suggestions - len(options)]
        return ShortenResponse(created=False, code=code, suggestions=options)

    def get_original_url(self, url: str) -> OriginalUrlResponse:
        code = self._extract_code(url)
        original = self.repo.get(code) if code else None
        if original is None:
            raise ShortUrlNotFound(code)
        return OriginalUrlResponse(code=code, original_url=original)


def get_shortener_service(request: Request) -> ShortenerService:
    return request.app.state.shortener_service
