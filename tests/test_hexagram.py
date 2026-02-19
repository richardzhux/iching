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
