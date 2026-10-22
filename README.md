# URL Shortener

FastAPI + Redis (key-value store) + RedisBloom (Bloom filter of used codes).

```
app/
  main.py                          # app factory, wires Redis -> repo -> service
  core/config.py                   # env settings
  core/hashing.py                  # SHA-256 -> base62 -> 8 chars
  repositories/url_repository.py   # Redis KV + Bloom filter
  services/shortener_service.py    # shorten / resolve / suggestions
  api/routes.py                    # endpoints
  models/schemas.py
tests/test_api.py                  # runs on fakeredis, no server needed
docker-compose.yml                 # redis-stack-server (has RedisBloom)
```

## Run

```bash
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://127.0.0.1:8000/docs
pytest -q
```

Env vars: `REDIS_URL`, `BASE_URL`, `HASH_LENGTH`, `BLOOM_CAPACITY`, `BLOOM_ERROR_RATE`, `MAX_SUGGESTIONS`.

## Flow — `POST /short`

1. `code = base62(sha256(url))[:8]`
2. Bloom `BF.EXISTS code` → **no** = definitely free (no DB read). **maybe** → check Redis.
3. Free → `SET url:<code> <url> NX` (atomic, handles races) + `BF.ADD` → **201** `{short_url}`.
4. Taken → **409** with available suggestions `base/{prefix}-{code}`:
   client `suggestions` first, then server fallbacks (domain, first path segment, random 3-char).
5. Claim one by re-posting with `"prefix": "<chosen>"`.

```bash
curl -X POST localhost:8000/short -H 'content-type: application/json' \
  -d '{"url":"https://www.example.com/blog/post-1","suggestions":["mine"]}'
curl "localhost:8000/getOriginalurl?url=http://localhost:8000/mine-XXXXXXXX"
```

## Other KV options considered

| Store | Notes |
|---|---|
| **Redis + RedisBloom** (chosen) | Fast, shared Bloom filter, easy local dev |
| DynamoDB | Managed, scales; conditional put replaces `SET NX`; Bloom kept in-app |
| Cassandra / ScyllaDB | High write throughput at large scale |
| RocksDB / LMDB | Embedded, single-node only |
