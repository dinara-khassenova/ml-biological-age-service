from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from config import BACKEND_BASE_URL, REQUEST_TIMEOUT


@dataclass
class ApiError(Exception):
    status_code: int
    message: str
    detail: Any = None
    method: str = ""
    url: str = ""

    def __str__(self) -> str:
        base = f"{self.message} (HTTP {self.status_code})"
        if self.method and self.url:
            base += f" [{self.method} {self.url}]"
        if self.detail:
            return f"{base}: {self.detail}"
        return base


class BackendClient:
    def __init__(self, base_url: str = BACKEND_BASE_URL, timeout: float = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _headers(self, token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _safe_detail(self, r: requests.Response) -> Any:
        ctype = (r.headers.get("content-type") or "").lower()
        if "application/json" in ctype:
            try:
                return r.json()
            except Exception:
                return r.text[:2000]
        return r.text[:2000]

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: Optional[str] = None,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        expected_status: Optional[int] = None,
        allow_statuses: Optional[set[int]] = None,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"

        try:
            r = self.session.request(
                method=method,
                url=url,
                headers=self._headers(token),
                json=json,
                data=data,
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise ApiError(
                status_code=0,
                message="Network error",
                detail=str(e),
                method=method,
                url=url,
            )

        if allow_statuses and r.status_code in allow_statuses:
            return r

        if expected_status is not None and r.status_code != expected_status:
            raise ApiError(
                status_code=r.status_code,
                message="Unexpected response status",
                detail=self._safe_detail(r),
                method=method,
                url=url,
            )

        if expected_status is None and r.status_code >= 400:
            raise ApiError(
                status_code=r.status_code,
                message="Request failed",
                detail=self._safe_detail(r),
                method=method,
                url=url,
            )

        return r

    # ---------- AUTH ----------
    def register(self, email: str, password: str) -> Dict[str, Any]:
        r = self._request(
            "POST",
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        return r.json()

    def login(self, email: str, password: str) -> str:
        r = self._request(
            "POST",
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        payload = r.json()
        token = payload.get("access_token")
        if not token:
            raise ApiError(
                status_code=500,
                message="No access_token in response",
                detail=payload,
                method="POST",
                url=f"{self.base_url}/api/auth/login",
            )
        return token

    # ---------- ML MODELS ----------
    def get_default_model(self) -> Dict[str, Any]:
        """
        Must be implemented in backend: GET /api/ml-models/default
        Should return MLModelOut including feature_names.
        """
        r = self._request("GET", "/api/ml-models/default")
        return r.json()

    def list_models(self) -> List[Dict[str, Any]]:
        r = self._request("GET", "/api/ml-models")
        return r.json()

    # ---------- WALLET ----------
    def get_balance(self, token: str) -> int:
        r = self._request("GET", "/api/wallet/balance", token=token)
        return int(r.json()["balance"])

    def topup(self, token: str, amount: int) -> Dict[str, Any]:
        r = self._request("POST", "/api/wallet/topup", token=token, json={"amount": amount})
        return r.json()
    
    # transactions history
    def get_transactions(self, token: str, limit: int = 20) -> List[Dict[str, Any]]:
        r = self._request("GET", f"/api/wallet/transactions?limit={int(limit)}", token=token)
        payload = r.json()
        return payload.get("items", [])

    # ---------- TASKS ----------
    def predict(self, token: str, answers: Dict[str, Any], model_id: Optional[int] = None) -> str:
        """
        IMPORTANT:
        - If model_id is None: do NOT send it at all.
          Backend will use PredictIn.model_id default (from schemas/env).
        """
        payload: Dict[str, Any] = {"answers": answers}
        if model_id is not None:
            payload["model_id"] = model_id

        r = self._request(
            "POST",
            "/api/tasks/predict",
            token=token,
            json=payload,
            allow_statuses={202, 422},
        )

        if r.status_code == 422:
            detail = r.json().get("detail", {})
            raise ApiError(
                status_code=422,
                message="Validation failed",
                detail=detail,
                method="POST",
                url=f"{self.base_url}/api/tasks/predict",
            )

        return r.json()["task_id"]

    def get_task(self, token: str, task_id: str) -> Dict[str, Any]:
        r = self._request("GET", f"/api/tasks/{task_id}", token=token)
        return r.json()

    def get_history(self, token: str) -> List[Dict[str, Any]]:
        r = self._request("GET", "/api/tasks/history", token=token)
        return r.json()
