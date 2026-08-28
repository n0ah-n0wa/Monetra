"""HTTP helpers for load testing."""

from __future__ import annotations

import time
from typing import Any

import httpx

from loadtest.config import LoadTestConfig
from loadtest.stats import RequestResult


class LoadTestClient:
    def __init__(self, config: LoadTestConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.request_timeout_seconds,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(
        self,
        *,
        scenario: str,
        method: str,
        path: str,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> RequestResult:
        headers: dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        started = time.perf_counter()
        try:
            response = await self._client.request(
                method,
                path,
                headers=headers,
                json=json,
                params=params,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            return RequestResult(
                scenario=scenario,
                latency_ms=latency_ms,
                status_code=response.status_code,
                error=None if response.is_success else response.text[:200],
            )
        except httpx.HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return RequestResult(
                scenario=scenario,
                latency_ms=latency_ms,
                status_code=0,
                error=str(exc),
            )

    async def login(self) -> str:
        response = await self._client.post(
            "/api/v1/auth/login",
            json={"email": self._config.email, "password": self._config.password},
        )
        response.raise_for_status()
        return str(response.json()["access_token"])

    async def register(self) -> str:
        response = await self._client.post(
            "/api/v1/auth/register",
            json={"email": self._config.email, "password": self._config.password},
        )
        if response.status_code == 409:
            return await self.login()
        response.raise_for_status()
        return str(response.json()["access_token"])

    async def get_json(
        self,
        path: str,
        *,
        token: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(
            path,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            msg = f"Expected object JSON from {path}"
            raise TypeError(msg)
        return payload

    async def post_json(
        self,
        path: str,
        *,
        token: str,
        json: dict[str, Any],
    ) -> dict[str, Any]:
        response = await self._client.post(
            path,
            headers={"Authorization": f"Bearer {token}"},
            json=json,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            msg = f"Expected object JSON from {path}"
            raise TypeError(msg)
        return payload
