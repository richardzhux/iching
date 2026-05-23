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


def test_production_hardening_uses_real_domain_and_no_stale_domain():
    api = read("frontend/src/lib/api.ts")
    env = read("frontend/src/lib/env.ts")
    sitemap = read("frontend/src/app/sitemap.ts")
    robots = read("frontend/src/app/robots.ts")
    repo_text = "\n".join(
        [
            read("frontend/src/lib/env.ts"),
            read("frontend/src/app/sitemap.ts"),
            read("frontend/src/app/robots.ts"),
            read("frontend/src/app/[locale]/method/page.tsx"),
        ]
    )

    assert "127.0.0.1" not in api
    assert "NEXT_PUBLIC_API_BASE_URL" in env
    assert "Missing NEXT_PUBLIC_API_BASE_URL" in env
    assert "iching.richardzhux.com" in env
    assert "stateofiching.com" not in repo_text
    assert "MetadataRoute.Sitemap" in sitemap
    assert "MetadataRoute.Robots" in robots


def test_imperial_amethyst_theme_is_sitewide_and_guarded():
    globals_css = read("frontend/src/app/globals.css")
    workspace = read("frontend/src/components/workspace/cast-workspace.tsx")
    cast_form = read("frontend/src/components/workspace/cast-form.tsx")
    themed_surfaces = "\n".join(
        [
            globals_css,
            workspace,
            cast_form,
            read("frontend/src/components/workspace/hexagram-visual.tsx"),
            read("frontend/src/components/workspace/line-glyph.tsx"),
            read("frontend/src/components/workspace/najia-table.tsx"),
            read("frontend/src/components/workspace/results-panel.tsx"),
            read("frontend/src/components/profile/profile-page.tsx"),
            read("frontend/src/components/profile/profile-menu.tsx"),
        ]
    )

    assert "--primary: 258 68% 48%" in globals_css
    assert "--primary: 255 90% 76%" in globals_css
    assert "#0b0714" in globals_css
    assert "#151021" in globals_css
    assert "oracle-mark" in globals_css
    assert "🔮" in cast_form
    assert "error && !data" in workspace
    assert "imperial-highlight-panel" in themed_surfaces
    assert "imperial-highlight-card" in themed_surfaces
    assert "imperial-chip" in themed_surfaces

    stale_theme_tokens = [
        "amber-",
        "orange-",
        "yellow-",
        "emerald-",
        "text-sky",
        "dark:text-white",
        "dark:bg-white",
        "dark:border-white",
        "#101419",
        "#15191b",
        "#101417",
        "#f8fafc",
        "#eef2f6",
        "#f5f3ee",
        "18 76% 44%",
        "25 82% 62%",
    ]
    for token in stale_theme_tokens:
        assert token not in themed_surfaces


def test_method_page_and_nav_explain_trust_boundary():
    method_page = read("frontend/src/app/[locale]/method/page.tsx")
    layout = read("frontend/src/app/[locale]/layout.tsx")
    en = read("frontend/src/i18n/catalog/en.ts")
    zh = read("frontend/src/i18n/catalog/zh.ts")

    assert "/method" in layout
    assert "md:hidden" in layout
    assert 'method: "Method"' in en
    assert 'method: "机理"' in zh
    assert "AI synthesis is allowed" in method_page
    assert "365-day cloud retention limit" in method_page
    assert "not medical, legal, financial" in method_page


def test_library_has_pinyin_search_and_public_metadata():
    library_data = read("frontend/src/lib/hexagram-library.ts")
    library_page = read("frontend/src/app/[locale]/library/page.tsx")
    search = read("frontend/src/components/library/library-search.tsx")
    detail_page = read("frontend/src/app/[locale]/hexagram/[slug]/page.tsx")

    assert "HEXAGRAM_PINYIN_BY_SLUG" in library_data
    assert 'qian: "Qián"' in library_data
    assert "LibrarySearch" in library_page
    assert library_page.index("<LibrarySearch") < library_page.index("HEXAGRAM_LIBRARY.map")
    assert "sourceSnippet" in library_page
    assert "Received text" in library_page
    assert "Judgment · Takashima" not in library_page
    assert "Search the Yi" in search
    assert "getHexagramPinyin" in detail_page
    assert "alternates" in detail_page


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


