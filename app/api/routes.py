from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.models.schemas import OriginalUrlResponse, ShortenRequest, ShortenResponse
from app.services.shortener_service import (
    InvalidPrefix,
    ShortenerService,
    ShortUrlNotFound,
    get_shortener_service,
)

router = APIRouter()


@router.post("/short", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
def short(
    request: ShortenRequest,
    response: Response,
    service: ShortenerService = Depends(get_shortener_service),
) -> ShortenResponse:
    """201 + short_url when created; 409 + available prefix suggestions when the code is taken."""
    try:
        result = service.shorten(str(request.url), request.suggestions, request.prefix)
    except InvalidPrefix as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not result.created:
        response.status_code = status.HTTP_409_CONFLICT
    return result


@router.get("/getOriginalurl", response_model=OriginalUrlResponse)
def get_original_url(
    url: str = Query(..., description="Short URL or short code"),
    service: ShortenerService = Depends(get_shortener_service),
) -> OriginalUrlResponse:
    try:
        return service.get_original_url(url)
    except ShortUrlNotFound:
        raise HTTPException(status_code=404, detail="Short URL not found")
