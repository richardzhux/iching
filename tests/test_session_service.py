from datetime import datetime
from types import SimpleNamespace

import iching.core.divination as divination
from iching.config import build_app_config
from iching.integrations.ai import AIResponseData
from iching.integrations.najia_repository import NajiaRepository
from iching.services.session import SessionService, _build_najia_table


def test_console_uses_one_timestamp_for_meihua_lines_and_session(monkeypatch):
    class FrozenWallClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2031, 1, 2, 23, 45, tzinfo=tz)

    cast_time = datetime(2026, 7, 12, 10, 30)
    time_calls = []
    captured = {}
    answers = iter(("1", "n", "m", "n", "n"))
    service = SessionService(config=build_app_config(enable_ai=False))

    def fake_get_current_time():
        time_calls.append(None)
        return cast_time

    def fake_create_session(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            current_time_str="2026.07.12 10:30",
            bazi_output="",
            elements_output="",
            hex_text="",
            najia_text="",
            ai_analysis=None,
        )

    monkeypatch.setattr(divination, "datetime", FrozenWallClock)
    monkeypatch.setattr(divination.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr("iching.services.session.get_current_time", fake_get_current_time)
    monkeypatch.setattr(service, "create_session", fake_create_session)

    service.run_console(
        input_func=lambda _prompt: next(answers),
        print_func=lambda _text: None,
        enable_ai=False,
    )

    assert len(time_calls) == 1
    assert captured["timestamp"] == cast_time
    assert captured["use_current_time"] is False
    assert captured["lines_override"] == [8, 7, 8, 6, 8, 8]


def test_session_service_uses_custom_timestamp_for_meihua_lines(monkeypatch):
    class FrozenWallClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2031, 1, 2, 23, 45, tzinfo=tz)

    monkeypatch.setattr(divination, "datetime", FrozenWallClock)
    cast_time = datetime(2026, 7, 12, 10, 30)
    service = SessionService(config=build_app_config(enable_ai=False))

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="m",
        use_current_time=False,
        timestamp=cast_time,
        enable_ai=False,
        interactive=False,
    )

    assert result.current_time_str == "2026.07.12 10:30"
    assert result.lines == [8, 7, 8, 6, 8, 8]


def _assert_brief_contract(brief):
    assert brief["headline"]
    assert brief["stance"]
    assert brief["plain_language"]
    assert brief["evidence"]
    assert brief["key_passages"]
    assert brief["source_passages"]
    assert brief["archive_sources"]
    assert brief["timing"]
    assert brief["actions"]
    assert brief["risks"]
    assert brief["followup_prompts"]
    assert brief["personal_context"]["status"] == "reserved"
    assert {"source_id", "excerpt", "plain_language", "source", "why_it_matters"} <= set(brief["key_passages"][0])
    assert brief["key_passages"][0]["source_id"]


def test_session_service_manual_lines_without_ai():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        manual_lines=[7, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    assert result.topic == "事业"
    assert result.lines == [7, 8, 7, 8, 7, 8]
    assert "najia_data" in result.to_dict()
    assert "najia_text" in result.to_dict()
    assert "青龙" in result.najia_text
    assert result.ai_analysis is None
    assert "起卦时间" in result.full_text


def test_session_service_uses_one_normalized_najia_payload_for_ai(monkeypatch):
    captured = {}

    def fake_start_analysis(data, **kwargs):
        captured.update(data)
        return None

    monkeypatch.setattr("iching.services.session.start_analysis", fake_start_analysis)
    config = build_app_config(enable_ai=True)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question="何时推进？",
        method_key="x",
        manual_lines=[8, 7, 8, 9, 6, 8],
        timestamp=datetime(2026, 7, 2, 12, 0),
        use_current_time=False,
        enable_ai=True,
        interactive=False,
    )

    assert captured["najia_table"] == result.najia_table
    assert captured["najia_data"] == result.najia_data
    assert captured["najia_text"] == result.najia_text
    assert captured["najia_data"]["block_text"] == captured["najia_text"]


