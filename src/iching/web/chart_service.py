from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from iching.integrations.supabase_client import SupabaseRestClient, SupabaseUser
from iching.web.models import MetaphysicsChartSaveRequest


class ChartArchiveService:
    """Private, owner-scoped persistence for BaZi and Zi Wei chart snapshots."""

    def __init__(self, client: SupabaseRestClient) -> None:
        self.client = client

    def authenticate(self, token: str) -> SupabaseUser:
        return self.client.verify_access_token(token)

    def save_chart(
        self,
        *,
        request: MetaphysicsChartSaveRequest,
        user: SupabaseUser,
    ) -> Dict[str, Any]:
        subject_payload = self._subject_payload(request, user.id)
        subject_id = self._optional_uuid(request.subject.id, "subject id")
        if subject_id:
            subject_rows = self.client.update_rows(
                "chart_subjects",
                params={"id": f"eq.{subject_id}", "user_id": f"eq.{user.id}"},
                payload=subject_payload,
            )
            if len(subject_rows) != 1:
                raise ValueError("命主档案不存在或不属于当前账户。")
            subject = subject_rows[0]
        else:
            subject = self.client.insert_row("chart_subjects", subject_payload)
            subject_id = str(subject["id"])

        chart_payload: Dict[str, Any] = {
            "user_id": user.id,
            "subject_id": subject_id,
            "chart_type": request.chart_type,
            "title": self._clean_text(request.title),
            "birth_date": request.birth_date.isoformat(),
            "day_pillar": self._clean_text(request.day_pillar),
            "input_snapshot": request.input_snapshot,
            "result_snapshot": request.result_snapshot,
            "engine_name": request.engine_name,
            "engine_version": request.engine_version,
            "rules_version": request.rules_version,
            "schema_version": request.schema_version,
            "last_opened_at": datetime.now(timezone.utc).isoformat(),
        }
        chart_id = self._optional_uuid(request.id, "chart id")
        if chart_id:
            chart_rows = self.client.update_rows(
                "metaphysics_charts",
                params={"id": f"eq.{chart_id}", "user_id": f"eq.{user.id}"},
                payload=chart_payload,
            )
            if len(chart_rows) != 1:
                raise ValueError("命盘不存在或不属于当前账户。")
            chart = chart_rows[0]
        else:
            chart = self.client.insert_row("metaphysics_charts", chart_payload)
        return self._record(chart, subject)

    def fetch_chart(self, *, chart_id: str, user: SupabaseUser) -> Dict[str, Any]:
        normalized_id = self._required_uuid(chart_id, "chart id")
        rows = self.client.select_rows(
            "metaphysics_charts",
            params={
                "id": f"eq.{normalized_id}",
                "user_id": f"eq.{user.id}",
                "select": "*,subject:chart_subjects!metaphysics_charts_subject_owner_fk(*)",
                "limit": "1",
            },
        )
        if not rows:
            raise ValueError("命盘不存在或不属于当前账户。")
        row = rows[0]
        subject = row.pop("subject", None)
        if not isinstance(subject, dict):
            raise RuntimeError("命盘缺少命主档案。")
        return self._record(row, subject)

    def list_charts(self, *, user: SupabaseUser, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.client.select_rows(
            "metaphysics_charts",
            params={
                "user_id": f"eq.{user.id}",
                "select": (
                    "id,subject_id,chart_type,title,birth_date,day_pillar,engine_name,"
                    "engine_version,pinned,created_at,updated_at,"
                    "subject:chart_subjects!metaphysics_charts_subject_owner_fk(display_name,birth_place)"
                ),
                "order": "updated_at.desc,id.desc",
                "limit": str(max(1, min(limit, 200))),
            },
        )
        summaries: List[Dict[str, Any]] = []
        for row in rows:
            subject = row.pop("subject", None)
            subject_data = subject if isinstance(subject, dict) else {}
            summaries.append(
                {
                    **row,
                    "display_name": subject_data.get("display_name"),
                    "birth_place": subject_data.get("birth_place"),
                }
            )
        return summaries

    def delete_chart(self, *, chart_id: str, user: SupabaseUser) -> None:
        normalized_id = self._required_uuid(chart_id, "chart id")
        deleted = self.client.delete_rows(
            "metaphysics_charts",
            params={
                "id": f"eq.{normalized_id}",
                "user_id": f"eq.{user.id}",
                "select": "id,subject_id",
            },
        )
        if len(deleted) != 1:
            raise ValueError("命盘不存在或不属于当前账户。")
        subject_id = str(deleted[0]["subject_id"])
        remaining = self.client.select_rows(
            "metaphysics_charts",
            params={
                "subject_id": f"eq.{subject_id}",
                "user_id": f"eq.{user.id}",
                "select": "id",
                "limit": "1",
            },
        )
        if not remaining:
            self.client.delete_rows(
                "chart_subjects",
                params={"id": f"eq.{subject_id}", "user_id": f"eq.{user.id}"},
            )

    def _subject_payload(self, request: MetaphysicsChartSaveRequest, user_id: str) -> Dict[str, Any]:
        subject = request.subject
        try:
            zone = ZoneInfo(subject.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("无效的 IANA 时区。") from exc
        local_timestamp = subject.birth_local_timestamp
        if local_timestamp.tzinfo is not None:
            local_timestamp = local_timestamp.astimezone(zone).replace(tzinfo=None)
        offset = local_timestamp.replace(tzinfo=zone).utcoffset()
        if offset is None:
            raise ValueError("无法确定出生时刻的时区偏移。")
        return {
            "user_id": user_id,
            "display_name": self._clean_text(subject.display_name),
            "birth_local_timestamp": local_timestamp.isoformat(timespec="minutes"),
            "timezone": subject.timezone,
            "utc_offset_minutes": int(offset.total_seconds() // 60),
            "calendar_type": subject.calendar_type,
            "gender": subject.gender,
            "birth_place": self._clean_text(subject.birth_place),
            "location_id": self._clean_text(subject.location_id),
            "latitude": subject.latitude,
            "longitude": subject.longitude,
        }

    @staticmethod
    def _record(chart: Dict[str, Any], subject: Dict[str, Any]) -> Dict[str, Any]:
        return {**chart, "subject": subject}

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None

    @staticmethod
    def _required_uuid(value: str, label: str) -> str:
        try:
            return str(UUID(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {label}.") from exc

    @classmethod
    def _optional_uuid(cls, value: str | None, label: str) -> str | None:
        return cls._required_uuid(value, label) if value else None
