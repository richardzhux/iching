import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_homepage_leads_with_decision_outcomes_and_four_intent_paths():
    source = read("frontend/src/components/home/home-page.tsx")
    english = read("frontend/src/i18n/catalog/en.ts")
    chinese = read("frontend/src/i18n/catalog/zh.ts")
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

    assert "messages.home" in source
    assert "方向、时机、下一步" in chinese
    assert "direction, timing, and next action" in english
    for topic in ("事业", "感情", "选择", "近况"):
        assert topic in chinese
    assert source.count("intent.href") == 1
    assert "?topic=" in english
    assert "sampleReading" in source
    assert "Hexagram 3" in english
    assert "Hexagram 8" in english
    assert "/library" in source
    assert "pillars" not in source
    assert "min-h-[calc" not in source
    assert "not medical, legal, financial" in english


def test_primary_navigation_is_task_oriented_active_and_profile_is_not_duplicated():
    layout = read("frontend/src/app/[locale]/layout.tsx")
    navigation_path = ROOT / "frontend/src/components/navigation/primary-navigation.tsx"
    assert navigation_path.exists(), "primary navigation should be a pathname-aware client component"
    navigation = navigation_path.read_text(encoding="utf-8")
    english = read("frontend/src/i18n/catalog/en.ts")
    chinese = read("frontend/src/i18n/catalog/zh.ts")

    assert 'workspace: "Cast"' in english
    assert 'library: "Study"' in english
    assert 'method: "Charts"' in english
    assert 'profile: "My"' in english
    assert 'workspace: "起卦"' in chinese
    assert 'library: "查卦"' in chinese
    assert 'method: "排盘"' in chinese
    assert 'profile: "我的"' in chinese
    assert "PrimaryNavigation" in layout
    assert "github.com" not in layout
    assert "messages.nav.profile" not in layout
    assert "usePathname" in navigation
    assert 'aria-current={active ? "page" : undefined}' in navigation
    assert "focus-visible:" in navigation
    assert "overflow-x-auto" in navigation


def test_i18n_provider_sets_the_document_language_after_hydration():
    provider = read("frontend/src/components/providers/i18n-provider.tsx")

    assert "document.documentElement.lang" in provider
    assert 'locale === "zh" ? "zh-CN" : "en"' in provider


def test_task4_review_intents_map_to_backend_topics_and_hydrate_cast_form_safely():
    intent_path = ROOT / "frontend/src/lib/reading-intents.ts"
    assert intent_path.exists(), "home intents need one stable mapping shared with CastForm"
    intents = intent_path.read_text(encoding="utf-8")
    cast_form = read("frontend/src/components/workspace/cast-form.tsx")
    e2e = read("frontend/e2e/public-routes.spec.ts")

    for intent_id, topic_label in (
        ("career", "事业"),
        ("relationship", "感情"),
        ("choice", "其他/跳过"),
        ("current", "整体运势"),
    ):
        assert intent_id in intents
        assert topic_label in intents
    assert "questionHint" in intents
    assert 'searchParams.get("topic")' in cast_form
    assert 'searchParams.get("question")' in cast_form
    assert "resolveReadingIntent" in cast_form
    assert "current.userQuestion" in cast_form
    assert "explicitQuestion" in cast_form
    assert "home intent hydrates a real topic and localized question hint" in e2e
    assert "explicit intent overrides stale topic without replacing a draft question" in e2e


def test_task4_review_navigation_search_and_home_hierarchy_are_unambiguous():
    navigation = read("frontend/src/components/navigation/primary-navigation.tsx")
    search = read("frontend/src/components/library/library-search.tsx")
    home = read("frontend/src/components/home/home-page.tsx")

    assert 'matches: ["/library", "/hexagram"]' in navigation
    assert "matchedResults" in search
    assert "displayedResults" in search
    assert "showing" in search
    assert "takashima" not in search.lower()
    assert "copy.viewFull" not in home


def test_task4_rereview_english_search_examples_and_live_count_are_truthful():
    search = read("frontend/src/components/library/library-search.tsx")

    assert 'placeholder: "qian, hexagram 3, difficulty, judgment..."' in search
    assert 'matched === 1 ? "result" : "results"' in search
    assert 'placeholder: "qian, 屯, difficulty, 利贞, timing..."' not in search


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
    assert "🔮" not in workspace
    assert "🔮" not in cast_form
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


def test_tools_page_replaces_method_page_and_stays_in_navigation():
    method_page = read("frontend/src/app/[locale]/method/page.tsx")
    tools_page = read("frontend/src/app/[locale]/tools/page.tsx")
    tools_ui = read("frontend/src/components/tools/metaphysics-tools.tsx")
    layout = read("frontend/src/app/[locale]/layout.tsx")
    navigation = read("frontend/src/components/navigation/primary-navigation.tsx")
    en = read("frontend/src/i18n/catalog/en.ts")
    zh = read("frontend/src/i18n/catalog/zh.ts")

    assert 'redirect(withLocale(locale, "/tools"))' in method_page
    assert "MetaphysicsTools" in tools_page
    assert "build_metaphysics" not in tools_ui
    assert 'import("iztro")' in tools_ui
    assert "PrimaryNavigation" in layout
    assert "/tools" in navigation
    assert "/method" not in navigation
    assert "md:hidden" in layout
    assert 'method: "Charts"' in en
    assert 'method: "排盘"' in zh


def test_p1_bazi_controls_separate_basic_and_professional_accessibly():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    controls = read("frontend/src/components/tools/metaphysics-controls.tsx")

    assert 'value="current"' in tools
    assert 'value="bazi"' in tools
    assert 'value="ziwei"' in tools
    assert "专业排盘设置" in tools
    assert "Professional chart settings" in tools
    assert "<details" in controls
    assert "<details open" not in controls
    for field_id in (
        "bazi-calendar",
        "bazi-birth-time",
        "bazi-lunar-date",
        "bazi-lunar-time",
        "bazi-gender",
        "bazi-timezone",
        "bazi-true-solar",
        "bazi-longitude",
        "bazi-day-boundary",
        "bazi-leap-month",
        "bazi-dayun-algorithm",
    ):
        assert field_id in controls
    assert 'aria-labelledby="bazi-calendar-label"' in controls
    assert 'aria-labelledby="bazi-gender-label"' in controls
    assert 'aria-labelledby="bazi-timezone-label"' in controls
    assert "BirthPlaceField" in controls
    assert 'id="bazi-hour-uncertain"' in controls
    assert 'checked={hourUncertain}' in controls
    assert 'onCheckedChange={setHourUncertain}' in controls
    assert "先看不受时辰影响的部分" in controls
    assert "Show the parts that stay stable across possible hours" in controls
    assert 'required' in controls
    assert 'htmlFor="bazi-true-solar"' in controls
    assert "trueSolar ?" in controls
    assert 'calendar === "lunar"' in controls
    assert "男 / Male" not in controls
    assert "分钟精算（sect2）" not in tools
    assert "传统折算法（sect1）" not in tools
    assert "Minute-based calculation (sect2)" not in tools
    assert "Traditional conversion (sect1)" not in tools
    assert "选择城市后自动填写时区和经度" in tools
    assert "Selecting a city fills its time zone and longitude" in tools
    assert 'role="status"' in tools
    assert "正在读取当前时令" in tools
    assert "Loading current calendar" in tools