def test_najia_table_does_not_fall_back_to_source_gods_for_unknown_day_stem():
    config = build_app_config(enable_ai=False)
    repository = NajiaRepository(config.paths.najia_db)
    main_entry = repository.get_by_bottom("010100")

    table = _build_najia_table(main_entry, None, [], "unknown")

    assert main_entry is not None
    assert [row["god"] for row in table["rows"]] == ["", "", "", "", "", ""]


def test_session_service_builds_fallback_reading_brief_without_ai():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question="是否应该推进这个合作？",
        method_key="x",
        manual_lines=[7, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    _assert_brief_contract(result.reading_brief)
    assert result.reading_brief["headline"].startswith("事业")
    assert "合作" in result.reading_brief["plain_language"]


def test_session_service_preserves_user_context_in_payload_and_brief():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question="是否应该推进这个合作？",
        user_context="对方催得很急，但我还没有看到预算和负责人。",
        method_key="x",
        manual_lines=[7, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    assert result.user_context == "对方催得很急，但我还没有看到预算和负责人。"
    assert result.to_dict()["user_context"] == "对方催得很急，但我还没有看到预算和负责人。"
    assert "预算" in result.reading_brief["plain_language"]


def test_session_service_brief_exposes_source_passages_and_archive_coverage():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question="是否应该推进这个合作？",
        method_key="x",
        manual_lines=[9, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    passages = result.reading_brief["source_passages"]
    assert passages
    assert {"source_id", "slot_key", "source", "source_label", "title", "content", "citation"} <= set(passages[0])
    assert passages[0]["source_id"] == f"{passages[0]['slot_key']}::{passages[0]['source']}"
    assert any(item["source"] == "takashima" for item in passages)
    key_source_ids = {item["source_id"] for item in result.reading_brief["key_passages"]}
    passage_source_ids = {item["source_id"] for item in passages}
    assert key_source_ids <= passage_source_ids
    coverage = result.reading_brief["archive_sources"]
    assert coverage["total_passages"] >= len(passages)
    assert "guaci" in coverage["sources"]


def test_session_service_reading_brief_tracks_moving_line_evidence():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="财运",
        user_question=None,
        method_key="x",
        manual_lines=[9, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    _assert_brief_contract(result.reading_brief)
    evidence_text = "\n".join(item["basis"] for item in result.reading_brief["evidence"])
    assert "动爻" in evidence_text
    key_text = "\n".join(item["why_it_matters"] for item in result.reading_brief["key_passages"])
    assert "动爻" in key_text
    assert all(item["section_kind"] == "line" for item in result.reading_brief["key_passages"])
    assert all(item["role"] == "primary" for item in result.reading_brief["key_passages"])
    assert any(item.get("source_ids") for item in result.reading_brief["evidence"])


def test_session_service_reading_brief_handles_no_moving_lines():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="整体运势",
        user_question=None,
        method_key="x",
        manual_lines=[7, 8, 7, 8, 7, 8],
        enable_ai=False,
        interactive=False,
    )

    _assert_brief_contract(result.reading_brief)
    evidence_text = "\n".join(item["basis"] for item in result.reading_brief["evidence"])
    assert "卦辞" in evidence_text
    key_text = "\n".join(item["why_it_matters"] for item in result.reading_brief["key_passages"])
    assert "卦辞" in key_text
    assert all(item["section_kind"] == "top" for item in result.reading_brief["key_passages"])


def test_session_service_reading_brief_handles_all_moving_qian_kun():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    qian = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        manual_lines=[9, 9, 9, 9, 9, 9],
        enable_ai=False,
        interactive=False,
    )
    kun = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        manual_lines=[6, 6, 6, 6, 6, 6],
        enable_ai=False,
        interactive=False,
    )

    _assert_brief_contract(qian.reading_brief)
    _assert_brief_contract(kun.reading_brief)
    assert any("用九" in item["basis"] for item in qian.reading_brief["evidence"])
    assert any("用六" in item["basis"] for item in kun.reading_brief["evidence"])
    assert any("用九" in item["why_it_matters"] for item in qian.reading_brief["key_passages"])
    assert any("用六" in item["why_it_matters"] for item in kun.reading_brief["key_passages"])
    assert all(item["line_key"] == "all" for item in qian.reading_brief["key_passages"])
    assert all(item["line_key"] == "all" for item in kun.reading_brief["key_passages"])


def test_session_service_reading_brief_uses_ai_summary_when_available(monkeypatch):
    def fake_start_analysis(*args, **kwargs):
        return AIResponseData(
            text=(
                "# 一句话结论\n"
                "- 利成，先小后大。\n\n"
                "# 应期与条件\n"
                "- 主应期：三日内｜条件：对方给出明确资源｜置信度：71%\n\n"
                "# 行动建议\n"
                "- 动作：先验证核心条件｜节奏：今天｜观察指标：是否有人负责\n\n"
                "# 风险与转折信号\n"
                "- 对方继续含糊则转弱。\n\n"
                "# 继续追问\n"
                "- 哪个条件最先验证？"
            ),
            response_id="resp_test",
            usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )

    monkeypatch.setattr("iching.services.session.start_analysis", fake_start_analysis)
    config = build_app_config(enable_ai=True)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question="是否应该推进这个合作？",
        method_key="x",
        manual_lines=[7, 8, 7, 8, 7, 8],
        enable_ai=True,
        interactive=False,
    )

    _assert_brief_contract(result.reading_brief)
    assert "利成" in result.reading_brief["headline"]
    assert result.reading_brief["timing"][0]["window"] == "三日内"
    assert result.reading_brief["timing"][0]["confidence"] == 71
    assert result.reading_brief["actions"][0]["action"] == "先验证核心条件"
    assert result.reading_brief["risks"][0] == "对方继续含糊则转弱。"
    assert result.reading_brief["followup_prompts"][0] == "哪个条件最先验证？"


