from iching.config import build_app_config
from iching.services.session import SessionService


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