def test_p1_bazi_results_lead_with_factual_digest_and_split_solar_term_modes():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")

    assert '<BaziChartView chart={currentChart} locale={locale} mode="current"' in tools
    assert 'chart={displayBirthChart ?? birthResult.chart}' in tools
    assert 'generatedAt={birthResult.generatedAt}' in tools
    assert 'subjectName={birthResult.subjectName}' in tools
    assert "function UncertainBaziView" in chart
    assert "先看不受时辰影响的部分" in chart
    assert "Start with what stays stable" in chart
    assert "日主" in chart
    assert "Day master" in chart
    assert "四柱" in chart
    assert "Four pillars" in chart
    assert "排盘规则" in chart
    assert "Calculation rule" in chart
    assert "当前大运" in chart
    assert "Current Da Yun" in chart
    assert "当前标记按精确交接时刻定位" in chart
    assert "Current markers use exact handoff instants" in chart
    assert "cycle.is_current" in chart
    assert "start_year <= currentYear" in chart
    assert "currentYear <= cycle.end_year" in chart
    assert "按精确起运与交接时刻定位" in chart
    assert "Located from the exact start and handoff instant" in chart
    assert "element_season_status" in chart
    assert "哪些结构更有辨识度" in chart
    assert "Which structures are more distinctive" in chart
    assert "BaziProfessionalTable" in chart
    assert "LiveSolarTermCountdown" in chart
    assert "HistoricalSolarTerm" in chart
    historical = chart[chart.index("function HistoricalSolarTerm") :]
    assert "term.seconds_away" in historical
    assert "term.timestamp" in historical
    assert "Date.now()" not in historical
    assert "0 天 0 时 0 分 0 秒" not in chart
    assert "0d 0h 0m 0s" not in chart


def test_p1_bazi_uses_chart_timezone_and_non_overlapping_current_refresh():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")

    assert "formatChartTimestamp(facts.gregorian, locale, chart.timezone)" in chart
    assert "formatChartTimestamp(calculationTimestamp, locale, timeZone)" in chart
    assert "formatChartTimestamp(term.timestamp, locale, timeZone)" in chart
    assert "timeZone={chart.timezone}" in chart
    assert "timeZone," in chart
    assert "currentYearInTimeZone(chart.timezone)" in chart
    assert "getFullYear()" not in chart

    assert "window.setInterval(load, 60_000)" not in tools
    assert "timer = window.setTimeout(() => { void load() }, 60_000)" in tools
    assert "window.clearTimeout(timer)" in tools


def test_task6_location_lookup_is_pinned_local_guarded_and_capped():
    package = json.loads(read("frontend/package.json"))
    route_path = ROOT / "frontend/src/app/api/locations/route.ts"
    search_path = ROOT / "frontend/src/lib/location-search.ts"

    assert package["dependencies"].get("city-timezones") == "1.3.4"
    assert route_path.exists(), "location search needs a local App Router endpoint"
    assert search_path.exists(), "location search needs a server-only lookup module"

    route = route_path.read_text()
    search = search_path.read_text()
    combined = f"{route}\n{search}"
    assert 'export const runtime = "nodejs"' in route
    assert "query.trim().length < 2" in route
    assert 'localeParam === "zh" ? "zh" : "en"' in route
    assert "searchLocations(query, locale).slice(0, 8)" in route
    assert "try {" in route and "catch" in route
    assert "Unable to search locations" in route
    assert "city-timezones" in search
    for remote_geocoder in ("open-meteo", "nominatim", "googleapis", "mapbox", "fetch("):
        assert remote_geocoder not in combined.lower()


def test_task6_location_search_has_explicit_chinese_aliases_and_safe_results():
    search_path = ROOT / "frontend/src/lib/location-search.ts"
    assert search_path.exists(), "Chinese aliases and city dataset search should share one module"
    search = search_path.read_text()

    assert "export type LocationResult" in search
    assert "CHINESE_CITY_ALIASES" in search
    for city in ("北京", "上海", "广州", "深圳", "成都", "西安", "乌鲁木齐", "香港", "澳门", "台北"):
        assert city in search
    for field in ("id", "name", "region", "country", "latitude", "longitude", "timezone"):
        assert f"{field}:" in search
    assert "cityMapping" in search
    assert "dedupe" in search.lower()
    assert ".slice(0, 8)" in search


def test_task6_birth_place_combobox_requires_selection_and_applies_exact_location():
    field_path = ROOT / "frontend/src/components/tools/birth-place-field.tsx"
    assert field_path.exists(), "BaZi needs an accessible birthplace resolver"

    field = field_path.read_text()
    controls = read("frontend/src/components/tools/metaphysics-controls.tsx")
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")

    assert 'role="combobox"' in field
    assert 'role="listbox"' in field
    assert 'role="option"' in field
    assert 'aria-autocomplete="list"' in field
    assert "aria-activedescendant" in field
    assert "onSelect(result)" in field
    assert "selectResult" in field
    assert "selectedLocation" in field
    assert "clear" in field.lower()
    assert "replace" in field.lower()
    assert 'role="status"' in field
    assert 'role="alert"' in field
    assert "BirthPlaceField" in controls
    assert "onBirthPlaceSelect" in controls
    assert "handleBirthPlaceSelect" in tools
    selection_handler = tools[
        tools.index("function handleBirthPlaceSelect") : tools.index("\n  }", tools.index("function handleBirthPlaceSelect"))
    ]
    assert "setBirthPlace(" in selection_handler
    assert "setTimezone(location.timezone)" in selection_handler
    assert "setLongitude(String(location.longitude))" in selection_handler
    assert 'id="bazi-timezone"' in controls
    assert 'id="bazi-longitude"' in controls


def test_task6_curated_aliases_are_explicit_and_use_official_civil_timezones():
    search = read("frontend/src/lib/location-search.ts")

    assert "CURATED_LOCATIONS" in search
    assert "lookupViaCity" not in search
    assert 'name: "石家庄"' in search
    assert "latitude: 38.05001467" in search
    assert 'name: "沈阳"' in search
    assert "latitude: 41.80497927" in search
    assert 'name: "苏州"' in search
    assert 'region: "江苏省"' in search
    assert search.count('timezone: "Asia/Shanghai"') >= 37
    assert 'timezone: "Asia/Hong_Kong"' in search
    assert 'timezone: "Asia/Macau"' in search
    assert 'timezone: "Asia/Taipei"' in search


def test_task6_search_is_indexed_bounded_and_supports_local_nearest_matching():
    route = read("frontend/src/app/api/locations/route.ts")
    search = read("frontend/src/lib/location-search.ts")

    assert "MAX_QUERY_LENGTH" in search
    assert "NORMALIZED_LOCATION_INDEX" in search
    assert "normalizeLocationQuery" in search
    assert "MAX_NEAREST_DISTANCE_KM" in search
    assert "haversineDistanceKm" in search
    assert "findNearestLocation" in search
    assert "Number.isFinite(latitude)" in search
    assert "latitude >= -90" in search
    assert "latitude <= 90" in search
    assert "longitude >= -180" in search
    assert "longitude <= 180" in search
    assert "distanceKm > MAX_NEAREST_DISTANCE_KM" in search
    assert "export async function POST" in route
    assert "await request.json()" in route
    assert "isValidCoordinates" in route
    assert "findNearestLocation" in route
    assert "distanceKm" in route
    assert "{ result: null }" in route