def test_session_service_marks_relevant_slots_primary_across_sources():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        # 震为雷，无动爻 -> relevance on 本卦卦辞
        manual_lines=[7, 8, 8, 7, 8, 8],
        enable_ai=False,
        interactive=False,
    )

    primary = [section for section in result.hex_sections if section.get("visible_by_default")]
    assert any(
        section.get("source") == "guaci" and section.get("section_kind") == "top"
        for section in primary
    )
    assert any(
        section.get("source") == "takashima" and section.get("section_kind") == "top"
        for section in primary
    )
    assert any(
        section.get("source") == "symbolic" and section.get("section_kind") == "top"
        for section in primary
    )
    assert any(
        section.get("source") == "english_commentary" and not section.get("visible_by_default")
        for section in result.hex_sections
    )


def test_session_service_keeps_yongjiu_when_qian_all_lines_moving():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        # 乾卦六爻全动
        manual_lines=[9, 9, 9, 9, 9, 9],
        enable_ai=False,
        interactive=False,
    )

    primary = [section for section in result.hex_sections if section.get("visible_by_default")]
    assert any(
        section.get("source") == "guaci" and section.get("line_key") == "all"
        for section in primary
    )
    assert any(
        section.get("source") == "takashima" and section.get("line_key") == "all"
        for section in primary
    )


def test_session_service_keeps_yongliu_when_kun_all_lines_moving():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        # 坤卦六爻全动
        manual_lines=[6, 6, 6, 6, 6, 6],
        enable_ai=False,
        interactive=False,
    )

    primary = [section for section in result.hex_sections if section.get("visible_by_default")]
    assert any(
        section.get("source") == "guaci" and section.get("line_key") == "all"
        for section in primary
    )
    assert any(
        section.get("source") == "takashima" and section.get("line_key") == "all"
        for section in primary
    )
