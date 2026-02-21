"""Integration tests that exercise the viewer through httpx ASGI transport.

This validates the full HTTP request/response cycle using httpx directly
(instead of Starlette TestClient) to surface any ASGI-level issues.
"""
from __future__ import annotations

from typing import AsyncGenerator, List

import httpx
import pytest
from fastapi import FastAPI

RUN_A = "20250101_120000_aaaaaa"

pytestmark = pytest.mark.anyio


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture()
async def async_client(viewer_app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=viewer_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


class TestClientServerRoundTrip:

    async def test_health(self, async_client: httpx.AsyncClient) -> None:
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_list_runs(
        self, async_client: httpx.AsyncClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = await async_client.get("/api/runs")
        assert resp.status_code == 200
        ids = {r["id"] for r in resp.json()}
        assert RUN_A in ids

    async def test_get_metrics(
        self, async_client: httpx.AsyncClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = await async_client.get(f"/api/runs/{RUN_A}/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "global_step" in data["columns"]

    async def test_patch_run(
        self, async_client: httpx.AsyncClient, populated_viewer_storage: List[str]
    ) -> None:
        resp = await async_client.patch(
            f"/api/runs/{RUN_A}", json={"alias": "httpx-test"}
        )
        assert resp.status_code == 200
        assert resp.json()["alias"] == "httpx-test"
