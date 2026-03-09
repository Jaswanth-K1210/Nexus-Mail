import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from fastapi import status


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "3.1.0"
    assert "app" in data


@pytest.mark.asyncio
async def test_root():
    """Test the root endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["app"] == "Nexus Mail"
    assert "version" in data
