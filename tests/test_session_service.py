from iching.config import build_app_config
from iching.integrations.ai import AIResponseData
from iching.services.session import SessionService


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
