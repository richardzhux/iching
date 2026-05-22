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


def test_results_source_review_uses_drawer_not_archive_tab_or_inline_expansion():
    results = read("frontend/src/components/workspace/results-panel.tsx")
    store = read("frontend/src/lib/store.ts")

    assert '<TabsTrigger value="archive">' not in results
    assert '<TabsContent value="archive">' not in results
    assert 'setResultsTab("archive")' not in results
    assert "scrollIntoView" not in results
    assert "SourceReaderSheet" in results
    assert "<SourceReaderSheet" in results
    assert "activeSourceId" in results
    assert "onSourceSelect={openSourceReader}" in results
    assert "function ArchiveComparisonPanel" not in results
    assert 'value === "archive"' not in store
    assert 'export type ResultsTab = "summary" | "hex" | "ai"' in store


def test_mechanics_source_review_no_long_inline_archive_expansion():
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert "function HexResultBlock({ result, brief, onSourceSelect }" in results
    assert "brief: ReadingBrief" in results
    assert "setShowFull" not in results
    assert "aria-expanded={showFull}" not in results
    assert "secondarySections.length" in results
    assert "onSourceSelect(sectionSourceIdForDrawer" in results


def test_guidance_key_passages_are_highlighted_as_decisive_interpretation():
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert "keyPassageHighlightSection" in results
    assert "border-amber" in results
    assert "卦辞解析" in results
    assert "Decisive passage analysis" in results
    assert "bg-amber" in results


def test_mechanics_page_has_professional_cast_logic_not_archive_replica():
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert "function MechanicsInsightPanel" in results
    assert "<MechanicsInsightPanel" in results
    assert "断法结构" in results
    assert "Cast logic" in results
    assert "爻变诊断" in results
    assert "Line movement" in results
    assert "重点段落解析" in results
    assert "显示补充" in results
    assert "sectionSourceIdForDrawer" in results
    assert results.index("<MechanicsInsightPanel") < results.index("<HexSectionGroup")


def test_hexagram_archive_data_organizes_all_sources_by_hexagram():
    archive_path = ROOT / "frontend/src/lib/hexagram-archive.ts"
    archive_data_dir = ROOT / "frontend/src/lib/hexagram-archive-data"
    assert archive_path.exists()
    assert archive_data_dir.exists()

    archive = archive_path.read_text(encoding="utf-8")
    qian_archive = (archive_data_dir / "qian.ts").read_text(encoding="utf-8")

    assert "HEXAGRAM_ARCHIVE_INDEX" in archive
    assert "HEXAGRAM_ARCHIVE_LOADERS" in archive
    assert archive.count("    slug:") == 64
    assert len(list(archive_data_dir.glob("*.ts"))) == 64
    assert "totalEntries: 1356" in archive
    assert "canonicalSlotCount: 450" in archive
    assert "sourceCounts" in archive
    assert "guaci: 450" in archive
    assert "takashima: 450" in archive
    assert "english_commentary: 448" in archive
    assert "symbolic: 8" in archive
    assert "slotKey" in qian_archive
    assert "slotKind" in qian_archive
    assert "lineNo" in qian_archive
    assert "useKind" in qian_archive
    assert "content" in qian_archive


def test_library_page_is_a_precise_study_index_not_only_cards():
    library_page = read("frontend/src/app/[locale]/library/page.tsx")

    assert "HEXAGRAM_ARCHIVE_SUMMARY" in library_page
    assert "getHexagramArchiveSummary" in library_page
    assert "450 canonical slots" in library_page
    assert "1,356 source entries" in library_page
    assert "学习库" in library_page
    assert "资料完整度" in library_page
    assert "sourceCounts" in library_page
    assert "canonicalSlotCount" in library_page


def test_hexagram_detail_page_renders_a_library_study_page_by_slot():
    detail_page = read("frontend/src/app/[locale]/hexagram/[slug]/page.tsx")

    assert "getHexagramArchive" in detail_page
    assert "await getHexagramArchive" in detail_page
    assert "ArchiveSlotSection" in detail_page
    assert "SourceEntryCard" in detail_page
    assert "Study table" in detail_page
    assert "学习目录" in detail_page
    assert "groupArchiveEntriesBySlot" in detail_page
    assert "本卦卦辞" in detail_page
    assert "爻位资料" in detail_page
    assert "用九 / 用六" in detail_page
    assert "whitespace-pre-wrap" in detail_page
    assert "sourceCounts" in detail_page