def test_task6_combobox_prevents_stale_results_and_uses_one_input_focus_model():
    field = read("frontend/src/components/tools/birth-place-field.tsx")

    assert "requestSequenceRef" in field
    assert "controller.abort()" in field
    assert "requestId === requestSequenceRef.current" in field
    assert "handleQueryChange" in field
    query_handler = field[field.index("function handleQueryChange") : field.index("\n  }", field.index("function handleQueryChange"))]
    assert "setResults([])" in query_handler
    assert "setActiveIndex(-1)" in query_handler
    assert 'tabIndex={-1}' in field
    assert "scrollIntoView({ block: \"nearest\" })" in field
    assert "aria-expanded={listboxOpen}" in field
    assert "aria-controls={listboxOpen ? listboxId : undefined}" in field
    listbox = field[field.index('role="listbox"') : field.index("</ul>", field.index('role="listbox"'))]
    assert 'role="status"' not in listbox
    assert 'role="alert"' not in listbox


def test_task6_current_location_is_gesture_triggered_local_and_confirmed_before_apply():
    field = read("frontend/src/components/tools/birth-place-field.tsx")
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")

    assert "Intl.DateTimeFormat().resolvedOptions().timeZone" in tools
    assert "useCurrentLocation" in field
    assert "navigator.geolocation.getCurrentPosition" in field
    assert 'onClick={useCurrentLocation}' in field
    assert 'method: "POST"' in field
    assert "latitude: position.coords.latitude" in field
    assert "longitude: position.coords.longitude" in field
    assert "currentLocationCandidate" in field
    assert "distanceKm" in field
    assert "confirmCurrentLocation" in field
    assert "cancelCurrentLocation" in field
    assert "onSelect(currentLocationCandidate.result)" in field
    assert "当前位置可能不是出生地" in field
    assert "Your current location may not be your birth place" in field
    assert "使用当前位置" in field
    assert "Use current location" in field
    assert "timeout: 8_000" in field
    assert "localStorage" not in field


def test_task6_current_location_invalidates_stale_permission_and_nearest_city_requests():
    field = read("frontend/src/components/tools/birth-place-field.tsx")

    assert "geolocationSequenceRef" in field
    assert "geolocationControllerRef" in field
    assert "invalidateGeolocation" in field
    assert "geolocationControllerRef.current?.abort()" in field
    assert "signal: controller.signal" in field
    assert "requestId !== geolocationSequenceRef.current" in field
    assert "!query.trim() ? currentLocationCandidate : null" in field
    query_handler = field[field.index("function handleQueryChange") : field.index("\n  }", field.index("function handleQueryChange"))]
    assert "invalidateGeolocation()" in query_handler


def test_frontend_ci_supplies_inert_public_config_for_mocked_browser_flows():
    workflow = read(".github/workflows/frontend-ci.yml")

    assert "NEXT_PUBLIC_API_BASE_URL: http://127.0.0.1:8001" in workflow
    assert "NEXT_PUBLIC_SUPABASE_URL: https://ci-test.supabase.co" in workflow
    assert "NEXT_PUBLIC_SUPABASE_ANON_KEY: ci-test-anon-key" in workflow
    assert "NEXT_PUBLIC_API_BASE_URL: ${{ secrets." not in workflow
    assert "NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets." not in workflow


def test_task6_manual_overrides_are_visible_and_preserved_when_city_is_cleared():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    field = read("frontend/src/components/tools/birth-place-field.tsx")

    assert "type LocationAutofillState" in tools
    assert "previousTimezone" in tools
    assert "previousLongitude" in tools
    assert "appliedTimezone" in tools
    assert "appliedLongitude" in tools
    assert "locationOverrideActive" in tools
    assert "timezone === locationAutofill.appliedTimezone" in tools
    assert "longitude === locationAutofill.appliedLongitude" in tools
    assert "setTimezone(locationAutofill.previousTimezone)" in tools
    assert "setLongitude(locationAutofill.previousLongitude)" in tools
    assert "overrideActive" in field
    assert "effectiveTimezone" in field
    assert "effectiveLongitude" in field
    assert "专业设置覆盖已生效" in field
    assert "Professional override active" in field


def test_task7_export_dependency_and_utility_are_lazy_safe_and_bounded():
    package = json.loads(read("frontend/package.json"))
    export_path = ROOT / "frontend/src/lib/chart-export.ts"

    assert package["dependencies"].get("html-to-image") == "1.11.13"
    assert export_path.exists(), "chart export needs one shared safe utility"
    export = export_path.read_text()
    assert 'await import("html-to-image")' in export
    assert 'from "html-to-image"' not in export
    assert "sanitizeExportFilename" in export
    assert "MAX_EXPORT_DIMENSION" in export
    assert "MAX_EXPORT_PIXEL_AREA" in export
    assert "MAX_PIXEL_RATIO" in export
    assert "Math.min(" in export
    assert "Math.sqrt(MAX_EXPORT_PIXEL_AREA / logicalPixelArea)" in export
    assert "pixelRatio" in export
    assert 'data-export-exclude' in export
    assert "link.click()" in export
    assert export.count("link.click()") == 1


def test_task7_export_button_restores_idle_and_surfaces_localized_failure():
    button_path = ROOT / "frontend/src/components/tools/chart-export-button.tsx"
    assert button_path.exists(), "results need one reusable export action"
    button = button_path.read_text()

    assert "export function ChartExportButton" in button
    assert "targetId" in button
    assert "safeBaseFilename" in button
    assert "exportChartPng" in button
    assert "toast.error(errorLabel)" in button
    assert "finally" in button
    assert "setExporting(false)" in button
    assert "data-export-exclude" in button
    assert 'role="status"' in button


def test_task7_bazi_is_summary_first_share_ready_and_keeps_raw_facts_collapsed():
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    css = read("frontend/src/app/globals.css")

    consumer_result = chart[chart.index("function BaziConsumerResult") : chart.index("function ShareExportMenu")]
    share_menu = chart[chart.index("function ShareExportMenu") : chart.index("function ExportMenuRow")]
    assert consumer_result.count("<ShareExportMenu") == 1
    assert share_menu.count("<ChartExportButton") == 1
    assert share_menu.count("<ChartAssetExportButton") == 4
    assert "分享与导出" in share_menu
    assert "Share & export" in share_menu
    assert "useId" in chart
    assert 'id={exportTargetId}' in chart
    assert 'aria-hidden="true"' in chart
    assert "data-chart-export-root" in chart
    assert "chart-export-canvas" in chart
    assert consumer_result.index("<ShareExportMenu") < consumer_result.index("<BaziExportCanvas")
    assert 'generatedAt: new Date().toISOString()' in tools
    assert 'generatedAt={birthResult.generatedAt}' in tools
    assert "chart.calculation_timestamp, locale" not in chart[chart.index("function BaziExportCanvas") :]
    assert "chart.birth_profile.birth_place" in chart
    assert "chart.birth_profile.input_date" in chart
    assert "chart.day_master" in chart
    assert "calculationRule" in chart
    assert "currentCycle" in chart
    assert "按出生地时间与精确节气排盘" in chart
    assert "Calculated from local birth time and exact solar terms" in chart
    assert "data-element={row.elements?.[index]}" in chart
    assert "grid-cols-[3.75rem_repeat(4" in chart
    assert "buildBaziMarkdown" in chart
    assert "BaziPeriodNavigator" in chart
    assert "overflow-x-auto" in chart
    assert 'aria-pressed={selected}' in chart
    assert "current ?" in chart
    assert "Which structures are more distinctive" in chart
    professional = chart[chart.index("function BaziProfessionalTable") :]
    for raw_fact in ("hidden_stems", "ten_god", "nayin", "xunkong", "di_shi", "self_seat"):
        assert raw_fact in professional
    assert ".chart-share-canvas" in css
    assert ".chart-export-canvas" in css
    assert "position: fixed" in css
    assert "width: 1080px" in css
    assert '[data-element="木"]' in css


