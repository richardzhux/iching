from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_uses_reading_desk_identity_and_sample_reading():
    source = read("frontend/src/components/home/home-page.tsx")
    banned_phrases = [
        "From yarrow stalks to AI",
        "从蓍草到AI",
        "Tired of ChatGPT-style vagueness",
        "Coming Soon",
        "AI WORKBENCH",
        "DEEP ARCHIVAL RESEARCH",
        "五款模型",
    ]
    for phrase in banned_phrases:
        assert phrase not in source

    assert "bilingual reading desk" in source
    assert "source-grounded reading environment" in source
    assert "sampleReading" in source
    assert "Hexagram 3" in source
    assert "Hexagram 8" in source
    assert "/library" in source
    assert "not medical, legal, financial" in source


def test_workspace_has_graceful_backend_fallback_and_library_escape():
    workspace = read("frontend/src/components/workspace/cast-workspace.tsx")
    messages = read("frontend/src/i18n/messages.ts")
    english = read("frontend/src/i18n/catalog/en.ts")
    chinese = read("frontend/src/i18n/catalog/zh.ts")
    queries = read("frontend/src/lib/queries.ts")

    assert "Loading workspace configuration..." not in english
    assert "正在加载工作台配置" not in chinese
    assert "loadingConfigTitle" in messages
    assert "sampleReadingCta" in messages
    assert "libraryCta" in messages
    assert "toLocalePath(\"/library\")" in workspace
    assert "refetch" in workspace
    assert "retry: 1" in queries
    assert "throw new Error" not in workspace


def test_public_hexagram_library_routes_and_data_exist():
    library_data = read("frontend/src/lib/hexagram-library.ts")
    library_page = ROOT / "frontend/src/app/[locale]/library/page.tsx"
    detail_page = ROOT / "frontend/src/app/[locale]/hexagram/[slug]/page.tsx"

    assert library_page.exists()
    assert detail_page.exists()
    assert "HEXAGRAM_LIBRARY" in library_data
    assert library_data.count("number:") == 64
    assert "qian" in library_data
    assert "kun" in library_data
    assert "difficulty-at-the-beginning" in library_data
    assert "Source Library" in read("frontend/src/app/[locale]/library/page.tsx")
    assert "generateStaticParams" in read("frontend/src/app/[locale]/hexagram/[slug]/page.tsx")


def test_reading_packet_has_first_class_journal_and_source_evidence():
    results = read("frontend/src/components/workspace/results-panel.tsx")
    history = read("frontend/src/components/workspace/history-drawer.tsx")
    api_types = read("frontend/src/types/api.ts")

    assert "ReadingJournalPanel" in results
    assert "What actually happened?" in results
    assert "revisitAt" in results
    assert "source_ids" in api_types
    assert "Decision journal" not in history
    assert "Reading journal" in history


def test_hexagram_source_preview_spans_full_card_width():
    visual = read("frontend/src/components/workspace/hexagram-visual.tsx")

    assert "function HexagramSourcePreview" in visual
    assert "<HexagramSourcePreview" in visual
    assert "onActivePositionChange" in visual
    assert "sourcePreviewSection" in visual
    assert "max-w-3xl text-sm leading-6 text-muted-foreground" not in visual

    preview_call = visual.index("<HexagramSourcePreview")
    interactive_function = visual.index("function InteractiveHexagramLines")
    assert preview_call < interactive_function
