from pathlib import Path

from iching.config import PATHS
from iching.integrations.interpretation_repository import InterpretationRepository


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
