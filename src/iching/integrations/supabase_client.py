from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


class SupabaseConfigurationError(RuntimeError):
    """Raised when Supabase credentials are missing but required."""


class SupabaseAuthError(RuntimeError):
    """Raised when Supabase access tokens cannot be verified."""


@dataclass(slots=True)
class SupabaseUser:
    id: str
    email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SupabaseRestClient:
    """Thin wrapper around Supabase REST + auth endpoints using httpx."""

    def __init__(
        self,
        *,
        project_url: Optional[str] = None,
        service_key: Optional[str] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.project_url = (project_url or os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_KEY") or ""
        self._timeout = httpx.Timeout(10.0)
        self._client = client or httpx.Client(timeout=self._timeout)

    @property
    def enabled(self) -> bool:
        return bool(self.project_url and self.service_key)

    @property
    def rest_base(self) -> str:
        if not self.enabled:
            raise SupabaseConfigurationError("Supabase REST endpoint not configured.")
        return f"{self.project_url}/rest/v1"

    @property
    def auth_base(self) -> str:
        if not self.enabled:
            raise SupabaseConfigurationError("Supabase Auth endpoint not configured.")
        return f"{self.project_url}/auth/v1"

    def verify_access_token(self, token: str) -> SupabaseUser:
        if not self.enabled:
            raise SupabaseConfigurationError("Supabase credentials missing for auth verification.")
        if not token:
            raise SupabaseAuthError("Missing Supabase access token.")
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {token}",
        }
        response = self._client.get(f"{self.auth_base}/user", headers=headers)
        if response.status_code != 200:
            raise SupabaseAuthError("Supabase token verification failed.")
        payload = response.json()
        user_id = payload.get("id")
        if not user_id:
            raise SupabaseAuthError("Supabase response missing user id.")
        return SupabaseUser(
            id=user_id,
            email=payload.get("email"),
            metadata=payload.get("user_metadata"),
        )

    def fetch_session(self, *, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        headers = self._service_headers()
        params = {
            "session_id": f"eq.{session_id}",
            "user_id": f"eq.{user_id}",
            "limit": "1",
            "select": "*",
        }
        response = self._client.get(f"{self.rest_base}/sessions", params=params, headers=headers)
        response.raise_for_status()
        records = response.json()
        return records[0] if records else None

    def fetch_session_any(self, *, session_id: str) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        headers = self._service_headers()
        params = {
            "session_id": f"eq.{session_id}",
            "limit": "1",
            "select": "*",
        }
        response = self._client.get(f"{self.rest_base}/sessions", params=params, headers=headers)
        response.raise_for_status()
        records = response.json()
        return records[0] if records else None

    def upsert_session(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        headers = self._service_headers()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        response = self._client.post(f"{self.rest_base}/sessions", headers=headers, json=payload)
        response.raise_for_status()
        records = response.json()
        return records[0] if records else None

    def update_session(self, session_id: str, user_id: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        headers = self._service_headers()
        headers["Prefer"] = "resolution=merge-duplicates"
        params = {
            "session_id": f"eq.{session_id}",
            "user_id": f"eq.{user_id}",
        }
        response = self._client.patch(
            f"{self.rest_base}/sessions", params=params, headers=headers, json=payload
        )
        response.raise_for_status()

    def update_session_any(self, session_id: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        headers = self._service_headers()
        headers["Prefer"] = "resolution=merge-duplicates"
        params = {
            "session_id": f"eq.{session_id}",
        }
        response = self._client.patch(
            f"{self.rest_base}/sessions", params=params, headers=headers, json=payload
        )
        response.raise_for_status()

    def insert_chat_messages(self, records: List[Dict[str, Any]]) -> None:
        if not self.enabled or not records:
            return
        headers = self._service_headers()
        headers["Prefer"] = "resolution=merge-duplicates"
        response = self._client.post(
            f"{self.rest_base}/chat_messages",
            headers=headers,
            json=records,
        )
        response.raise_for_status()

    def fetch_chat_messages(self, *, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        headers = self._service_headers()
        params = {
            "session_id": f"eq.{session_id}",
            "user_id": f"eq.{user_id}",
            "order": "created_at.asc",
            "select": "*",
        }
        response = self._client.get(
            f"{self.rest_base}/chat_messages",
            params=params,
            headers=headers,
        )
        response.raise_for_status()
        items = response.json()
        return items if isinstance(items, list) else []

    def delete_session(self, session_id: str, user_id: str) -> None:
        if not self.enabled:
            return
        headers = self._service_headers()
        params = {
            "session_id": f"eq.{session_id}",
            "user_id": f"eq.{user_id}",
        }
        response = self._client.delete(f"{self.rest_base}/sessions", params=params, headers=headers)
        response.raise_for_status()

    def list_session_ids(self, *, user_id: str, limit: int, offset: int) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        headers = self._service_headers()
        params = {
            "user_id": f"eq.{user_id}",
            "order": "updated_at.desc",
            "select": "session_id",
            "limit": str(max(0, limit)),
            "offset": str(max(0, offset)),
        }
        response = self._client.get(f"{self.rest_base}/sessions", params=params, headers=headers)
        response.raise_for_status()
        records = response.json()
        return records if isinstance(records, list) else []

    def list_sessions_page(
        self,
        *,
        limit: int,
        offset: int,
        select: str = "session_id,payload_snapshot,updated_at,user_id",
    ) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        headers = self._service_headers()
        params = {
            "order": "updated_at.desc",
            "select": select,
            "limit": str(max(0, limit)),
            "offset": str(max(0, offset)),
        }
        response = self._client.get(f"{self.rest_base}/sessions", params=params, headers=headers)
        response.raise_for_status()
        records = response.json()
        return records if isinstance(records, list) else []

    def _service_headers(self) -> Dict[str, str]:
        if not self.enabled:
            raise SupabaseConfigurationError("Supabase credentials missing.")
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
