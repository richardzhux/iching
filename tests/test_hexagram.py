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
