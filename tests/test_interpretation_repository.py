from pathlib import Path

from iching.config import PATHS
from iching.integrations.interpretation_repository import (
    InterpretationRepository,
    _clean_english_structured_text,
)


def _build_repo(tmp_path: Path) -> InterpretationRepository:
    return InterpretationRepository(
        db_path=tmp_path / "interpretations-test.db",
        index_file=PATHS.gua_index_file,
        guaci_dir=PATHS.guaci_dir,
        takashima_dir=PATHS.takashima_dir,
        symbolic_dir=PATHS.symbolic_dir,
        english_structured_dir=PATHS.english_structured_dir,
    )


def test_interpretation_repository_seeds_fixed_slot_grid(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    assert repo.count_slots() == 450
    assert repo.count_entries("guaci") >= 448
    assert repo.count_entries("takashima") >= 448
    assert repo.count_entries("symbolic") >= 8
    assert repo.count_entries("english_commentary") >= 448


def test_interpretation_repository_keeps_use_slots_on_qian_kun(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    assert repo.get_slot_content(
        hexagram_name="乾为天",
        source_key="guaci",
        slot_kind="use",
    )
    assert repo.get_slot_content(
        hexagram_name="坤为地",
        source_key="guaci",
        slot_kind="use",
    )
    assert (
        repo.get_slot_content(
            hexagram_name="震为雷",
            source_key="guaci",
            slot_kind="use",
        )
        is None
    )


def test_interpretation_repository_orders_slots_bottom_to_top(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    entries = repo.list_entries(hexagram_name="震为雷")
    unique_slot_keys = []
    for entry in entries:
        if not unique_slot_keys or unique_slot_keys[-1] != entry.slot_key:
            unique_slot_keys.append(entry.slot_key)
    assert unique_slot_keys[0] == "51.gua"
    assert unique_slot_keys[1:7] == [f"51.line.{idx}" for idx in range(1, 7)]


def test_interpretation_repository_symbolic_is_sparse_and_gua_only(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)

    zhen_entries = repo.list_entries(
        hexagram_name="震为雷",
        source_keys=("symbolic",),
    )
    assert zhen_entries
    assert all(entry.slot_kind == "gua" for entry in zhen_entries)
    assert all(entry.slot_key == "51.gua" for entry in zhen_entries)

    tun_entries = repo.list_entries(
        hexagram_name="水雷屯",
        source_keys=("symbolic",),
    )
    assert tun_entries == []


def test_interpretation_repository_english_has_line_entries(tmp_path: Path) -> None:
    repo = _build_repo(tmp_path)
    entries = repo.list_entries(
        hexagram_name="乾为天",
        source_keys=("english_commentary",),
        locale="en-US",
    )
    assert entries
    assert entries[0].slot_key == "1.gua"
    assert any(entry.slot_kind == "line" and entry.line_no == 1 for entry in entries)


def test_clean_english_structured_text_reflows_hard_wrapped_lines() -> None:
    raw = (
        "Judgment\n"
        "Legge: Under the conditions of Clouded Perception be aware of the difficulty\n"
        "of your position and maintain firm correctness.\n"
        "Wilhelm/Baynes: Darkening of the Light. In adversity it furthers one to be\n"
        "persevering.\n"
    )
    cleaned = _clean_english_structured_text(raw)
    assert cleaned is not None
    assert "difficulty of your position" in cleaned
    assert "to be persevering." in cleaned
    assert "\nJudgment\nLegge:" not in cleaned
    assert "\nWilhelm/Baynes:" in cleaned


def test_clean_english_structured_text_preserves_structural_breaks() -> None:
    raw = (
        "COMMENTARY\n"
        "Legge: The lesson of the figure is to show\n"
        "how such an officer will conduct himself.\n"
        "King Wen was not of the line of Shang. Though opposed and persecuted\n"
        "by its sovereign, he could pursue his own course.\n"
        "M.L. Von Franz -- The Feminine in Fairytales\n"
        "A. You had clarity,\n"
        "then you lost it.\n"
    )
    cleaned = _clean_english_structured_text(raw)
    assert cleaned is not None
    assert "is to show how such an officer" in cleaned
    assert "persecuted by its sovereign" in cleaned
    assert "\nM.L. Von Franz -- The Feminine in Fairytales\n" in cleaned
    assert "\nA. You had clarity, then you lost it." in cleaned


def test_clean_english_structured_text_does_not_split_lowercase_colon() -> None:
    raw = (
        "Ritsema/Karcher: This hexagram says\n"
        "to: hide your brightness!\n"
    )
    cleaned = _clean_english_structured_text(raw)
    assert cleaned == "Ritsema/Karcher: This hexagram says to: hide your brightness!"