def test_task7_ziwei_has_one_share_canvas_and_preserves_palace_interaction():
    chart = read("frontend/src/components/tools/ziwei-chart-view.tsx")

    fallback_result = chart[: chart.index("type ZiweiConsumerTab")]
    consumer_result = chart[chart.index("function ZiweiConsumerResult") : chart.index("function ZiweiArchiveBanner")]
    assert fallback_result.count("<ChartExportButton") == 1
    assert consumer_result.count("<ChartExportButton") == 1
    assert "if (consumer)" in chart
    assert "useId" in chart
    assert 'id={exportTargetId}' in chart
    assert 'aria-hidden="true"' in chart
    assert "data-chart-export-root" in chart
    assert chart.index("<ChartExportButton") < chart.index('id={exportTargetId}')
    assert "generatedAt" in chart
    assert "chart.fiveElementsClass" in chart
    assert "chart.soul" in chart and "chart.body" in chart
    assert "horoscopeDate" in chart
    assert "horoscope.decadal" in chart
    assert "horoscope.yearly" in chart
    assert "horoscope.yearly.mutagen" in chart
    assert "chart.chineseDate" in chart
    assert "chart.lunarDate" in chart
    assert "chart.time" in chart
    assert "chart.gender" in chart
    assert "ZiweiPalaceChart" in chart
    export_canvas = chart[chart.index("function ZiweiExportCanvas") : chart.index("function ZiweiIdentitySummary")]
    assert "<ZiweiPalaceChart" in export_canvas
    palace_chart = chart[chart.index("function ZiweiPalaceChart") : chart.index("function PalaceButton")]
    assert "palace.name" in palace_chart
    assert "palace.heavenlyStem" in palace_chart
    assert "palace.earthlyBranch" in palace_chart
    assert "palace.majorStars" in palace_chart
    assert "star.mutagen" in palace_chart
    assert "按统一通行法排盘" in chart
    assert "Calculated with one standard method" in chart
    assert "频率样本暂时不可用；命盘事实不受影响" in chart
    assert "Frequency samples are temporarily unavailable; chart facts are unaffected" in chart
    assert 'type="button"' in chart
    assert "aria-pressed={isSelected}" in chart
    assert "horoscope?.decadal.index === palace.index" in chart
    assert "horoscope?.yearly.index === palace.index" in chart
    assert "overflow-x-auto" in chart
    assert "Professional chart data and provenance" in chart


def test_task7_visible_summary_is_not_immediately_duplicated_and_details_are_flat():
    bazi = read("frontend/src/components/tools/bazi-chart-view.tsx")
    ziwei = read("frontend/src/components/tools/ziwei-chart-view.tsx")

    bazi_consumer = bazi[bazi.index("function BaziConsumerResult") : bazi.index("function ShareExportMenu")]
    bazi_share_stage = bazi[bazi.index("function BaziConsumerShareCanvases") : bazi.index("function BaziPatternSummary")]
    bazi_full_export = bazi[bazi.index("function BaziExportCanvas") :]
    assert bazi_consumer.count("<BaziProfessionalTable chart={chart} locale={locale} />") == 1
    assert bazi_share_stage.count("<BaziProfessionalTable chart={chart} locale={locale} />") == 1
    assert bazi_full_export.count("<BaziProfessionalTable chart={chart} locale={locale} />") == 1
    assert 'aria-hidden="true" inert className="chart-export-stage"' in bazi_share_stage
    assert "ZiweiDigest" not in ziwei
    ziwei_fallback = ziwei[: ziwei.index("type ZiweiConsumerTab")]
    ziwei_consumer = ziwei[ziwei.index("function ZiweiConsumerResult") : ziwei.index("function ZiweiArchiveBanner")]
    ziwei_export = ziwei[ziwei.index("function ZiweiExportCanvas") : ziwei.index("type ChartStar")]
    assert ziwei_fallback.count("<ZiweiIdentitySummary") == 1
    assert ziwei_consumer.count("<ZiweiIdentitySummary") == 1
    assert ziwei_export.count("<ZiweiIdentitySummary") == 1
    assert 'className="chart-share-canvas chart-export-canvas"' in ziwei
    assert "rounded-lg border" not in ziwei[ziwei.index("function SelectedPalaceDetail") :]
    assert "rounded-md border" not in ziwei[ziwei.index("function StarGroup") :]


def test_task7_reduced_motion_is_checked_before_imperative_dayun_scroll():
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    css = read("frontend/src/app/globals.css")

    assert "scrollIntoView" not in chart
    assert 'window.matchMedia("(prefers-reduced-motion: reduce)").matches' in tools
    assert 'behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"' in tools
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "scroll-behavior: auto !important" in css


def test_task7_playwright_covers_single_safe_png_download_and_failure_recovery():
    e2e = read("frontend/e2e/public-routes.spec.ts")

    assert "exports one mocked BaZi PNG with a safe filename" in e2e
    assert 'page.waitForEvent("download")' in e2e
    assert 'toHaveAttribute("aria-hidden", "true")' in e2e
    assert 'locator("button, input, select, textarea")' in e2e
    assert "downloads).toBe(1)" in e2e
    assert "recovers when the export target is unavailable" in e2e


def test_task7_export_target_is_unpositioned_inside_hidden_staging_wrapper():
    bazi = read("frontend/src/components/tools/bazi-chart-view.tsx")
    ziwei = read("frontend/src/components/tools/ziwei-chart-view.tsx")
    css = read("frontend/src/app/globals.css")

    stage_rule = css[css.index(".chart-export-stage") : css.index("}", css.index(".chart-export-stage"))]
    target_rule = css[css.index(".chart-export-canvas") : css.index("}", css.index(".chart-export-canvas"))]
    for positioning in ("position: fixed", "left: -12000px", "z-index: -1"):
        assert positioning in stage_rule
        assert positioning not in target_rule
    for chart in (bazi, ziwei):
        assert chart.count('className="chart-export-stage"') == chart.count('aria-hidden="true" inert className="chart-export-stage"')
        assert chart.index('className="chart-export-stage"') < chart.index("data-chart-export-root")
        assert 'data-chart-export-root className="chart-share-canvas chart-export-canvas"' in chart


def test_task7_playwright_decodes_png_and_checks_dimensions_and_pixels():
    e2e = read("frontend/e2e/public-routes.spec.ts")

    assert 'from "node:fs/promises"' in e2e
    assert "await download.path()" in e2e
    assert 'data:image/png;base64,' in e2e
    assert "image.naturalWidth" in e2e
    assert "image.naturalHeight" in e2e
    assert "getImageData" in e2e
    assert "opaqueSamples" in e2e
    assert "uniqueColors" in e2e


