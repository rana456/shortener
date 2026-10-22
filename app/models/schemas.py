from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ShortenRequest(BaseModel):
    url: HttpUrl
    suggestions: List[str] = Field(default_factory=list, description="Preferred prefixes to try if the hash is taken")
    prefix: Optional[str] = Field(None, description="Claim a specific prefix, e.g. one returned in suggestions")


class Suggestion(BaseModel):
    prefix: str
    short_url: str


class ShortenResponse(BaseModel):
    created: bool
    code: str
    short_url: Optional[str] = None
    suggestions: List[Suggestion] = Field(default_factory=list)


class OriginalUrlResponse(BaseModel):
    code: str
    original_url: str
