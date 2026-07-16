from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from iching.integrations.supabase_client import SupabaseUser
from iching.web.chart_service import ChartArchiveService
from iching.web.models import MetaphysicsChartSaveRequest


USER_ID = "00000000-0000-0000-0000-000000000001"
SUBJECT_ID = "00000000-0000-0000-0000-000000000002"
CHART_ID = "00000000-0000-0000-0000-000000000003"

RULE_VERSIONS = {
    "calendar": "canonical-calendar-1",
    "pattern_bundle": "zzq-shen-canonical-v1",
    "pattern_digest": "8c41b4f22b8461526651b364d95144a74036c9e9a8606f1088eb53c4d356a523",
    "shensha": "shensha-2026.07-v2.1",
    "consumer": "metaphysics-consumer-2026.07-v4",
}


def test_chart_reads_are_always_scoped_to_the_authenticated_owner() -> None:
    client = Mock()
    client.select_rows.return_value = [{"id": CHART_ID, "subject": {"id": SUBJECT_ID}}]
    service = ChartArchiveService(client)

    record = service.fetch_chart(chart_id=CHART_ID, user=SupabaseUser(id=USER_ID))

    assert record["subject"]["id"] == SUBJECT_ID
    params = client.select_rows.call_args.kwargs["params"]
    assert params["id"] == f"eq.{CHART_ID}"
    assert params["user_id"] == f"eq.{USER_ID}"


def test_chart_updates_scope_both_subject_and_chart_to_the_owner() -> None:
    client = Mock()
    client.update_rows.side_effect = [
        [{"id": SUBJECT_ID}],
        [{"id": CHART_ID, "subject_id": SUBJECT_ID}],
    ]
    request = MetaphysicsChartSaveRequest.model_validate(
        {
            "id": CHART_ID,
            "chart_type": "bazi",
            "subject": {
                "id": SUBJECT_ID,
                "display_name": "测试命主",
                "birth_local_timestamp": "2004-06-26T04:00",
                "timezone": "Asia/Shanghai",
                "calendar_type": "solar",
                "gender": "male",
            },
            "birth_date": "2004-06-26",
            "day_pillar": "丙子",
            "input_snapshot": {"form": {}},
            "result_snapshot": {"chart": {}},
            "engine_name": "test",
            "engine_version": "1",
            "rules_version": "test-v1",
            "schema_version": 1,
        }
    )

    ChartArchiveService(client).save_chart(request=request, user=SupabaseUser(id=USER_ID))

    subject_params = client.update_rows.call_args_list[0].kwargs["params"]
    chart_params = client.update_rows.call_args_list[1].kwargs["params"]
    assert subject_params == {"id": f"eq.{SUBJECT_ID}", "user_id": f"eq.{USER_ID}"}
    assert chart_params == {"id": f"eq.{CHART_ID}", "user_id": f"eq.{USER_ID}"}


def test_schema_six_archive_is_returned_without_snapshot_migration() -> None:
    legacy_snapshot = {
        "chart": {"derived_schema_version": 6, "rules_version": "shensha-2026.07-v2.1", "bazi": "甲申 庚午 丙子 庚寅"},
        "derived_schema_version": 6,
    }
    row = {"id": CHART_ID, "schema_version": 6, "result_snapshot": deepcopy(legacy_snapshot), "subject": {"id": SUBJECT_ID}}
    client = Mock()
    client.select_rows.return_value = [row]

    record = ChartArchiveService(client).fetch_chart(chart_id=CHART_ID, user=SupabaseUser(id=USER_ID))

    assert record["schema_version"] == 6
    assert record["result_snapshot"] == legacy_snapshot
    assert "rule_versions" not in record["result_snapshot"]["chart"]


def test_schema_seven_snapshot_requires_and_preserves_rule_versions() -> None:
    payload = {
        "chart_type": "bazi",
        "subject": {
            "display_name": "测试命主",
            "birth_local_timestamp": "2004-06-26T04:00",
            "timezone": "Asia/Shanghai",
            "calendar_type": "solar",
            "gender": "male",
        },
        "birth_date": "2004-06-26",
        "day_pillar": "丙子",
        "input_snapshot": {"form": {}},
        "result_snapshot": {"chart": {"derived_schema_version": 7, "rule_versions": RULE_VERSIONS}},
        "engine_name": "canonical-bazi",
        "engine_version": "1",
        "rules_version": "shensha-2026.07-v2.1",
        "schema_version": 7,
    }

    request = MetaphysicsChartSaveRequest.model_validate(payload)
    assert request.schema_version == 7
    assert request.result_snapshot["chart"]["rule_versions"] == RULE_VERSIONS

    missing_versions = deepcopy(payload)
    missing_versions["result_snapshot"]["chart"].pop("rule_versions")
    with pytest.raises(ValidationError, match="schema 7"):
        MetaphysicsChartSaveRequest.model_validate(missing_versions)