def test_task7_ziwei_result_precedes_one_closed_edit_details_disclosure():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")

    assert "ziweiEditorOpen" in tools
    assert "setZiweiEditorOpen(false)" in tools
    assert 'id="ziwei-edit-details"' in tools
    assert "修改资料" in tools
    assert "Edit details" in tools
    assert tools.index("ziweiResult ? <ZiweiChartView") < tools.index('id="ziwei-edit-details"')
    assert tools.count('id="ziwei-basic-title"') == 1
    assert "generatedAt: new Date().toISOString()" in tools
    assert "generatedAt={ziweiResult.generatedAt}" in tools


def test_p1_ziwei_controls_keep_basic_inputs_visible_and_name_every_control():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")

    assert 'id="ziwei-basic-title"' in tools
    assert "紫微基础信息" in tools
    assert "Zi Wei basic details" in tools
    for field_id in (
        "ziwei-calendar",
        "ziwei-birth-time",
        "ziwei-lunar-date",
        "ziwei-lunar-time",
        "ziwei-gender",
        "ziwei-horoscope-date",
        "ziwei-leap-month",
    ):
        assert field_id in tools
    for removed_field_id in (
        "ziwei-school",
        "ziwei-astro-type",
        "ziwei-year-boundary",
        "ziwei-fix-leap",
        "ziwei-day-boundary",
    ):
        assert removed_field_id not in tools
    assert 'aria-labelledby="ziwei-calendar-label"' in tools
    assert 'aria-labelledby="ziwei-gender-label"' in tools
    assert 'htmlFor="ziwei-birth-time"' in tools
    assert 'htmlFor="ziwei-horoscope-date"' in tools
    assert 'const ZIWEI_STANDARD_CONFIG_ID = "ziwei-standard-v1"' in tools
    assert 'standardRulesBody: "已为你采用通行法排盘"' in tools
    assert 'standardRulesBody: "The standard method is already selected for you"' in tools
    assert "通行法 · 天盘 · 立春年界及运限年界 · 晚子时换日 · 闰月修正开启" not in tools
    assert 'role="status"' in tools
    assert "正在生成紫微星盘" in tools
    assert "Generating Zi Wei chart" in tools


def test_p1_ziwei_chart_is_interactive_readable_and_period_aware():
    chart_path = ROOT / "frontend/src/components/tools/ziwei-chart-view.tsx"
    assert chart_path.exists(), "Zi Wei chart view should be extracted into its own component"

    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    chart = chart_path.read_text()

    assert "ZiweiChartView" in tools
    assert "function ZiweiChart(" not in tools
    assert 'type="button"' in chart
    assert "aria-pressed={isSelected}" in chart
    assert "aria-label={palaceLabel}" in chart
    assert "focus-visible:" in chart
    assert "setSelectedPalaceIndex" in chart
    assert "selectedPalace.majorStars" in chart
    assert "selectedPalace.minorStars" in chart
    assert "selectedPalace.adjectiveStars" in chart
    assert "star.mutagen" in chart
    assert "star.brightness" in chart
    assert "selectedPalace.changsheng12" in chart
    assert "selectedPalace.decadal.range" in chart
    assert "horoscope?.decadal.index === palace.index" in chart
    assert "horoscope?.yearly.index === palace.index" in chart
    assert "大限" in chart
    assert "流年" in chart
    assert "horoscope.yearly.mutagen" in chart
    assert "四化" in chart
    assert "空宫" in chart
    assert "Empty palace" in chart
    assert "overflow-x-auto" in chart
    assert "min-w-[64rem]" in chart
    assert "grid-cols-4" in chart
    assert "<details" in chart
    professional = chart[chart.index("<details") :]
    assert "iztro 2.5.8 · MIT" in professional
    assert "provenance.algorithm" in professional
    assert "解释层不混入排盘事实" in professional
    assert "Interpretation remains separate from chart facts" in professional


def test_p1_ziwei_digest_uses_selected_date_and_localized_provenance_values():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    chart = read("frontend/src/components/tools/ziwei-chart-view.tsx")

    assert "horoscopeDate={ziweiResult.horoscopeDate}" in tools
    assert "horoscope.solarDate" in chart
    assert "horoscope.lunarDate" in chart
    assert "horoscopeDate" in chart
    assert "所选日期大限" in chart
    assert "Selected-date decadal period" in chart
    assert "所选日期流年" in chart
    assert "Selected-date annual period" in chart
    assert "当前大限" not in chart
    assert "Current decadal period" not in chart
    for localized_value in (
        "公历",
        "农历",
        "通行法",
        "中州派",
        "天盘",
        "地盘",
        "人盘",
        "立春",
        "农历正月初一",
        "晚子时换日",
        "晚子时不换日",
        "修正闰月",
        "不修正闰月",
        "闰月",
        "非闰月",
    ):
        assert localized_value in chart


def test_p1_ziwei_validates_target_date_and_commits_one_immutable_snapshot():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    generate = tools[
        tools.index("async function generateZiwei") : tools.index("\n\n  return (", tools.index("async function generateZiwei"))
    ]

    assert "type ZiweiResultSnapshot" in tools
    assert "const [ziweiResult, setZiweiResult]" in tools
    assert "isSupportedHoroscopeDate(horoscopeDate)" in generate
    assert '"1900-01-31"' in tools
    assert '"2100-12-31"' in tools
    assert "请输入 1900-01-31 至 2100-12-31 之间的有效运限日期" in tools
    assert "Enter a valid horoscope date from 1900-01-31 through 2100-12-31" in tools
    assert "instantiateStandardZiwei(normalizedInput, locale)" in generate
    assert generate.index("instantiateStandardZiwei(normalizedInput, locale)") < generate.index("setZiweiResult({")
    assert "setZiwei(" not in generate
    assert "setZiweiHoroscope(" not in generate
    assert generate.index("setZiweiResult({") < generate.index("requestZiweiStatistics(")
    assert "chart," in generate
    assert "horoscope," in generate
    assert "horoscopeDate," in generate
    assert "provenance," in generate
    assert "chart={ziweiResult.chart}" in tools
    assert "horoscope={ziweiResult.horoscope}" in tools
    assert "provenance={ziweiResult.provenance}" in tools


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
    assert "Received text" in detail_page
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
    assert "Explore the 64 hexagrams" in read("frontend/src/app/[locale]/library/page.tsx")
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
    assert 'value === "sources" ? "hex"' in store


def test_p0_result_page_is_one_continuous_trustworthy_reading_flow():
    results = read("frontend/src/components/workspace/results-panel.tsx")
    chinese = read("frontend/src/i18n/catalog/zh.ts")
    english = read("frontend/src/i18n/catalog/en.ts")

    assert "<TabsTrigger" not in results
    assert '<HexResultBlock result={result}' in results
    assert '<ChatPanel session={result} embedded' in results
    assert 'id="ai-followup"' in results
    assert 'reading: "解卦"' in chinese
    assert 'reading: "Read"' in english
    assert "{labels.confidence} {item.confidence}%" not in results
    assert 'noMoving: "无动爻，以本卦卦辞为主断。"' in results
    assert 'noMoving: "No moving lines: the primary hexagram judgment carries the reading."' in results
    assert "格局稳定" not in results
    assert "Stable pattern" not in results
    assert "SourceReaderSheet" in results
    assert "sourcePassages[0]" not in results
    assert "来源待核" in results
    assert "Source unverified" in results
    mechanics = results[
        results.index("function MechanicsInsightPanel") : results.index("function HexResultBlock")
    ]
    assert "labels.keyPassages" not in mechanics


