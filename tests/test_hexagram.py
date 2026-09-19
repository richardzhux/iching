from pathlib import Path

from iching.config import PATHS
from iching.core.hexagram import Hexagram, load_hexagram_definitions


def test_hexagram_basic_properties():
    definitions = load_hexagram_definitions(PATHS.gua_index_file)
    lines = [7, 7, 7, 7, 7, 7]  # 乾卦
    hexagram = Hexagram(lines, definitions)

    assert hexagram.name.startswith("乾")
    assert hexagram.binary == "111111"

    text = hexagram.to_text(guaci_path=PATHS.guaci_dir)
    assert "本卦" in text
    assert "错卦" in text
    assert "对应的文件" not in text
    assert "内容:" not in text
    assert "变卦：没有动爻，故无变卦" in text


def test_hexagram_single_moving_line_focuses_on_that_line():
    definitions = load_hexagram_definitions(PATHS.gua_index_file)
    # Only初六动
    lines = [6, 7, 7, 7, 7, 7]
    hexagram = Hexagram(lines, definitions)
    text = hexagram.to_text(guaci_path=PATHS.guaci_dir)

    assert "对应的文件" not in text
    assert "内容:" not in text
    assert "初六" in text
    assert "九二爻辞" not in text
    assert "变卦:" in text


def test_hexagram_text_package_exposes_additional_sections():
    definitions = load_hexagram_definitions(PATHS.gua_index_file)
    lines = [6, 7, 8, 7, 7, 7]
    hexagram = Hexagram(lines, definitions)

    summary, sections, overview = hexagram.to_text_package(guaci_path=PATHS.guaci_dir)
    legacy_text = hexagram.to_text(guaci_path=PATHS.guaci_dir)

    assert summary == legacy_text
    assert sections, "expected structured sections for the hexagram text"
    assert any(section["importance"] == "secondary" for section in sections)
    assert all("visible_by_default" in section for section in sections)
    assert overview["lines"], "expected line overview metadata"


def test_hexagram_text_package_includes_takashima_sections():
    definitions = load_hexagram_definitions(PATHS.gua_index_file)
    lines = [7, 7, 7, 7, 7, 7]  # 乾卦，含用九
    hexagram = Hexagram(lines, definitions)

    _, sections, _ = hexagram.to_text_package(
        guaci_path=PATHS.guaci_dir,
        takashima_path=PATHS.takashima_dir,
    )

    takashima_sections = [
        section for section in sections if section.get("source") == "takashima"
    ]
    assert takashima_sections, "expected takashima sections to be included"
    assert any(section.get("line_key") == "1" for section in takashima_sections)
    assert any(section.get("line_key") == "all" for section in takashima_sections)


# --------------------------------------------------------------------------- #
# 取用 rule: which line carries the reading, and what kind of line it is
# --------------------------------------------------------------------------- #

import pytest

from iching.core.hexagram import drop_conflicting_change_note


def _definitions():
    return load_hexagram_definitions(PATHS.gua_index_file)


@pytest.mark.parametrize(
    "lines, rule, primary, secondary, moving",
    [
        ([7, 8, 7, 8, 7, 8], "none", None, (), False),
        ([9, 8, 7, 8, 7, 8], "one-moving", 1, (), True),
        # One yin and one yang moving: the yin line leads.
        ([6, 8, 7, 8, 9, 8], "two-moving", 1, (5,), True),
        # Two alike: the upper leads, the other is read alongside.
        ([9, 8, 7, 8, 9, 8], "two-moving", 5, (1,), True),
        ([9, 9, 7, 8, 9, 8], "three-moving", 2, (1, 5), True),
        # Four and five moving lines select a STATIC line.
        ([9, 9, 9, 8, 9, 8], "four-moving", 4, (6,), False),
        ([9, 9, 9, 6, 9, 8], "five-moving", 6, (), False),
        ([9, 9, 9, 9, 9, 9], "all-use", None, (), False),
        ([6, 6, 6, 6, 6, 6], "all-use", None, (), False),
        ([9, 6, 9, 6, 9, 6], "all-changed", None, (), False),
    ],
)
def test_line_selection_covers_every_moving_line_count(lines, rule, primary, secondary, moving):
    selection = Hexagram(lines, _definitions()).line_selection()

    assert selection.rule == rule
    assert selection.primary_line_no == primary
    assert selection.secondary_line_nos == secondary
    assert selection.primary_is_moving is moving


