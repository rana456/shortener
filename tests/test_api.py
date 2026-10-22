import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.core.hashing import hash_url
from app.main import create_app

URL = "https://www.example.com/blog/post-1"


@pytest.fixture
def client():
    fake = fakeredis.FakeRedis(decode_responses=True)
    with TestClient(create_app(redis_client=fake)) as c:
        yield c


def test_hash_is_8_chars_and_deterministic():
    assert len(hash_url(URL)) == 8
    assert hash_url(URL) == hash_url(URL)


def test_create_then_resolve(client):
    r = client.post("/short", json={"url": URL})
    assert r.status_code == 201
    body = r.json()
    assert body["created"] and body["short_url"].endswith("/" + hash_url(URL))

    r = client.get("/getOriginalurl", params={"url": body["short_url"]})
    assert r.status_code == 200 and r.json()["original_url"] == URL


def test_taken_returns_client_then_server_suggestions(client):
    client.post("/short", json={"url": URL})
    r = client.post("/short", json={"url": URL, "suggestions": ["mine", "bad-prefix!"]})
    assert r.status_code == 409
    prefixes = [s["prefix"] for s in r.json()["suggestions"]]
    assert prefixes[0] == "mine" and "bad-prefix!" not in prefixes
    assert "example" in prefixes  # server fallback from domain
    assert all(s["short_url"].endswith(f"{s['prefix']}-{hash_url(URL)}") for s in r.json()["suggestions"])


def test_claim_suggested_prefix(client):
    client.post("/short", json={"url": URL})
    r = client.post("/short", json={"url": URL, "prefix": "mine"})
    assert r.status_code == 201 and r.json()["code"] == f"mine-{hash_url(URL)}"
    r = client.get("/getOriginalurl", params={"url": r.json()["code"]})
    assert r.json()["original_url"] == URL


def test_unknown_code_404(client):
    assert client.get("/getOriginalurl", params={"url": "nope1234"}).status_code == 404