def test_p0_casting_surface_has_three_visible_steps_coin_default_and_no_latency_guesses():
    cast_form = read("frontend/src/components/workspace/cast-form.tsx")
    chinese = read("frontend/src/i18n/catalog/zh.ts")
    english = read("frontend/src/i18n/catalog/en.ts")

    for label in ("1 问什么", "2 怎么起", "3 怎么解", "1 What to ask", "2 How to cast", "3 How to interpret"):
        assert label in cast_form or label in chinese or label in english
    assert 'method.label === "三枚铜钱法"' in cast_form
    assert "appendManualLine(result.value, COIN_METHOD_KEY)" in cast_form
    assert "≈" not in cast_form
    assert "≈" not in chinese
    assert "≈" not in english
    assert 'submitIdle: "起卦"' in chinese
    assert 'submitIdle: "Cast"' in english
    assert "methodUnknownDescription" in cast_form
    assert 'methodUnknownDescription: "其他起卦方法；请按当前方法说明操作。"' in chinese
    assert 'methodUnknownDescription: "Another configured casting method; follow its supplied instructions."' in english


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


def test_guidance_sources_live_in_the_on_demand_notebook_without_a_duplicate_panel():
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert "SourceEvidencePanel" not in results
    assert "SourceReaderSheet" in results
    assert "查看原文笔记" in results
    assert "Review source notebook" in results
    assert "为什么选它" in results
    assert "Why selected" in results
    assert "imperial-highlight-card" in results


def test_mechanics_page_has_professional_cast_logic_not_archive_replica():
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert "function MechanicsInsightPanel" in results
    assert "<MechanicsInsightPanel" in results
    assert "断法结构" in results
    assert "Cast logic" in results
    assert "爻变诊断" in results
    assert "Line movement" in results
    assert "显示补充" in results
    assert "sectionSourceIdForDrawer" in results
    assert results.index("<MechanicsInsightPanel") < results.index("<HexSectionGroup")
    assert results.index("<HexResultBlock") < results.index("<ChatPanel")
    assert "<SourceEvidencePanel" not in results


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


def test_library_page_is_a_consumer_browse_index_without_database_metrics():
    library_page = read("frontend/src/app/[locale]/library/page.tsx")
    search = read("frontend/src/components/library/library-search.tsx")
    copy_path = ROOT / "frontend/src/lib/hexagram-copy.ts"
    assert copy_path.exists(), "localized hexagram copy should be shared by list and detail routes"
    copy_helpers = copy_path.read_text(encoding="utf-8")

    for phrase in ("Source Library", "canonical slots", "source entries", "资料完整度"):
        assert phrase not in library_page
    assert "HEXAGRAM_ARCHIVE_SUMMARY" not in library_page
    assert "getHexagramArchiveSummary" not in library_page
    assert "localizedHexagramMeaning" in library_page
    assert "localizedHexagramThemes" in library_page
    assert "localizedHexagramMeaning" in copy_helpers
    assert "localizedHexagramThemes" in copy_helpers
    assert "themeFilters" not in search
    assert "HEXAGRAM_THEME_FILTERS" not in search
    assert "matchesThemeFilter" not in search
    assert 'role="status"' in search
    assert 'aria-live="polite"' in search
    assert "focus-visible:" in search


def test_hexagram_consumers_use_symmetric_glyphs_and_shared_quick_navigation():
    glyph_path = ROOT / "frontend/src/components/hexagram/hexagram-glyph.tsx"
    nav_path = ROOT / "frontend/src/components/hexagram/hexagram-quick-nav.tsx"
    home = read("frontend/src/components/home/home-page.tsx")
    library = read("frontend/src/app/[locale]/library/page.tsx")
    detail = read("frontend/src/app/[locale]/hexagram/[slug]/page.tsx")

    assert glyph_path.exists()
    assert nav_path.exists()
    glyph = glyph_path.read_text(encoding="utf-8")
    nav = nav_path.read_text(encoding="utf-8")
    assert "flex-1" in glyph
    assert "gap-[18%]" in glyph
    assert "bg-gradient-to-r" not in glyph
    for consumer in (home, library, detail):
        assert "HexagramGlyph" in consumer
        assert "bg-gradient-to-r" not in consumer
    assert "HEXAGRAM_LIBRARY.map" in nav
    assert 'mode: "anchors" | "routes"' in nav
    assert "HexagramQuickNav" in library
    assert 'mode="anchors"' in library
    assert "HexagramQuickNav" in detail
    assert 'mode="routes"' in detail
    assert 'id={`hexagram-${entry.number}`}' in library


def test_library_search_has_no_heuristic_theme_filter_controls():
    search = read("frontend/src/components/library/library-search.tsx")
    copy_helpers = read("frontend/src/lib/hexagram-copy.ts")

    for token in ("activeTheme", "themeFilters", "HEXAGRAM_THEME_FILTERS", "matchesThemeFilter", "aria-pressed"):
        assert token not in search
    assert "HEXAGRAM_THEME_FILTERS" not in copy_helpers
    assert "matchesThemeFilter" not in copy_helpers


def test_cast_form_has_consumer_facing_step_order_and_compact_controls():
    cast_form = read("frontend/src/components/workspace/cast-form.tsx")

    assert 'data-cast-step="question" className="order-1' in cast_form
    assert 'data-cast-step="cast" className="order-2' in cast_form
    assert 'data-cast-step="interpret" className="order-3' in cast_form
    assert 'data-cast-page-title="true"' in cast_form
    assert 'sm:grid-cols-3' in cast_form
    assert 'xl:grid-cols-4' in cast_form
    assert 'data-ai-enable-switch="true"' not in cast_form
    assert 'aria-labelledby="reading-topic-label" className="h-11 w-full' in cast_form


def test_hexagram_detail_prioritizes_meaning_progression_and_collapsed_sources():
    detail_page = read("frontend/src/app/[locale]/hexagram/[slug]/page.tsx")

    assert "getHexagramArchive" in detail_page
    assert "await getHexagramArchive" in detail_page
    assert "ArchiveSlotSection" in detail_page
    assert "SourceEntryCard" in detail_page
    assert "sixLineProgression" in detail_page
    assert "六爻进程" in detail_page
    assert "Six-line progression" in detail_page
    assert "groupArchiveEntriesBySlot" in detail_page
    assert "本卦卦辞" in detail_page
    assert "爻位资料" in detail_page
    assert "用九 / 用六" in detail_page
    assert "whitespace-pre-wrap" in detail_page
    assert "tabIndex={0}" in detail_page
    assert "scroll-mt-[9rem]" in detail_page
    assert "sourcePreview" in detail_page
    assert "<details open=" not in detail_page
    assert "entry.slotKey" not in detail_page
    assert "archive.sourceCounts" in detail_page
    assert "查看全文" in detail_page
    assert "Cast with this context" not in detail_page
    assert "用此卦起一条阅读" not in detail_page


