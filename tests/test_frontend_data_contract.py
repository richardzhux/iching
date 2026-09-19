"""Durable frontend contracts: data completeness, locale parity, shipped config.

This file replaces ``test_frontend_premium_contract.py``, which asserted on
literal JSX substrings, exact CSS variable values and internal type names. Those
assertions locked the source text of a moment rather than any behaviour, so they
went red on every refactor and stopped being read. Interaction behaviour belongs
in ``frontend/e2e`` (Playwright); what remains checkable from Python is the data
the UI reads, the parity of the two locale catalogs, and the routes and
constants the product promises.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
LOCALES = ("en", "zh")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Locale parity
# --------------------------------------------------------------------------- #


def _catalog_keys(source: str) -> List[str]:
    """Flatten a catalog literal into dotted key paths.

    The catalogs are plain nested object literals, so brace depth tracking is
    enough. Values are ignored; only the shape has to match across locales.
    """
    body = source[source.index("= {") + 2 :]
    keys: List[str] = []
    stack: List[str] = []
    pending: str | None = None
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*|"[^"]+")\s*:\s*(.*)$', stripped)
        if match:
            name = match.group(1).strip('"')
            rest = match.group(2)
            if rest.startswith("{"):
                stack.append(name)
                pending = None
                if rest.rstrip().endswith("},"):
                    stack.pop()
                continue
            keys.append(".".join([*stack, name]))
            pending = None
            continue
        if stripped.startswith("}"):
            if stack:
                stack.pop()
            pending = None
    assert pending is None
    return keys


def test_locale_catalogs_expose_identical_key_sets():
    """A key present in one locale and missing in the other renders raw or blank."""
    catalogs: Dict[str, List[str]] = {
        locale: _catalog_keys(read(f"frontend/src/i18n/catalog/{locale}.ts"))
        for locale in LOCALES
    }
    english = set(catalogs["en"])
    chinese = set(catalogs["zh"])

    assert english, "english catalog parsed to zero keys; the parser needs updating"
    assert not english - chinese, f"missing from zh: {sorted(english - chinese)}"
    assert not chinese - english, f"missing from en: {sorted(chinese - english)}"


def test_locale_catalogs_have_no_empty_strings():
    for locale in LOCALES:
        source = read(f"frontend/src/i18n/catalog/{locale}.ts")
        assert ': ""' not in source, f"{locale} catalog has an empty string value"


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


def test_every_public_page_lives_under_the_locale_segment():
    """Pages outside ``[locale]`` bypass locale negotiation entirely."""
    app_dir = FRONTEND / "app"
    stray = [
        path.relative_to(FRONTEND).as_posix()
        for path in app_dir.rglob("page.tsx")
        if "[locale]" not in path.as_posix()
    ]
    assert stray == [], f"pages outside [locale]: {stray}"


def test_locale_routes_cover_every_navigation_target():
    navigation = read("frontend/src/components/navigation/primary-navigation.tsx")
    targets = set(re.findall(r'href:\s*"(/[a-z-]*)"', navigation))
    for target in targets:
        segment = target.strip("/")
        page = FRONTEND / "app" / "[locale]" / segment / "page.tsx" if segment else FRONTEND / "app" / "[locale]" / "page.tsx"
        assert page.exists(), f"navigation points at {target} with no page at {page}"


# --------------------------------------------------------------------------- #
# Shipped data completeness
# --------------------------------------------------------------------------- #


def test_hexagram_library_covers_all_sixty_four():
    library = read("frontend/src/lib/hexagram-library.ts")
    assert library.count("number:") == 64
    assert (FRONTEND / "app/[locale]/library/page.tsx").exists()
    assert (FRONTEND / "app/[locale]/hexagram/[slug]/page.tsx").exists()
    assert "generateStaticParams" in read(
        "frontend/src/app/[locale]/hexagram/[slug]/page.tsx"
    )


def test_hexagram_archive_has_one_module_per_hexagram():
    archive = read("frontend/src/lib/hexagram-archive.ts")
    archive_dir = FRONTEND / "lib" / "hexagram-archive-data"
    assert archive.count("    slug:") == 64
    assert len(list(archive_dir.glob("*.ts"))) == 64
    assert "HEXAGRAM_ARCHIVE_INDEX" in archive
    assert "HEXAGRAM_ARCHIVE_LOADERS" in archive


def test_archive_counts_match_the_interpretation_database():
    """The static archive summary is generated from the DB and must not drift."""
    import sqlite3

    archive = read("frontend/src/lib/hexagram-archive.ts")
    connection = sqlite3.connect(ROOT / "data" / "interpretations.db")
    try:
        total = connection.execute(
            "SELECT COUNT(*) FROM interpretation_entry WHERE is_current = 1"
        ).fetchone()[0]
        per_source = dict(
            connection.execute(
                "SELECT s.source_key, COUNT(*) FROM interpretation_entry e "
                "JOIN interpretation_source s ON s.id = e.source_id "
                "WHERE e.is_current = 1 GROUP BY s.source_key"
            )
        )
    finally:
        connection.close()

    assert f"totalEntries: {total}" in archive
    for source_key, count in per_source.items():
        assert f"{source_key}: {count}" in archive, (
            f"archive summary disagrees with the database for {source_key}"
        )


# --------------------------------------------------------------------------- #
# Constants the product documents
# --------------------------------------------------------------------------- #


def test_cloud_session_limit_is_documented_wherever_it_is_promised():
    assert 'ICHING_USER_SESSION_LIMIT", "500"' in read("src/iching/web/chat_service.py")
    assert "`ICHING_USER_SESSION_LIMIT` (default `500`)" in read("README.md")
    assert (
        "`ICHING_USER_SESSION_LIMIT` (saved sessions per user, default 500)"
        in read("docs/deployment.md")
    )


def test_supabase_retention_keeps_sessions_for_one_year():
    schema = read("docs/supabase-schema.sql")
    assert "365 days" in schema
    assert "90 days" not in schema
