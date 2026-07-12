from datetime import datetime
from importlib import import_module

from iching.config import build_app_config
from iching.integrations.ai import _build_followup_session_context, _build_prompt
from iching.integrations.najia_repository import NajiaRepository
from iching.services.session import SessionService


def _najia_helpers():
    try:
        module = import_module("iching.core.najia")
    except ModuleNotFoundError:
        raise AssertionError("canonical Najia mechanics module is missing") from None
    return module.palace_element, module.six_relative_label, module.rebase_relation


def test_rebases_six_relatives_to_the_main_palace():
    palace_element, six_relative_label, rebase_relation = _najia_helpers()

    assert palace_element("震宫") == "木"
    assert six_relative_label("木", "金") == "官鬼"
    assert six_relative_label("木", "土") == "妻财"
    assert rebase_relation("父母戊申金", "震宫") == "官鬼戊申金"
    assert rebase_relation("官鬼戊戌土", "震宫") == "妻财戊戌土"


def test_repository_adapts_asymmetric_binary_and_line_position_columns():
    config = build_app_config(enable_ai=False)
    repository = NajiaRepository(config.paths.najia_db)

    entry = repository.get_by_bottom("100010")

    assert entry is not None
    assert entry.name == "水雷屯"
    assert repository.get_by_top("010001") is entry
    assert entry.binary_bottom_to_top == "100010"
    assert entry.binary_top_to_bottom == "010001"
    assert [line.position_top for line in entry.lines] == [1, 2, 3, 4, 5, 6]
    assert [line.position_bottom for line in entry.lines] == [6, 5, 4, 3, 2, 1]
    assert [line.position for line in entry.lines] == [6, 5, 4, 3, 2, 1]


def test_session_normalizes_changed_relations_gods_and_legacy_text():
    config = build_app_config(enable_ai=False)
    service = SessionService(config=config)

    result = service.create_session(
        topic="事业",
        user_question=None,
        method_key="x",
        manual_lines=[8, 7, 8, 9, 6, 8],
        timestamp=datetime(2026, 7, 2, 12, 0),
        use_current_time=False,
        enable_ai=False,
        interactive=False,
    )

    expected_relations = [
        "父母戊子水",
        "妻财戊戌土",
        "官鬼戊申金",
        "子孙戊午火",
        "妻财戊辰土",
        "兄弟戊寅木",
    ]
    expected_gods = ["青龙", "玄武", "白虎", "腾蛇", "勾陈", "朱雀"]

    assert result.najia_table["meta"]["main"]["name"] == "雷水解"
    assert result.najia_table["meta"]["changed"]["name"] == "坎为水"
    assert [row["changed_relation"] for row in result.najia_table["rows"]] == expected_relations
    assert [row["god"] for row in result.najia_table["rows"]] == expected_gods

    main_lines = result.najia_data["main"]["lines"]
    changed_lines = result.najia_data["changed"]["lines"]
    assert [line["god"] for line in main_lines] == expected_gods
    assert [line["god"] for line in changed_lines] == expected_gods
    assert [line["relation"] for line in changed_lines] == expected_relations
    assert all(line["hidden"] == "" for line in changed_lines)

    assert result.najia_data["block_text"] == result.najia_text
    text_rows = [
        line
        for line in result.najia_text.splitlines()
        if any(relation in line for relation in expected_relations)
    ]
    assert len(text_rows) == 6
    assert all(god in line for god, line in zip(expected_gods, text_rows))


def test_ai_context_uses_normalized_table_instead_of_source_gods():
    data = {
        "najia_data": {"main": {"lines": [{"god": "固定源六神"}]}},
        "najia_table": {"rows": [{"god": "青龙", "main_relation": "父母戊子水"}]},
    }

    prompt = _build_prompt(data)
    followup = _build_followup_session_context(data)

    assert "青龙" in prompt
    assert "青龙" in followup
    assert "固定源六神" not in prompt
    assert "固定源六神" not in followup