def test_my_page_has_focused_signed_out_auth_and_preserves_signed_in_reading_actions():
    profile = read("frontend/src/components/profile/profile-page.tsx")
    menu = read("frontend/src/components/profile/profile-menu.tsx")
    english = read("frontend/src/i18n/catalog/en.ts")
    chinese = read("frontend/src/i18n/catalog/zh.ts")

    assert "AccountSummaryPanel" in profile
    assert "CloudHistoryPanel" in profile
    assert "AuthPanel" in profile
    assert "SessionRecordCard" in profile
    assert "rounded-3xl" not in profile
    assert 'from "@/components/ui/card"' not in profile
    assert "<Card" not in profile
    assert "Textarea" not in profile
    assert "max-w-7xl" in profile
    assert "auth.user ?" in profile
    assert "auth.user ? (" in profile
    assert 'autoComplete="email"' in profile
    assert 'autoComplete={authMode === "signIn" ? "current-password" : "new-password"}' in profile
    assert 'htmlFor="profile-email"' in profile
    assert 'htmlFor="profile-password"' in profile
    assert profile.index("messages.common.continueWithGoogle") < profile.index("<form")
    assert "messages.profile.authBenefits" in profile
    assert "messages.profile.privacyCopy" in profile
    assert "safeAuthError" in profile
    assert "safeAuthError" in menu
    assert "(error as Error).message" not in profile
    assert "(error as Error).message" not in menu
    assert 'locale === "zh" ? "zh-CN" : "en"' in profile
    assert 'kicker: "My"' in english
    assert 'kicker: "我的"' in chinese
    assert 'cloudHistoryTitle: "Saved readings"' in english
    assert 'cloudHistoryTitle: "已保存卦例"' in chinese
    assert "border border-border/60 bg-surface" in profile
    assert "bg-surface-elevated" in profile
    assert "LogOut" in profile
    assert "Trash2" in profile
    assert "Download" in profile
    assert "365-day" in profile
    assert "365 天" in profile
    assert "up to 500" in profile
    assert "最多 500" in profile


def test_task8_primary_paths_use_consumer_copy_without_duplicate_or_internal_chrome():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    bazi = read("frontend/src/components/tools/bazi-chart-view.tsx")
    ziwei = read("frontend/src/components/tools/ziwei-chart-view.tsx")
    search = read("frontend/src/components/library/library-search.tsx")
    profile = read("frontend/src/components/profile/profile-page.tsx")
    results = read("frontend/src/components/workspace/results-panel.tsx")

    assert 'title: "命盘与人生走势"' in tools
    assert 'title: "Charts & Life Timeline"' in tools
    assert 'calculate: "生成我的命盘"' in tools
    assert 'calculate: "Generate my chart"' in tools
    assert "出生地文本不会自动生成此数值" not in tools
    assert "the birth-place text does not generate this value" not in tools
    assert 'className="rounded-lg border border-border/60 bg-surface p-4 text-xs' not in tools

    assert bazi.count('locale === "zh" ? "八字命盘" : "BaZi chart"') == 0
    assert ziwei.count('locale === "zh" ? "紫微斗数命盘" : "Zi Wei Dou Shu chart"') == 0
    assert 'className="flex justify-end"' in bazi
    assert 'className="flex justify-end"' in ziwei

    assert "检索经典档案" not in search
    assert "Search the archive" not in search
    for phrase in ("私人卦例档案", "已登录档案", "游客档案", "卦例档案", "Reading archive", "Private divination archive"):
        assert phrase not in profile

    assert 'sameSlot: "同一爻位依据"' in results
    assert 'sameSlot: "Same-line evidence"' in results
    assert 'slot: "槽位"' not in results
    assert 'slot: "Slot"' not in results
    assert 'sourceDepth: "来源覆盖"' not in results
    assert 'sourceDepth: "Source coverage"' not in results


def test_task9_frontend_reads_schema6_and_only_new_rule_versioned_charts_write_schema7():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")
    types = read("frontend/src/types/api.ts")
    markdown = read("frontend/src/lib/chart-markdown.ts")

    assert "const snapshotSchemaVersion = Math.max(record.schema_version ?? 0, chart.derived_schema_version ?? 0)" in tools
    assert "if (snapshotSchemaVersion < 6)" in tools
    assert "const snapshotSchemaVersion = chart.rule_versions ? 7 : 6" in tools
    assert "derived_schema_version: snapshotSchemaVersion" in tools
    assert "rule_versions: chart.rule_versions" in tools
    assert "schema_version: snapshotSchemaVersion" in tools
    assert "Present on schema 7 live charts; absent from readable schema 6 archives." in types
    assert "rule_versions?: RuleVersions" in types
    assert "if (!versions)" in markdown
    assert "chart.rules_version" in markdown


def test_task9_incomplete_schema6_archive_is_not_rendered_or_silently_recalculated():
    tools = read("frontend/src/components/tools/metaphysics-tools.tsx")

    assert "function hasCompleteBaziArchiveChart" in tools
    assert "if (!hasCompleteBaziArchiveChart(chart))" in tools
    assert 'kind: "corrupt"' in tools
    assert "为避免显示残缺或错误内容，旧快照未被打开。请核对下方出生资料并重新排盘。" in tools


def test_task8_review_uses_bilingual_saved_reading_copy_once_and_no_internal_fallbacks():
    profile = read("frontend/src/components/profile/profile-page.tsx")
    english = read("frontend/src/i18n/catalog/en.ts")
    chinese = read("frontend/src/i18n/catalog/zh.ts")
    results = read("frontend/src/components/workspace/results-panel.tsx")
    search = read("frontend/src/components/library/library-search.tsx")
    e2e = read("frontend/e2e/public-routes.spec.ts")

    assert 'cloudHistoryTitle: "Saved readings"' in english
    assert 'cloudHistoryTitle: "已保存卦例"' in chinese
    assert 'authCardSignUp: "Create your account"' in english
    assert 'authCardSignUp: "创建账户"' in chinese
    assert "reading archive" not in english.lower()
    assert "卦例档案" not in chinese
    assert "经典档案" not in chinese
    assert "Cloud Session History" not in english
    assert "云端历史记录" not in chinese
    assert profile.count("{copy.readingArchiveBody}") == 1
    assert "isSignedIn" not in profile
    assert "copy.signedOut" not in profile
    for obsolete in ("identity:", "signedOut:", "authRequired:", "accountAccess:", "emailAccount:", "googleAccount:", "useEmail:"):
        assert obsolete not in profile

    assert "slot or source group" not in results
    assert "槽位或来源组" not in results
    assert 'empty: "No matching hexagram. Try a name, pinyin, number, or source phrase."' in search
    assert "source snippet" not in search.lower()

    assert "signed-in My shows saved readings and safe record controls" in e2e
    assert 'route("**/auth/v1/token**"' in e2e
    assert 'name: "Saved readings"' in e2e
    for control in ("Download", "Open session", "Delete"):
        assert f'name: "{control}"' in e2e


def test_task8_bazi_consumer_os_exposes_one_clear_identity_and_share_contract():
    identity = read("frontend/src/components/tools/consumer-identity.tsx")
    achievements = read("frontend/src/components/tools/metaphysics-achievements.tsx")
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")

    for field in ("pattern_title", "pattern_status", "formation_path", "memorable_line", "hero_tags"):
        assert field in identity
    for field in ("comparison_label", "next_activation", "month_preview"):
        assert field in identity
    assert "overflow-x-auto" in identity, "the twelve-month preview should scroll inside its own region"

    assert "稀有结构组合" in achievements
    assert "命盘成就" not in achievements
    assert "命盘成就" not in chart
    assert "分享成就卡" not in chart
    assert chart.count("分享与导出") == 1
    for decision_step in ("主导结构", "命中规则", "已核验命题"):
        assert decision_step in chart


