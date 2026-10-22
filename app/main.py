from contextlib import asynccontextmanager
from typing import Optional

import redis
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import Settings, settings as default_settings
from app.repositories.url_repository import UrlRepository
from app.services.shortener_service import ShortenerService


def create_app(redis_client: Optional[redis.Redis] = None, settings: Settings = default_settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = redis_client or redis.Redis.from_url(settings.redis_url, decode_responses=True)
        repo = UrlRepository(client, settings.bloom_key, settings.bloom_capacity, settings.bloom_error_rate)
        app.state.shortener_service = ShortenerService(repo, settings)
        yield
        if redis_client is None:
            client.close()

    app = FastAPI(title="URL Shortener", version="0.2.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
