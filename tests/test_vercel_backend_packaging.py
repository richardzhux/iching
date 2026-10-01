from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from iching.config import PATHS, build_app_config, build_path_config
from iching.integrations.interpretation_repository import InterpretationRepository


ROOT = Path(__file__).resolve().parents[1]


def _repository(db_path: Path, *, read_only: bool = False) -> InterpretationRepository:
    return InterpretationRepository(
        db_path=db_path,
        index_file=PATHS.gua_index_file,
        guaci_dir=PATHS.guaci_dir,
        takashima_dir=PATHS.takashima_dir,
        symbolic_dir=PATHS.symbolic_dir,
        english_structured_dir=PATHS.english_structured_dir,
        read_only=read_only,
    )


@pytest.fixture
def reference_db(tmp_path: Path) -> Path:
    target = tmp_path / "reference.db"
    _repository(target)
    return target


def test_resolving_config_does_not_create_data_or_archives(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ICHING_DATA_DIR", str(tmp_path / "missing-data"))
    monkeypatch.setenv("ICHING_ARCHIVE_BASE", str(tmp_path / "missing-archives"))
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("ICHING_REFERENCE_READ_ONLY", raising=False)

    paths = build_path_config()
    assert not paths.data_dir.exists()
    assert not paths.archive_complete_dir.exists()
    assert build_app_config().reference_read_only


def test_read_only_reference_does_not_create_a_missing_database(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "reference.db"
    with pytest.raises(FileNotFoundError, match="build_vercel_backend"):
        _repository(target, read_only=True)
    assert not target.parent.exists()


def test_read_only_reference_rejects_missing_schema(tmp_path: Path) -> None:
    target = tmp_path / "empty.db"
    with sqlite3.connect(target):
        pass
    with pytest.raises(RuntimeError, match="missing required columns"):
        _repository(target, read_only=True)


def test_read_only_reference_rejects_incomplete_commentary(reference_db: Path) -> None:
    with sqlite3.connect(reference_db) as conn:
        conn.execute(
            "DELETE FROM interpretation_entry WHERE source_id = "
            "(SELECT id FROM interpretation_source WHERE source_key = 'english_commentary')"
        )
    with pytest.raises(RuntimeError, match="english_commentary commentary is incomplete"):
        _repository(reference_db, read_only=True)


def test_packaged_reference_cannot_be_modified(reference_db: Path) -> None:
    before = reference_db.read_bytes()
    repo = _repository(reference_db, read_only=True)
    assert repo.count_slots() == 450
    assert repo.get_slot_content(hexagram_name="乾为天", source_key="guaci", slot_kind="use")
    assert repo.get_slot_content(hexagram_name="坤为地", source_key="guaci", slot_kind="use")
    with repo._connect() as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM interpretation_entry")
    with pytest.raises(PermissionError, match="read-only"):
        repo.sync_from_files()
    assert reference_db.read_bytes() == before


def test_fresh_hosted_app_import_and_readings_need_no_filesystem_writes(reference_db: Path, tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update({
        "VERCEL": "1",
        "ICHING_REFERENCE_READ_ONLY": "1",
        "ICHING_INTERPRETATION_DB": str(reference_db),
        "ICHING_ARCHIVE_BASE": str(tmp_path / "never-created"),
        "ICHING_WEB_ARCHIVE_ENABLED": "0",
        "ICHING_ENABLE_AI": "0",
        "ICHING_CASTING_SECRET": "synthetic-packaging-test-secret",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    script = """
import os, sys
sys.dont_write_bytecode = True
def deny_writes(event, args):
    if event == 'os.mkdir':
        raise AssertionError('runtime attempted mkdir')
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        raise AssertionError('runtime attempted a writable file open')
    if event == 'sqlite3.connect' and '?mode=ro' not in str(args[0]):
        raise AssertionError('runtime attempted a writable SQLite connection')
sys.addaudithook(deny_writes)
from app import app
from datetime import datetime
from zoneinfo import ZoneInfo
from iching.web.service import _SESSION_SERVICE
assert _SESSION_SERVICE.config.reference_read_only
assert len(_SESSION_SERVICE.definitions) == 64
for lines in ([9] * 6, [6] * 6):
    reading = _SESSION_SERVICE.create_session(topic='packaging fixture', user_question=None,
        method_key='x', lines_override=lines, timestamp=datetime(2024, 2, 10, 12, tzinfo=ZoneInfo('Asia/Shanghai')),
        use_current_time=False, enable_ai=False)
    assert reading.hex_text and reading.najia_text
assert any(route.path == '/api/health' for route in app.routes)
print('readonly startup and both use-line readings passed')
"""
    completed = subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert "passed" in completed.stdout
    assert not (tmp_path / "never-created").exists()


def test_casting_provenance_verifies_in_a_fresh_process() -> None:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "src"),
        "VERCEL": "1",
        "ICHING_CASTING_SECRET": "synthetic-cross-instance-test-secret",
    })
    signed = subprocess.run(
        [sys.executable, "-c", "from iching.web.casting_provenance import sign_cast; print(sign_cast('s', [7,8,9,6,7,8], '2024-02-10T12:00:00+08:00'))"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    ).stdout.strip()
    script = """
import json, sys
from iching.web.casting_provenance import resolve_line_source
print(json.dumps(resolve_line_source(method_key='s', lines=[7,8,9,6,7,8],
    timestamp='2024-02-10T12:00:00+08:00', casting_token=sys.argv[1], declared_source=None)))
"""
    checked = subprocess.run([sys.executable, "-c", script, signed], cwd=ROOT, env=env, capture_output=True, text=True, check=True)
    assert json.loads(checked.stdout) == "server_cast"
