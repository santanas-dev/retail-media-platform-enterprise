"""KSO Player Client — safe HTTP adapter."""

import json
from typing import Any, Optional

import requests

from .retry_backoff import PlayerHttpError


class PlayerHttpClient:
    def __init__(self, base_url: str, token: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get_json(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.get(url, headers=self._auth_headers(), timeout=30)
        return self._handle(resp)

    def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = requests.post(url, json=body, headers=self._auth_headers(), timeout=30)
        return self._handle(resp)

    def _handle(self, resp: requests.Response) -> dict[str, Any]:
        if resp.status_code < 400:
            data: Any = resp.json() if resp.text else {}
            if not isinstance(data, dict):
                raise PlayerHttpError(resp.status_code, "invalid JSON response", retryable=False)
            return data
        retryable = resp.status_code in (429, 502, 503, 504)
        raise PlayerHttpError(resp.status_code, resp.text[:500] or "HTTP error", retryable=retryable)
