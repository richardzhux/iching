from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Load environment variables from the project .env if available.
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True, slots=True)
class PathConfig:
    """Holds all filesystem locations used by the application."""

    project_root: Path
    data_dir: Path
    gua_index_file: Path
    najia_db: Path
    interpretation_db: Path
    guaci_dir: Path
    takashima_dir: Path
    symbolic_dir: Path
    english_dir: Path
    archive_complete_dir: Path
    archive_acquittal_dir: Path

    def ensure_directories(self) -> None:
        """Create required directories if they are missing."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.interpretation_db.parent.mkdir(parents=True, exist_ok=True)
        self.guaci_dir.mkdir(parents=True, exist_ok=True)
        self.takashima_dir.mkdir(parents=True, exist_ok=True)
        self.symbolic_dir.mkdir(parents=True, exist_ok=True)
        self.english_dir.mkdir(parents=True, exist_ok=True)
        self.archive_complete_dir.mkdir(parents=True, exist_ok=True)
        self.archive_acquittal_dir.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Aggregate configuration for the application."""

    paths: PathConfig
    enable_ai: bool = True
    preferred_ai_model: Optional[str] = None


def _expand(path_value: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path_value)))).resolve()


def build_path_config() -> PathConfig:
    """Construct the path configuration from environment variables or defaults."""
    default_data_dir = PROJECT_ROOT / "data"
    data_dir = _expand(os.getenv("ICHING_DATA_DIR", default_data_dir))

    archive_base = _expand(
        os.getenv("ICHING_ARCHIVE_BASE", "~/Documents/Hexarchive")
    )
    archive_complete_dir = _expand(
        os.getenv("ICHING_ARCHIVE_COMPLETE", archive_base / "guilty")
    )
    archive_acquittal_dir = _expand(
        os.getenv("ICHING_ARCHIVE_ACQUITTAL", archive_base / "acquittal")
    )

    guaci_dir = _expand(os.getenv("ICHING_GUACI_DIR", data_dir / "guaci"))
    takashima_dir = _expand(
        os.getenv("ICHING_TAKASHIMA_DIR", data_dir / "takashima_structured")
    )
    symbolic_dir = _expand(os.getenv("ICHING_SYMBOLIC_DIR", data_dir / "symbolic"))
    english_dir = _expand(os.getenv("ICHING_ENGLISH_DIR", data_dir / "eng"))
    gua_index_file = _expand(
        os.getenv("ICHING_GUA_INDEX_FILE", data_dir / "guaxiang.txt")
    )
    najia_db = _expand(os.getenv("ICHING_NAJIA_DB", data_dir / "najia.db"))
    interpretation_db = _expand(
        os.getenv("ICHING_INTERPRETATION_DB", data_dir / "interpretations.db")
    )

    paths = PathConfig(
        project_root=PROJECT_ROOT,
        data_dir=data_dir,
        gua_index_file=gua_index_file,
        najia_db=najia_db,
        interpretation_db=interpretation_db,
        guaci_dir=guaci_dir,
        takashima_dir=takashima_dir,
        symbolic_dir=symbolic_dir,
        english_dir=english_dir,
        archive_complete_dir=archive_complete_dir,
        archive_acquittal_dir=archive_acquittal_dir,
    )
    paths.ensure_directories()
    return paths


def build_app_config(
    *,
    enable_ai: bool | None = None,
    preferred_ai_model: Optional[str] = None,
) -> AppConfig:
    """Load the full application configuration."""
    paths = build_path_config()
    ai_default = os.getenv("ICHING_ENABLE_AI", "1") not in {"0", "false", "False"}
    return AppConfig(
        paths=paths,
        enable_ai=ai_default if enable_ai is None else enable_ai,
        preferred_ai_model=preferred_ai_model
        or os.getenv("ICHING_AI_MODEL")
        or None,
    )


PATHS = build_path_config()