def test_bazi_pattern_source_chain_uses_only_canonical_claim_ids_and_fetches_real_sources_on_demand():
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")
    api = read("frontend/src/lib/api.ts")
    types = read("frontend/src/types/api.ts")

    assert 'claim.slot === "hero"' in chart
    assert "hero.ruleIds" in chart
    assert "hero.sourceIds" in chart
    assert 'claim.ruleIds.length && claim.sourceIds.length' in chart
    assert "PatternSourceDisclosure" in chart
    assert "fetchPatternRuleSummary" in chart
    assert "命题索引" not in chart
    assert "Classical proposition" not in chart
    assert "已核验影印定位" in chart
    assert "visually_verified" in chart
    assert 'key={`${patternBundleId}:${heroRuleIds.join(",")}:${heroSourceIds.join(",")}`}' in chart
    assert "requestedSources.has(source.proposition_id)" in chart
    assert 'locator.review_state === "scan_verified"' in chart
    assert "Boolean(locator.quote)" in chart
    assert "Boolean(locator.url || locator.pdf_page || locator.printed_page || locator.column_line)" in chart
    assert "打开影印页" in chart
    assert 'target="_blank"' in chart

    assert "export async function fetchPatternRuleSummary" in api
    assert "/api/tools/metaphysics/pattern-rules/" in api
    assert "encodeURIComponent(bundleId)" in api
    assert "encodeURIComponent(ruleId)" in api

    for type_name in (
        "PatternRuleSourceLocator",
        "PatternRuleSourceSummary",
        "PatternRuleSummary",
    ):
        assert f"export type {type_name}" in types
    for field in ("proposition_id", "witness_id", "visually_verified", "quote", "pdf_page", "url"):
        assert field in types


def test_task8_markdown_uses_consumer_display_semantics_not_raw_percentile_buckets():
    markdown = read("frontend/src/lib/chart-markdown.ts")

    assert "display_label" in markdown
    assert "display_mode" in markdown
    for internal_bucket in ("lower_percentage", "same_percentage", "higher_percentage"):
        assert internal_bucket not in markdown
    assert "稀有结构组合" in markdown
    assert "命盘成就" not in markdown


def test_task8_chart_report_contains_wide_content_at_390px_without_page_overflow():
    css = read("frontend/src/app/globals.css")
    chart = read("frontend/src/components/tools/bazi-chart-view.tsx")
    identity = read("frontend/src/components/tools/consumer-identity.tsx")

    report_rule_start = css.index(".chart-report {")
    report_rule = css[report_rule_start : css.index("}", report_rule_start)]
    scroll_rule_start = css.index(".chart-report .overflow-x-auto {")
    scroll_rule = css[scroll_rule_start : css.index("}", scroll_rule_start)]
    mobile_rule_start = css.index("@media (max-width: 390px)")
    mobile_rule = css[mobile_rule_start:]

    for declaration in ("width: 100%", "min-width: 0", "max-width: 100%", "overflow-x: clip"):
        assert declaration in report_rule
    for declaration in ("max-width: 100%", "overflow-x: auto", "overscroll-behavior-inline: contain"):
        assert declaration in scroll_rule
    assert "overflow-wrap: anywhere" in mobile_rule
    assert "overflow-wrap: normal" in mobile_rule
    assert "overflow-x-auto" in chart, "professional tables should retain internal horizontal scrolling"
    assert "overflow-x-auto" in identity, "the month preview should retain internal horizontal scrolling"


def test_e2e_review_uses_one_source_trust_resolver_in_passages_and_chart_preview():
    resolver_path = ROOT / "frontend/src/lib/source-labels.ts"
    assert resolver_path.exists(), "source labels need one shared trust boundary"
    resolver = resolver_path.read_text(encoding="utf-8")
    results = read("frontend/src/components/workspace/results-panel.tsx")
    visual = read("frontend/src/components/workspace/hexagram-visual.tsx")

    assert "export function sourceDisplayLabel" in resolver
    assert 'return locale === "zh" ? "来源待核" : "Source unverified"' in resolver
    for known_source in ("takashima", "english_commentary", "symbolic", "guaci"):
        assert known_source in resolver
    assert 'from "@/lib/source-labels"' in results
    assert 'from "@/lib/source-labels"' in visual
    assert "function sourceDisplayLabel" not in results
    assert "sourceDisplayLabel(section.source, locale)" in visual
    assert "section.source_label || section.source" not in visual


def test_e2e_review_waits_for_persisted_form_before_applying_url_precedence():
    cast_form = read("frontend/src/components/workspace/cast-form.tsx")

    assert "useWorkspaceStore.persist.hasHydrated()" in cast_form
    assert "useWorkspaceStore.persist.onFinishHydration" in cast_form
    assert "useSyncExternalStore" in cast_form
    assert "storeHydrated" in cast_form
    hydration_effect = cast_form[cast_form.index("const storeHydrated") : cast_form.index("const mutation = useSessionMutation")]
    assert "setStoreHydrated" not in hydration_effect
    assert "if (!storeHydrated) return" in hydration_effect
    assert "unsubscribeFromStart()" in cast_form
    assert "unsubscribeFromFinish()" in cast_form
    assert 'const persistedTopic = config.topics.some((topic) => topic.label === current.topic) ? current.topic : ""' in hydration_effect
    assert "requestedIntent?.topic || persistedTopic || preferredTopic" in hydration_effect
    assert "explicitQuestion || draftedQuestion || requestedIntent?.questionHint" in hydration_effect
    assert "if (!value || !config.topics.some((topic) => topic.label === value)) return" in cast_form
    assert 'updateForm("topic", value)' in cast_form


def test_e2e_review_export_button_has_parent_name_and_separate_live_status():
    button = read("frontend/src/components/tools/chart-export-button.tsx")

    assert "aria-label={exporting ? loadingLabel : label}" in button
    assert '<span role="status">' not in button
    assert 'role="status"' in button
    assert 'aria-live="polite"' in button
    assert 'className="sr-only"' in button
    assert button.index("</Button>") < button.index('role="status"')


def test_najia_table_uses_compact_rows_without_duplicate_line_preview():
    najia = read("frontend/src/components/workspace/najia-table.tsx")

    assert 'overflow-hidden border-y' in najia
    assert "grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1fr)]" in najia
    assert "row.movement_tag" in najia
    assert "×→" not in najia
    assert "○→" not in najia
    assert "row.main_mark" not in najia
    assert "row.changed_mark" not in najia
    assert "row.marker" in najia
    assert "min-h-12" in najia
    assert "LineSvg" in najia
    assert "imperial-text" in najia


def test_chat_panel_feels_like_native_ai_conversation_surface():
    chat = read("frontend/src/components/workspace/chat-panel.tsx")

    assert "min-h-[42rem]" in chat
    assert "flex-1 flex-col gap-5 overflow-y-auto" in chat
    assert "w-full max-w-3xl border-l border-primary/35 pl-4" in chat
    assert "surface-soft rounded-lg border border-border/50 p-2" in chat
    assert "min-h-20 border-0 bg-transparent" in chat
    assert "streamChatMessage" in chat
    assert "abortRef.current?.abort()" in chat
    assert "Regenerate" in chat


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
