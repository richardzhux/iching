from __future__ import annotations

from unittest.mock import Mock

from iching.integrations.supabase_client import SupabaseUser
from iching.web.chart_service import ChartArchiveService
from iching.web.models import MetaphysicsChartSaveRequest


USER_ID = "00000000-0000-0000-0000-000000000001"
SUBJECT_ID = "00000000-0000-0000-0000-000000000002"
CHART_ID = "00000000-0000-0000-0000-000000000003"


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