def test_source_drawer_has_classification_and_why_selected():
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert "sourceLayerLabel" in results
    assert "whySelectedForSource" in results
    assert "Why selected" in results
    assert "Source class" in results
    assert "为什么选它" in results


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
    assert "imperial-highlight-panel" in results
    assert "卦辞解析" in results
    assert "Decisive passage analysis" in results
    assert "imperial-highlight-card" in results


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


def test_profile_page_matches_premium_study_surface():
    profile = read("frontend/src/components/profile/profile-page.tsx")

    assert "AccountSummaryPanel" in profile
    assert "CloudHistoryPanel" in profile
    assert "AuthPanel" in profile
    assert "SessionRecordCard" in profile
    assert "rounded-3xl" not in profile
    assert 'from "@/components/ui/card"' not in profile
    assert "<Card" not in profile
    assert "Textarea" not in profile
    assert "max-w-7xl" in profile
    assert "grid gap-6 lg:grid-cols-[18rem_1fr]" in profile
    assert "Reading archive" in profile
    assert "阅读档案" in profile
    assert "border border-border/60 bg-surface" in profile
    assert "bg-surface-elevated" in profile
    assert "LogOut" in profile
    assert "Trash2" in profile
    assert "Download" in profile
    assert "365-day" in profile
    assert "365 天" in profile
    assert "up to 500" in profile
    assert "最多 500" in profile


def test_najia_table_uses_compact_rows_without_losing_line_preview():
    najia = read("frontend/src/components/workspace/najia-table.tsx")

    assert 'CardContent className="p-2 sm:p-3"' in najia
    assert "md:grid-cols-[7rem_minmax(0,1fr)_2.5rem_minmax(0,1fr)]" in najia
    assert "×→" in najia
    assert "row.changed_mark" in najia
    assert "min-h-11" in najia
    assert 'className="h-2.5 w-14"' in najia
    assert "imperial-text" in najia


def test_reading_desk_has_question_coaching_and_guided_line_builder():
    cast_form = read("frontend/src/components/workspace/cast-form.tsx")
    analytics = read("frontend/src/lib/analytics.ts")
    store = read("frontend/src/lib/store.ts")

    assert "analyzeQuestion" in cast_form
    assert "High-risk question" in cast_form
    assert "Better as an inquiry question" in cast_form
    assert "coinLineValue" in cast_form
    assert "Toss one coin line" in cast_form
    assert "Line builder" in cast_form
    assert "CastHexagramPreview" in cast_form
    assert "Live hexagram" in cast_form
    assert "AI reading settings" in cast_form
    assert "Time and raw input" in cast_form
    assert "AI controls stay on the main page" in cast_form
    assert "max-w-[88rem]" in cast_form
    assert "Classical research" not in cast_form
    assert "经典研究" not in cast_form
    assert "aria-pressed={mode.active}" in cast_form
    assert "SAFE_EVENT_NAMES" in analytics
    assert "user_question" not in analytics
    assert 'accessPassword: ""' in store


def test_supabase_retention_contract_keeps_sessions_for_one_year():
    schema = read("docs/supabase-schema.sql")

    assert "365 days" in schema
    assert "90 days" not in schema


def test_cloud_session_limit_defaults_to_500_saved_readings():
    chat_service = read("src/iching/web/chat_service.py")
    readme = read("README.md")
    deployment = read("docs/deployment.md")

    assert 'ICHING_USER_SESSION_LIMIT", "500"' in chat_service
    assert "`ICHING_USER_SESSION_LIMIT` (default `500`)" in readme
    assert "`ICHING_USER_SESSION_LIMIT` (saved sessions per user, default 500)" in deployment
