import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_items_crud():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # listar vacío
        r = await ac.get("/api/v1/items/")
        assert r.status_code == 200
        assert r.json() == []

        # crear
        r = await ac.post("/api/v1/items/", json={"name": "demo", "description": "desc"})
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == 1
        assert data["name"] == "demo"

        # obtener
        r = await ac.get("/api/v1/items/1")
        assert r.status_code == 200
        assert r.json()["name"] == "demo"