def test_four_and_five_moving_lines_are_not_labelled_as_moving():
    """They resolve to a static line; three call sites used to say 动爻."""
    for lines in ([9, 9, 9, 8, 9, 8], [9, 9, 9, 6, 9, 8]):
        selection = Hexagram(lines, _definitions()).line_selection()
        assert selection.line_role == "静爻"
        assert lines[selection.primary] not in (6, 9)


def test_secondary_lines_are_reported_not_discarded():
    """The classical rule names more than one line; only one used to survive."""
    selection = Hexagram([9, 9, 7, 8, 9, 8], _definitions()).line_selection()
    assert selection.secondary_line_nos == (1, 5)
    assert selection.describes_line(2) and selection.describes_line(5)


def test_use_lines_are_matched_by_structure_not_by_name():
    """乾/坤 carry 用九/用六 whatever the index file calls them."""
    definitions = dict(_definitions())
    definitions["111111"] = ("The Creative", "renamed")
    definitions["000000"] = ("The Receptive", "renamed")

    assert Hexagram([9] * 6, definitions).line_selection().rule == "all-use"
    assert Hexagram([6] * 6, definitions).line_selection().rule == "all-use"


# --------------------------------------------------------------------------- #
# Corpus notes that contradict the reading they sit inside
# --------------------------------------------------------------------------- #

_NOTE_TEXT = (
    "六四。需于血。\n"
    "象曰：顺以听也。\n"
    "\n"
    "六四爻动变得周易第43卦：泽天夬。这个卦是异卦相叠，故名为夬。\n"
    "\n"
    "需于血：坎卦为血。"
)


def test_change_note_survives_when_it_names_this_readings_changed_hexagram():
    kept = drop_conflicting_change_note(_NOTE_TEXT, "泽天夬")
    assert "泽天夬" in kept
    assert "需于血：坎卦为血。" in kept


def test_change_note_is_dropped_when_it_contradicts_the_changed_hexagram():
    cleaned = drop_conflicting_change_note(_NOTE_TEXT, "坤为地")
    assert "爻动变得周易第" not in cleaned
    assert "需于血：坎卦为血。" in cleaned
    assert "象曰：顺以听也。" in cleaned


def test_change_note_is_dropped_when_nothing_changes():
    cleaned = drop_conflicting_change_note(_NOTE_TEXT, None)
    assert "爻动变得周易第" not in cleaned


def test_rendered_reading_never_contradicts_its_own_changed_hexagram():
    from iching.services.session import SessionService

    service = SessionService(history_limit=0)
    # Four moving lines: 水天需 -> 坤为地, while every line slot's note names
    # the hexagram reached by moving that one line alone.
    hexagram = Hexagram([9, 9, 9, 8, 9, 8], service.definitions)
    summary, sections, _ = hexagram.to_text_package(
        guaci_path=service.config.paths.guaci_dir,
        takashima_path=service.config.paths.takashima_dir,
        interpretation_repo=service.interpretation_repo,
    )

    assert "爻动变得周易第" not in summary
    assert not [
        section
        for section in sections
        if section.get("content") and "爻动变得周易第" in str(section["content"])
    ]


def test_english_reading_shows_its_classical_sections():
    """english_commentary was hidden by source, leaving English readers nothing."""
    from iching.services.session import SessionService

    service = SessionService(history_limit=0)
    hexagram = Hexagram([9, 8, 7, 8, 7, 8], service.definitions)
    _, sections, _ = hexagram.to_text_package(
        guaci_path=service.config.paths.guaci_dir,
        takashima_path=service.config.paths.takashima_dir,
        interpretation_repo=service.interpretation_repo,
    )

    english = [s for s in sections if s["source"] == "english_commentary"]
    assert english, "no English commentary was collected at all"
    assert [s for s in english if s["visible_by_default"]]
    # And its titles are not half-Chinese.
    assert not [s for s in english if str(s["title"]).startswith("本卦")]
