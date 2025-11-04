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
