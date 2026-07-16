"use client"

import { useEffect, useId, useState } from "react"
import { ChevronRight } from "lucide-react"
import { ChartExportButton } from "@/components/tools/chart-export-button"
import { ChartAssetExportButton } from "@/components/tools/chart-asset-export-button"
import { ConsumerIdentity } from "@/components/tools/consumer-identity"
import { LifeKlineChart } from "@/components/tools/life-kline-chart"
import { MetaphysicsAchievements, type MetaphysicsAchievement } from "@/components/tools/metaphysics-achievements"
import { buildBaziMarkdown } from "@/lib/chart-markdown"
import { calculateMetaphysicsChart, fetchMetaphysicsPeriod } from "@/lib/api"
import type { DayunCycle, MetaphysicsChart, PeriodMonth, PeriodYear, RarityMetric, ShenShaHit, ThemeComparison, ThemeProfile } from "@/types/api"

type Locale = "en" | "zh"
type DisplayMode = "simple" | "study" | "professional"
type SolarTerm = NonNullable<MetaphysicsChart["next_solar_term"]>
type BaziChartViewProps =
  | { chart: MetaphysicsChart; locale: Locale; mode: "current"; generatedAt?: never; onCompare?: never }
  | { chart: MetaphysicsChart; locale: Locale; mode: "birth"; generatedAt: string; subjectName: string; onCompare?: () => void }

function formatChartTimestamp(timestamp: string, locale: Locale, timeZone: string) {
  return new Date(timestamp).toLocaleString(locale === "zh" ? "zh-CN" : "en-US", { timeZone })
}

function currentYearInTimeZone(timeZone: string) {
  return Number(new Intl.DateTimeFormat("en", { timeZone, year: "numeric" }).format(new Date()))
}

export function BaziChartView(props: BaziChartViewProps) {
  const { chart, locale, mode } = props
  const exportTargetId = `bazi-export-${useId().replaceAll(":", "")}`
  const tableExportTargetId = `bazi-table-${useId().replaceAll(":", "")}`
  const facts = chart.calendar_facts
  const currentYear = currentYearInTimeZone(chart.timezone)
  const dayun = chart.birth_profile.dayun
  const [periodCycles, setPeriodCycles] = useState(dayun.cycles)
  const [periodLoadingIndex, setPeriodLoadingIndex] = useState<number | null>(null)
  const [periodError, setPeriodError] = useState<string | null>(null)
  const currentCycle = periodCycles.find((cycle) => cycle.is_current)
    ?? periodCycles.find((cycle) => cycle.start_year <= currentYear && currentYear <= cycle.end_year)
  const [selectedCycleIndex, setSelectedCycleIndex] = useState(() => currentCycle?.index ?? dayun.cycles[0]?.index ?? 0)
  const initialYear = dayun.current?.year?.year ?? currentYear
  const [selectedYear, setSelectedYear] = useState(initialYear)
  const [selectedMonthIndex, setSelectedMonthIndex] = useState(() => dayun.current?.month?.index ?? 0)
  const [displayMode, setDisplayMode] = useState<DisplayMode>("simple")
  useEffect(() => {
    const saved = window.localStorage.getItem("iching:bazi-display-mode")
    if (saved !== "simple" && saved !== "study" && saved !== "professional") return
    const frame = window.requestAnimationFrame(() => setDisplayMode(saved))
    return () => window.cancelAnimationFrame(frame)
  }, [])
  useEffect(() => {
    const nextCurrent = dayun.cycles.find((cycle) => cycle.is_current) ?? dayun.cycles[0]
    setPeriodCycles(dayun.cycles)
    setSelectedCycleIndex(nextCurrent?.index ?? 0)
    setSelectedYear(dayun.current?.year?.year ?? nextCurrent?.years[0]?.year ?? currentYear)
    setSelectedMonthIndex(dayun.current?.month?.index ?? 0)
    setPeriodError(null)
  }, [chart.input_timestamp, currentYear, dayun])
  function changeDisplayMode(nextMode: DisplayMode) {
    setDisplayMode(nextMode)
    window.localStorage.setItem("iching:bazi-display-mode", nextMode)
  }
  async function selectCycle(cycle: DayunCycle) {
    setSelectedCycleIndex(cycle.index)
    setPeriodError(null)
    if (cycle.years.length || !chart.birth_profile.period_query) {
      setSelectedYear(cycle.years.find((year) => year.is_current)?.year ?? cycle.years[0]?.year ?? cycle.start_year)
      setSelectedMonthIndex(cycle.years.find((year) => year.is_current)?.months.find((month) => month.is_current)?.index ?? 0)
      return
    }
    setPeriodLoadingIndex(cycle.index)
    try {
      const loaded = await fetchMetaphysicsPeriod({ ...chart.birth_profile.period_query, cycle_index: cycle.index })
      setPeriodCycles((items) => items.map((item) => item.index === loaded.index ? loaded : item))
      setSelectedYear(loaded.years.find((year) => year.is_current)?.year ?? loaded.years[0]?.year ?? loaded.start_year)
      setSelectedMonthIndex(loaded.years.find((year) => year.is_current)?.months.find((month) => month.is_current)?.index ?? 0)
    } catch {
      setPeriodError(locale === "zh" ? "这一段运限暂时未载入，请重试。" : "This period could not be loaded. Try again.")
    } finally {
      setPeriodLoadingIndex(null)
    }
  }
  const calculationRule = [
    chart.calculation_mode === "true_solar"
      ? (locale === "zh" ? "真太阳时" : "True solar time")
      : (locale === "zh" ? "标准时间" : "Standard civil time"),
    chart.day_boundary === "forward"
      ? (locale === "zh" ? "晚子时换日" : "Late Zi advances the day")
      : (locale === "zh" ? "子时不提前换日" : "Zi hour stays on the current day"),
  ].join(" · ")

  if (mode === "current") {
    return <CurrentBaziView chart={chart} locale={locale} />
  }

  const { generatedAt, subjectName } = props
  const markdown = buildBaziMarkdown(chart, subjectName, locale)

  const trustNote = locale === "zh"
    ? "按出生地时间与精确节气排盘，并结合传统命理规则与历法统计进行分析。"
    : "Calculated from local birth time and exact solar terms, then interpreted with traditional rules and calendar statistics."
  const currentCycleText = currentCycle
    ? `${currentCycle.label} · ${currentCycle.start_year}–${currentCycle.end_year}`
    : (locale === "zh" ? "当前年份不在已列周期内" : "Current year is outside the listed cycles")
  const resultGeneratedAt = generatedAt

  if (chart.birth_profile.hour_uncertain) {
    return <UncertainBaziView chart={chart} locale={locale} subjectName={subjectName} generatedAt={resultGeneratedAt} calculationRule={calculationRule} exportTargetId={exportTargetId} markdown={markdown} />
  }

  if (chart.consumer?.identity) {
    return <BaziConsumerResult
      chart={chart}
      locale={locale}
      subjectName={subjectName}
      generatedAt={resultGeneratedAt}
      calculationRule={calculationRule}
      currentCycleText={currentCycleText}
      trustNote={trustNote}
      exportTargetId={exportTargetId}
      tableExportTargetId={tableExportTargetId}
      markdown={markdown}
      periodCycles={periodCycles}
      currentYear={currentYear}
      selectedCycleIndex={selectedCycleIndex}
      selectedYear={selectedYear}
      selectedMonthIndex={selectedMonthIndex}
      periodLoadingIndex={periodLoadingIndex}
      periodError={periodError}
      onCycleChange={(cycle) => void selectCycle(cycle)}
      onYearChange={(year) => { setSelectedYear(year.year); setSelectedMonthIndex(0) }}
      onMonthChange={(month) => setSelectedMonthIndex(month.index)}
      onCompare={props.onCompare}
    />
  }

  return (
    <section className="chart-report space-y-8" aria-label={locale === "zh" ? "八字排盘结果" : "BaZi chart result"}>
      <div data-export-exclude className="flex justify-end">
        <ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出命盘" : "Export chart"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "命盘图片生成失败，请重试。" : "Chart image could not be generated. Try again."} safeBaseFilename={`bazi-${chart.birth_profile.input_date}`} copyLabel={locale === "zh" ? "复制 Markdown" : "Copy Markdown"} copySuccess={locale === "zh" ? "Markdown 已复制" : "Markdown copied"} copyError={locale === "zh" ? "复制失败，请改用下载。" : "Copy failed. Use the download instead."} />
      </div>

      <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={resultGeneratedAt} trustNote={trustNote} />

      <DisplayModeControl mode={displayMode} locale={locale} onChange={changeDisplayMode} />

      <ChartSectionNav locale={locale} mode={displayMode} />

      <ReportChapter id="bazi-chart" title={locale === "zh" ? "命盘" : "Chart"} intro={locale === "zh" ? "四柱、十神、藏干与神煞按列对照；左侧字段固定，手机可横向滑动。" : "Compare pillars, Ten Gods, hidden stems, and Shen Sha by column. The field column stays visible on mobile."}>
        <div data-export-exclude className="mb-3 flex justify-end"><ChartAssetExportButton targetId={tableExportTargetId} label={locale === "zh" ? "单独导出四柱表" : "Export pillar table"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "四柱表导出失败。" : "Pillar table export failed."} safeBaseFilename={`bazi-pillars-${chart.birth_profile.input_date}`} /></div>
        <div id={tableExportTargetId}><BaziProfessionalTable chart={chart} locale={locale} /></div>
      </ReportChapter>

      <ReportChapter id="bazi-synthesis" title={locale === "zh" ? "核心判断" : "Key findings"}>
        <BaziSynthesisPanel chart={chart} locale={locale} />
      </ReportChapter>

      <ReportChapter id="bazi-periods" title={locale === "zh" ? "运限" : "Periods"} intro={locale === "zh" ? "依次选择大运、流年和流月，查看这一阶段新增或被触发的结构。当前标记按精确交接时刻定位。" : "Select a Da Yun, year, and month to see structures activated in that period. Current markers use exact handoff instants."}>
        <BaziPeriodNavigator
          cycles={periodCycles}
          locale={locale}
          currentYear={currentYear}
          selectedCycleIndex={selectedCycleIndex}
          selectedYear={selectedYear}
          selectedMonthIndex={selectedMonthIndex}
          loadingCycleIndex={periodLoadingIndex}
          error={periodError}
          onCycleChange={(cycle) => void selectCycle(cycle)}
          onYearChange={(year) => { setSelectedYear(year.year); setSelectedMonthIndex(0) }}
          onMonthChange={(month) => setSelectedMonthIndex(month.index)}
        />
      </ReportChapter>

      {displayMode !== "simple" ? <ReportChapter id="bazi-statistics" title={locale === "zh" ? "结构统计" : "Structure statistics"} intro={locale === "zh" ? "看看哪些结构更有辨识度，以及它们在历法样本中的分布位置。" : "See which structures are more distinctive and where they sit in the calendar-sample distribution."}>
        <div className="space-y-8">
          <ThemeProfilePanel profiles={chart.theme_profiles ?? chart.structure?.theme_profiles ?? []} baselineLabel={chart.statistics.baseline.label} locale={locale} />
          <BaziStatistics chart={chart} locale={locale} currentYear={currentYear} />
        </div>
      </ReportChapter> : null}

      {displayMode !== "simple" ? <ReportChapter id="bazi-shensha" title={locale === "zh" ? "神煞" : "Shen Sha"} intro={locale === "zh" ? "神煞作为辅助线索呈现；点击可查看命中位置、频率与传统依据。" : "Shen Sha appears as supporting evidence; open an item for its position, frequency, and source."}>
        <ShenShaPanel chart={chart} locale={locale} />
      </ReportChapter> : null}

      {displayMode === "professional" ? <ReportChapter title={locale === "zh" ? "排盘规则与版本" : "Rules and versions"}>
        <div className="space-y-8">
          <div><p className="text-sm">{chart.previous_solar_term?.name || "—"} → {chart.next_solar_term?.name || "—"}</p>{chart.next_solar_term ? <HistoricalSolarTerm term={chart.next_solar_term} calculationTimestamp={chart.calculation_timestamp} locale={locale} timeZone={chart.timezone} /> : null}</div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <RawFact label={locale === "zh" ? "旬空" : "Void branches"} value={chart.xunkong} />
            <RawFact label={locale === "zh" ? "月建冲合" : "Month clash/combine"} value={`${facts.month_command} · ${facts.month_clash} · ${facts.month_combine}`} />
            <RawFact label={locale === "zh" ? "日辰冲合" : "Day clash/combine"} value={`${facts.day_pillar} · ${facts.day_clash} · ${facts.day_combine}`} />
            <RawFact label={locale === "zh" ? "六神" : "Six spirits"} value={`${facts.six_spirit_start} · ${facts.six_spirits.join(" · ")}`} />
          </div>
          {chart.birth_profile.hour_uncertain ? <HourCandidates candidates={chart.birth_profile.hour_candidates} locale={locale} /> : null}
          <div><h3 className="text-sm font-semibold">{locale === "zh" ? "原始大运周期" : "Raw Da Yun cycles"}</h3><div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{dayun.cycles.map((cycle) => <p key={cycle.index} className="text-xs leading-5 text-muted-foreground">{cycle.index}. {cycle.ganzhi} · {cycle.start_age}–{cycle.end_age} · {cycle.start_year}–{cycle.end_year}</p>)}</div></div>
          <p className="text-xs leading-5 text-muted-foreground">{Object.values(chart.birth_profile.engines).join(" · ")} · {chart.rules_version} · {chart.statistics.baseline.id}</p>
          <p className="text-xs leading-5 text-muted-foreground">{chart.statistics.disclaimer}</p>
        </div>
      </ReportChapter> : null}

      <BaziExportCanvas exportTargetId={exportTargetId} chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={resultGeneratedAt} trustNote={trustNote} />
    </section>
  )
}

type ConsumerTab = "identity" | "kline" | "chart"

function BaziConsumerResult({
  chart, locale, subjectName, generatedAt, calculationRule, currentCycleText, trustNote,
  exportTargetId, tableExportTargetId, markdown, periodCycles, currentYear,
  selectedCycleIndex, selectedYear, selectedMonthIndex, periodLoadingIndex, periodError,
  onCycleChange, onYearChange, onMonthChange,
  onCompare,
}: {
  chart: MetaphysicsChart
  locale: Locale
  subjectName: string
  generatedAt: string
  calculationRule: string
  currentCycleText: string
  trustNote: string
  exportTargetId: string
  tableExportTargetId: string
  markdown: string
  periodCycles: DayunCycle[]
  currentYear: number
  selectedCycleIndex: number
  selectedYear: number
  selectedMonthIndex: number
  periodLoadingIndex: number | null
  periodError: string | null
  onCycleChange: (cycle: DayunCycle) => void
  onYearChange: (year: PeriodYear) => void
  onMonthChange: (month: PeriodMonth) => void
  onCompare?: () => void
}) {
  const [tab, setTab] = useState<ConsumerTab>("identity")
  const identityCardId = `bazi-identity-${useId().replaceAll(":", "")}`
  const achievementCardId = `bazi-achievements-${useId().replaceAll(":", "")}`
  const klineCardId = `bazi-kline-${useId().replaceAll(":", "")}`
  const consumer = chart.consumer!
  const [lifeKline, setLifeKline] = useState(consumer.life_kline)
  const [fullLifeLoading, setFullLifeLoading] = useState(false)
  const [fullLifeError, setFullLifeError] = useState<string | null>(null)
  useEffect(() => {
    setLifeKline(consumer.life_kline)
    setFullLifeError(null)
  }, [consumer.life_kline])
  const profile = {
    identity: consumer.identity,
    subjects: consumer.subjects,
    fingerprints: consumer.fingerprints,
    twin: consumer.twin,
  }
  const achievementStates = new Set(["发力", "有力", "可见", "受制"])
  const achievements = consumer.achievements
    .filter((item) => achievementStates.has(item.state)) as MetaphysicsAchievement[]
  const tabs: Array<{ key: ConsumerTab; label: string; description: string }> = locale === "zh"
    ? [
      { key: "identity", label: "我是谁", description: "称号、路径与命盘成就" },
      { key: "kline", label: "人生 K 线", description: "未来十年与月份节奏" },
      { key: "chart", label: "完整命盘", description: "四柱、运限与全部依据" },
    ]
    : [
      { key: "identity", label: "Identity", description: "Archetype, paths, achievements" },
      { key: "kline", label: "Life K-line", description: "Ten-year and monthly rhythm" },
      { key: "chart", label: "Full chart", description: "Pillars, periods, all details" },
    ]

  async function loadFullLifeKline() {
    const request = chart.birth_profile.period_query
    if (!request || fullLifeLoading) return
    setFullLifeLoading(true)
    setFullLifeError(null)
    try {
      const expanded = await calculateMetaphysicsChart({ ...request, include_period_details: true, period_cycle_index: null })
      if (!expanded.consumer?.life_kline.series.some((series) => series.points.length > 10)) throw new Error(locale === "zh" ? "完整人生走势暂时未生成。" : "The full-life series is not available yet.")
      setLifeKline(expanded.consumer.life_kline)
    } catch (cause) {
      setFullLifeError((cause as Error).message)
    } finally {
      setFullLifeLoading(false)
    }
  }

  return <section className="chart-report min-w-0 space-y-6" aria-label={locale === "zh" ? "八字命盘结果" : "BaZi result"}>
    <div data-export-exclude className="flex justify-end">
      <ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "一键导出" : "Export"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "命盘图片生成失败，请重试。" : "Chart image could not be generated."} safeBaseFilename={`bazi-${chart.birth_profile.input_date}`} copyLabel={locale === "zh" ? "复制 Markdown" : "Copy Markdown"} copySuccess={locale === "zh" ? "Markdown 已复制" : "Markdown copied"} copyError={locale === "zh" ? "复制失败，请改用下载。" : "Copy failed."} />
    </div>

    <nav data-export-exclude aria-label={locale === "zh" ? "八字结果主导航" : "BaZi result navigation"} className="sticky top-20 z-20 grid grid-cols-3 gap-1 rounded-2xl border border-border/60 bg-background/90 p-1.5 shadow-sm backdrop-blur">
      {tabs.map((item) => <button key={item.key} type="button" aria-pressed={tab === item.key} onClick={() => setTab(item.key)} className={`min-w-0 rounded-xl px-2 py-3 text-center transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${tab === item.key ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:bg-primary/8 hover:text-foreground"}`}><span className="block text-sm font-semibold sm:text-base">{item.label}</span><span className={`mt-1 hidden text-[0.68rem] sm:block ${tab === item.key ? "text-primary-foreground/75" : "text-muted-foreground"}`}>{item.description}</span></button>)}
    </nav>

    {tab === "identity" ? <div className="space-y-9">
      <div data-export-exclude className="flex flex-wrap justify-end gap-2"><ChartAssetExportButton targetId={identityCardId} label={locale === "zh" ? "分享身份卡" : "Share identity card"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "身份卡生成失败。" : "Identity card could not be generated."} safeBaseFilename={`bazi-identity-${chart.birth_profile.input_date}`} /></div>
      <div id={identityCardId}><ConsumerIdentity profile={profile} locale={locale} comparisonAction={onCompare ? { label: locale === "zh" ? "双人命盘比较" : "Compare two charts", onClick: onCompare } : undefined} /></div>
      <div data-export-exclude className="flex flex-wrap justify-end gap-2"><ChartAssetExportButton targetId={achievementCardId} label={locale === "zh" ? "分享成就卡" : "Share achievements"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "成就卡生成失败。" : "Achievement card could not be generated."} safeBaseFilename={`bazi-achievements-${chart.birth_profile.input_date}`} /></div>
      <div id={achievementCardId}><MetaphysicsAchievements achievements={achievements} locale={locale} /></div>
    </div> : null}

    {tab === "kline" ? <div className="space-y-8">
      <div data-export-exclude className="flex justify-end"><ChartAssetExportButton targetId={klineCardId} label={locale === "zh" ? "分享人生 K 线" : "Share Life K-line"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "K 线图片生成失败。" : "K-line image could not be generated."} safeBaseFilename={`bazi-kline-${chart.birth_profile.input_date}`} /></div>
      <div id={klineCardId}><LifeKlineChart lifeKline={lifeKline} locale={locale} currentYear={currentYear} fullLifeLoading={fullLifeLoading} onRequestFullLife={chart.birth_profile.period_query ? loadFullLifeKline : undefined} /></div>
      {fullLifeError ? <p role="alert" className="text-sm text-destructive">{fullLifeError}</p> : null}
      <section className="rounded-3xl border border-border/60 bg-surface p-5 sm:p-7"><h2 className="text-xl font-semibold">{locale === "zh" ? "点开阶段看细节" : "Open a period"}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{locale === "zh" ? "选择大运、流年和流月，查看这一阶段新增、联动和冲突的具体结构。" : "Choose a cycle, year, and month to inspect its activated structures."}</p><div className="mt-5"><BaziPeriodNavigator cycles={periodCycles} locale={locale} currentYear={currentYear} selectedCycleIndex={selectedCycleIndex} selectedYear={selectedYear} selectedMonthIndex={selectedMonthIndex} loadingCycleIndex={periodLoadingIndex} error={periodError} onCycleChange={onCycleChange} onYearChange={onYearChange} onMonthChange={onMonthChange} /></div></section>
    </div> : null}

    {tab === "chart" ? <div className="space-y-9">
      <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={generatedAt} trustNote={trustNote} />
      <ReportChapter title={locale === "zh" ? "四柱命盘" : "Four pillars"} intro={locale === "zh" ? "四柱、十神、藏干、神煞与状态集中在同一张专业表。" : "Pillars, Ten Gods, hidden stems, and Shen Sha in one table."}><div data-export-exclude className="mb-3 flex justify-end"><ChartAssetExportButton targetId={tableExportTargetId} label={locale === "zh" ? "单独导出四柱表" : "Export pillar table"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "四柱表导出失败。" : "Pillar table export failed."} safeBaseFilename={`bazi-pillars-${chart.birth_profile.input_date}`} /></div><div id={tableExportTargetId}><BaziProfessionalTable chart={chart} locale={locale} /></div></ReportChapter>
      <ReportChapter title={locale === "zh" ? "格局与核心判断" : "Pattern and findings"}><BaziPatternSummary chart={chart} locale={locale} /><div className="mt-7"><BaziSynthesisPanel chart={chart} locale={locale} /></div></ReportChapter>
      <ReportChapter title={locale === "zh" ? "运限" : "Periods"}><BaziPeriodNavigator cycles={periodCycles} locale={locale} currentYear={currentYear} selectedCycleIndex={selectedCycleIndex} selectedYear={selectedYear} selectedMonthIndex={selectedMonthIndex} loadingCycleIndex={periodLoadingIndex} error={periodError} onCycleChange={onCycleChange} onYearChange={onYearChange} onMonthChange={onMonthChange} /></ReportChapter>
      <ReportChapter title={locale === "zh" ? "结构对照" : "Structure comparisons"}><ThemeProfilePanel profiles={chart.theme_profiles ?? chart.structure?.theme_profiles ?? []} baselineLabel={chart.statistics.baseline.label} locale={locale} /></ReportChapter>
      <ReportChapter title={locale === "zh" ? "神煞全表" : "Shen Sha"}><ShenShaPanel chart={chart} locale={locale} /></ReportChapter>
      <details className="rounded-2xl border border-border/60 bg-surface px-5 py-4"><summary className="cursor-pointer text-sm font-semibold text-primary">{locale === "zh" ? "查看排盘规则与原始统计" : "Chart rules and raw statistics"}</summary><div className="mt-6 space-y-7"><BaziStatistics chart={chart} locale={locale} currentYear={currentYear} /><p className="text-xs leading-5 text-muted-foreground">{Object.values(chart.birth_profile.engines).join(" · ")} · {chart.rules_version} · {chart.statistics.baseline.id}</p></div></details>
    </div> : null}

    <BaziExportCanvas exportTargetId={exportTargetId} chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={generatedAt} trustNote={trustNote} />
  </section>
}

function BaziPatternSummary({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const primary = chart.structure.patterns?.primary
  if (!primary) return <p className="text-sm text-muted-foreground">{locale === "zh" ? "这张命盘以主导结构呈现，不强贴单一格局标签。" : "This chart is described by its dominant structure rather than a forced pattern label."}</p>
  const statusLabels: Record<string, string> = { formed: "成格", candidate: "候选", effective: "得用", broken: "受制", rescued: "救成", mixed: "混杂", transformed: "转化" }
  const selectionLabels: Record<string, string> = { month_main_qi: "月令本气", month_hidden_exposed: "藏气透干", month_meeting: "合会取格", strict_special_gates: "特殊格严格成立" }
  const integrityLabels: Record<string, string> = { complete: "完整", minor_damage: "有局部牵制", rescued: "破而有救", broken: "受损" }
  const purityLabels: Record<string, string> = { clear: "清", combined: "兼见", mixed: "混杂" }
  const strengthLabels: Record<string, string> = { effective: "有力", ordinary: "可用", weak: "偏弱", none: "未定" }
  const allEvidence = (chart.structure.patterns?.evidence ?? []) as Array<{ id?: string; kind?: string; detail?: string }>
  const evidence = allEvidence.filter((item) => item.id && primary.evidence_ids?.includes(item.id))
  const pathTitle = primary.formation_path?.title
  const dimensions = [
    [locale === "zh" ? "取格" : "Selection", selectionLabels[primary.selection ?? ""] ?? primary.selection],
    [locale === "zh" ? "成格路径" : "Formation path", pathTitle],
    [locale === "zh" ? "完整性" : "Integrity", integrityLabels[primary.integrity ?? ""] ?? primary.integrity],
    [locale === "zh" ? "清浊" : "Purity", purityLabels[primary.purity ?? ""] ?? primary.purity],
    [locale === "zh" ? "力度" : "Strength", typeof primary.strength === "string" ? (strengthLabels[primary.strength] ?? primary.strength) : undefined],
  ].filter((item): item is [string, string] => Boolean(item[1]))
  return (
    <section className="rounded-2xl bg-primary/[0.06] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-2xl font-semibold">{primary.title || `${primary.name}格`}</h3>
        <span className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">{statusLabels[primary.status] || primary.status}</span>
      </div>
      <p className="mt-3 text-sm leading-7 text-muted-foreground">{primary.summary}</p>
      {dimensions.length ? <dl className="mt-5 grid gap-px overflow-hidden rounded-xl border border-border/50 bg-border/50 sm:grid-cols-3 lg:grid-cols-5">{dimensions.map(([label, value]) => <div key={label} className="bg-surface px-3 py-3"><dt className="text-[0.68rem] font-semibold text-muted-foreground">{label}</dt><dd className="mt-1 text-sm font-semibold text-foreground">{value}</dd></div>)}</dl> : null}
      {primary.rescues?.length ? <p className="mt-4 text-sm"><strong>{locale === "zh" ? "救应" : "Rescue"}：</strong>{primary.rescues.join(" · ")}</p> : null}
      {primary.tensions?.length ? <p className="mt-2 text-sm"><strong>{locale === "zh" ? "结构张力" : "Structural tension"}：</strong>{primary.tensions.join(" · ")}</p> : null}
      {primary.constraints?.length ? <p className="mt-2 text-sm"><strong>{locale === "zh" ? "制约" : "Constraints"}：</strong>{primary.constraints.join(" · ")}</p> : null}
      {evidence.length ? <details className="mt-5 border-t border-border/50 pt-4"><summary className="cursor-pointer text-sm font-semibold text-primary">{locale === "zh" ? "为什么这样判断" : "Why this pattern"}</summary><ol className="mt-3 space-y-2">{evidence.map((item, index) => <li key={item.id ?? index} className="flex gap-2 text-sm leading-6 text-muted-foreground"><span aria-hidden="true" className="font-semibold text-primary">{item.kind === "tension" ? "△" : "✓"}</span><span>{item.detail}</span></li>)}</ol></details> : null}
    </section>
  )
}

function UncertainBaziView({ chart, locale, subjectName, generatedAt, calculationRule, exportTargetId, markdown }: { chart: MetaphysicsChart; locale: Locale; subjectName: string; generatedAt: string; calculationRule: string; exportTargetId: string; markdown: string }) {
  const stability = chart.birth_profile.stability
  const findings = chart.synthesis?.conclusions ?? []
  return <section id={exportTargetId} className="chart-report space-y-7" aria-label={locale === "zh" ? "时辰待定八字分析" : "BaZi analysis with uncertain hour"}>
    <div data-export-exclude className="flex justify-end"><ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出稳定分析" : "Export stable analysis"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "图片生成失败，请重试。" : "Image generation failed. Try again."} safeBaseFilename={`bazi-stable-${chart.birth_profile.input_date}`} copyLabel={locale === "zh" ? "复制 Markdown" : "Copy Markdown"} copySuccess={locale === "zh" ? "Markdown 已复制" : "Markdown copied"} copyError={locale === "zh" ? "复制失败" : "Copy failed"} /></div>
    <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={locale === "zh" ? "补充时辰后显示" : "Available after adding the birth hour"} generatedAt={generatedAt} trustNote={locale === "zh" ? "先呈现所有可能时辰中都成立的部分；补充时辰后自动解锁完整命盘与运限。" : "This view starts with what remains true across every possible birth hour. Add the hour to unlock the full chart and periods."} />
    <section className="rounded-2xl border border-primary/25 bg-primary/[0.045] p-5"><p className="text-xs font-semibold text-primary">{locale === "zh" ? `已对照 ${stability?.candidate_count ?? 13} 个可能时辰` : `Compared ${stability?.candidate_count ?? 13} possible hours`}</p><h2 className="mt-2 text-2xl font-semibold">{locale === "zh" ? "先看不受时辰影响的部分" : "Start with what stays stable"}</h2><p className="mt-2 text-sm leading-7 text-muted-foreground">{locale === "zh" ? "这些内容在早子到晚子的候选盘中都成立，不需要等到确认时辰才有价值。" : "These findings hold from early Zi through late Zi, so the chart remains useful before the exact hour is known."}</p></section>
    <section><h2 className="text-xl font-semibold">{locale === "zh" ? "稳定四柱" : "Stable pillars"}</h2><div className="mt-4 grid gap-3 sm:grid-cols-3">{(stability?.stable_pillars ?? []).map((item) => <div key={item.label} className="rounded-2xl border border-border/55 bg-surface p-4 text-center"><p className="text-xs font-semibold text-muted-foreground">{item.label}{locale === "zh" ? "柱" : " pillar"}</p><p className="mt-3"><span data-element={item.pillar.stem_element} className="chart-element-text text-4xl font-semibold">{item.pillar.stem}</span><span data-element={item.pillar.branch_element} className="chart-element-text ml-2 text-4xl font-semibold">{item.pillar.branch}</span></p><p className="mt-2 text-xs text-muted-foreground">{item.pillar.ten_god}</p></div>)}</div></section>
    <section><h2 className="text-xl font-semibold">{locale === "zh" ? "稳定判断" : "Stable findings"}</h2>{findings.length ? <div className="mt-4 grid gap-3 lg:grid-cols-2">{findings.map((item) => <article key={item.id} className="rounded-2xl border border-border/55 bg-surface p-5"><p className="text-xs font-semibold text-primary">{item.theme}</p><h3 className="mt-2 text-lg font-semibold leading-7">{item.headline}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{item.body}</p></article>)}</div> : <p className="mt-3 text-sm text-muted-foreground">{locale === "zh" ? "当前三柱没有跨全部时辰都一致的主题结论。" : "No theme-level finding remains identical across every possible hour."}</p>}</section>
    {stability?.stable_shensha.length ? <section><h2 className="text-xl font-semibold">{locale === "zh" ? "稳定命中的核心线索" : "Stable supporting markers"}</h2><div className="mt-3 flex flex-wrap gap-2">{stability.stable_shensha.map((name) => <span key={name} className="rounded-full bg-primary/8 px-3 py-1.5 text-sm font-semibold text-primary">{name}</span>)}</div></section> : null}
    <section><h2 className="text-xl font-semibold">{locale === "zh" ? "确认时辰后会进一步明确" : "What the exact hour will clarify"}</h2><div className="mt-4 grid gap-3 sm:grid-cols-2">{(stability?.sensitive_items ?? []).map((item) => <div key={item.label} className="rounded-xl border border-border/50 px-4 py-3"><p className="text-sm font-semibold">{item.label}</p><p className="mt-1 text-sm leading-6 text-muted-foreground">{item.detail}</p></div>)}</div><details className="mt-4 rounded-xl border border-border/50 px-4 py-3"><summary className="cursor-pointer text-sm font-semibold text-primary">{locale === "zh" ? "查看全部可能时柱" : "View every possible hour pillar"}</summary><div className="mt-3"><HourCandidates candidates={chart.birth_profile.hour_candidates} locale={locale} /></div></details></section>
  </section>
}

function BaziIdentitySummary({ chart, locale, subjectName, calculationRule, currentCycleText, generatedAt, trustNote }: { chart: MetaphysicsChart; locale: Locale; subjectName: string; calculationRule: string; currentCycleText: string; generatedAt: string; trustNote: string }) {
  return (
    <section className="border-b border-border/60 pb-6" aria-label={locale === "zh" ? "命盘身份摘要" : "Chart identity summary"}>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="kicker">State of I Ching · 易经决策</p><h3 className="mt-3 text-3xl font-semibold">{subjectName || (locale === "zh" ? "我的八字命盘" : "My BaZi chart")}</h3><p className="mt-2 text-sm text-muted-foreground">{chart.lunar_date}</p></div>
        <div className="text-right"><p className="text-xs text-muted-foreground">{locale === "zh" ? "日主" : "Day master"}</p><p className="mt-1 text-4xl font-semibold text-primary">{chart.day_master}</p></div>
      </header>
      <div className="mt-6 grid gap-x-8 gap-y-5 sm:grid-cols-2">
        <ShareFact label={locale === "zh" ? "出生地点" : "Birth place"} value={chart.birth_profile.birth_place || "—"} />
        <ShareFact label={locale === "zh" ? "出生时间" : "Birth time"} value={`${chart.birth_profile.input_date} · ${chart.timezone}`} />
        <ShareFact label={locale === "zh" ? "排盘规则" : "Calculation rule"} value={calculationRule} />
        <ShareFact label={locale === "zh" ? "当前大运" : "Current Da Yun"} value={currentCycleText} />
      </div>
      <footer className="mt-6 text-xs leading-5 text-muted-foreground"><p className="flex flex-wrap items-center gap-2"><span>{locale === "zh" ? "生成于" : "Generated"}: {formatChartTimestamp(generatedAt, locale, chart.timezone)}</span><span className="rounded-full bg-emerald-500/10 px-2 py-0.5 font-semibold text-emerald-700 dark:text-emerald-300">{chart.calculation_quality?.label ?? (locale === "zh" ? "已校准" : "Calibrated")}</span>{chart.boundary_flags?.near_solar_term ? <span className="rounded-full bg-amber-500/10 px-2 py-0.5 font-semibold text-amber-700 dark:text-amber-300">{locale === "zh" ? "时间接近换柱边界" : "Near a pillar boundary"}</span> : null}</p><p className="mt-1">{trustNote}</p></footer>
    </section>
  )
}

function BaziSynthesisPanel({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const evidence = new Map(
    (chart.theme_profiles ?? []).flatMap((profile) => profile.evidence).map((item) => [item.id, item]),
  )
  const conclusions = chart.synthesis?.conclusions ?? []
  if (!conclusions.length) return <p className="text-sm text-muted-foreground">{locale === "zh" ? "按新版重新排盘后显示核心判断。" : "Recalculate with the current version to see key findings."}</p>
  return <div className="grid gap-4 lg:grid-cols-2">{conclusions.map((item, index) => {
    const supporting = item.supporting_evidence_ids.map((id) => evidence.get(id)).filter(Boolean)
    const constraints = item.counter_evidence_ids.map((id) => evidence.get(id)).filter(Boolean)
    return <article key={item.id} className={`rounded-2xl border p-5 ${index === 0 ? "border-primary/35 bg-primary/[0.045] lg:col-span-2" : "border-border/55 bg-surface"}`}>
      <p className="text-xs font-semibold text-primary">{locale === "zh" ? item.theme : ({ 事业: "Career", 财富: "Wealth", 感情: "Relationship", 五行与承压结构: "Elements & pressure", 整体: "Overall" } as Record<string, string>)[item.theme] ?? item.theme}</p>
      <h3 className="mt-2 text-xl font-semibold leading-8">{item.headline}</h3>
      <p className="mt-2 text-sm leading-7 text-muted-foreground">{item.body}</p>
      {item.distribution_context ? <p className="mt-3 w-fit rounded-full bg-primary/8 px-3 py-1 text-xs font-semibold text-primary">{item.distribution_context}</p> : null}
      <details className="mt-4 border-t border-border/45 pt-3"><summary className="cursor-pointer text-sm font-semibold text-primary">{locale === "zh" ? "为什么这样判断" : "Why this finding"}</summary><div className="mt-3 space-y-3">{supporting.map((entry) => entry ? <div key={entry.id}><p className="text-sm font-medium">{entry.title}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{entry.detail}</p></div> : null)}{constraints.length ? <div className="rounded-xl bg-muted/35 px-3 py-2"><p className="text-xs font-semibold">{locale === "zh" ? "同时需要留意" : "Also consider"}</p>{constraints.map((entry) => entry ? <p key={entry.id} className="mt-1 text-xs leading-5 text-muted-foreground">{entry.title}：{entry.detail}</p> : null)}</div> : null}</div></details>
    </article>
  })}</div>
}

function CurrentBaziView({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const facts = chart.calendar_facts
  return (
    <section className="space-y-6" aria-label={locale === "zh" ? "当前时令结果" : "Current calendar result"}>
      <header className="border-b border-border/60 pb-5"><p className="kicker">{chart.lunar_date}</p><p className="mt-2 text-xs text-muted-foreground">{formatChartTimestamp(facts.gregorian, locale, chart.timezone)} · {chart.timezone}</p></header>
      <div className="overflow-hidden rounded-xl border border-border/50 bg-surface-elevated/35">
        <div className="grid grid-cols-4 border-b border-border/40 bg-primary/[0.05]">
          {chart.pillars.map((pillar) => <div key={pillar.label} className="border-l border-border/30 px-2 py-2.5 text-center text-xs font-semibold first:border-l-0">{pillar.label}{locale === "zh" ? "柱" : ""}</div>)}
        </div>
        <div className="grid grid-cols-4">
          {chart.pillars.map((pillar) => <div key={pillar.label} className="border-l border-border/30 px-2 py-4 text-center first:border-l-0"><p data-element={pillar.stem_element} className="chart-element-text text-3xl font-semibold leading-none">{pillar.stem}</p><p data-element={pillar.branch_element} className="chart-element-text mt-2 text-3xl font-semibold leading-none">{pillar.branch}</p></div>)}
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><RawFact label={locale === "zh" ? "月建" : "Month command"} value={facts.month_command} /><RawFact label={locale === "zh" ? "日辰" : "Day branch"} value={`${facts.day_pillar} · ${facts.day_branch}`} /><RawFact label={locale === "zh" ? "旬空" : "Void branches"} value={chart.xunkong} /><RawFact label={locale === "zh" ? "六神起点" : "Six-spirit start"} value={facts.six_spirit_start} /></div>
      <div className="border-t border-border/60 pt-5"><h3 className="text-sm font-semibold">{locale === "zh" ? "下一节气" : "Next solar term"}</h3><p className="mt-2 text-sm">{chart.previous_solar_term?.name || "—"} → {chart.next_solar_term?.name || "—"}</p>{chart.next_solar_term ? <LiveSolarTermCountdown key={chart.next_solar_term.timestamp} term={chart.next_solar_term} locale={locale} /> : null}</div>
    </section>
  )
}

function ReportChapter({ id, title, intro, children }: { id?: string; title: string; intro?: string; children: React.ReactNode }) {
  return <section id={id} className="chart-report-chapter scroll-mt-28 border-t border-border/60 pt-6"><h2 className="text-xl font-semibold">{title}</h2>{intro ? <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{intro}</p> : null}<div className="mt-5">{children}</div></section>
}

function DisplayModeControl({ mode, locale, onChange }: { mode: DisplayMode; locale: Locale; onChange: (mode: DisplayMode) => void }) {
  const options: Array<{ value: DisplayMode; zh: string; en: string }> = [
    { value: "simple", zh: "简明", en: "Simple" },
    { value: "study", zh: "研习", en: "Study" },
    { value: "professional", zh: "专业", en: "Professional" },
  ]
  return <div data-export-exclude className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/55 bg-surface px-4 py-3"><div><p className="text-sm font-semibold">{locale === "zh" ? "查看深度" : "Detail level"}</p><p className="mt-0.5 text-xs text-muted-foreground">{locale === "zh" ? "先看结论，需要时再进入统计与规则。" : "Start with findings, then open statistics and rules when needed."}</p></div><div className="inline-flex rounded-xl bg-muted/60 p-1" role="group" aria-label={locale === "zh" ? "命盘查看深度" : "Chart detail level"}>{options.map((option) => <button key={option.value} type="button" aria-pressed={mode === option.value} onClick={() => onChange(option.value)} className={`min-w-16 rounded-lg px-3 py-2 text-sm font-semibold transition ${mode === option.value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{locale === "zh" ? option.zh : option.en}</button>)}</div></div>
}

function ChartSectionNav({ locale, mode }: { locale: Locale; mode: DisplayMode }) {
  const coreItems = locale === "zh" ? [["#bazi-chart", "命盘"], ["#bazi-synthesis", "解读"], ["#bazi-periods", "运限"]] : [["#bazi-chart", "Chart"], ["#bazi-synthesis", "Reading"], ["#bazi-periods", "Periods"]]
  const studyItems = locale === "zh" ? [["#bazi-statistics", "统计"], ["#bazi-shensha", "神煞"]] : [["#bazi-statistics", "Statistics"], ["#bazi-shensha", "Shen Sha"]]
  const items = mode === "simple" ? coreItems : [...coreItems, ...studyItems]
  return <nav aria-label={locale === "zh" ? "八字命盘章节" : "BaZi chart sections"} className="sticky top-20 z-20 -mx-2 flex gap-1 overflow-x-auto rounded-2xl border border-border/60 bg-background/90 p-1.5 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-background/75"><span className="sr-only">{locale === "zh" ? "跳转到" : "Jump to"}</span>{items.map(([href, label]) => <a key={href} href={href} className="min-w-20 flex-1 whitespace-nowrap rounded-xl px-4 py-2.5 text-center text-sm font-semibold text-muted-foreground transition hover:bg-primary/8 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{label}</a>)}</nav>
}

function BaziProfessionalTable({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const rows = [
    { label: locale === "zh" ? "干神" : "Stem relation", values: chart.pillars.map((pillar) => pillar.ten_god) },
    { label: locale === "zh" ? "天干" : "Stem", values: chart.pillars.map((pillar) => pillar.stem), elements: chart.pillars.map((pillar) => pillar.stem_element), prominent: true },
    { label: locale === "zh" ? "地支" : "Branch", values: chart.pillars.map((pillar) => pillar.branch), elements: chart.pillars.map((pillar) => pillar.branch_element), prominent: true },
    { label: locale === "zh" ? "藏干" : "Hidden stems", values: chart.pillars.map((pillar) => pillar.hidden_stems.map((item) => `${item.stem}·${item.element}`).join(" / ") || "—") },
    { label: locale === "zh" ? "支神" : "Hidden relations", values: chart.pillars.map((pillar) => pillar.hidden_stems.map((item) => item.ten_god).join(" / ") || "—") },
    { label: locale === "zh" ? "纳音" : "Na Yin", values: chart.pillars.map((pillar) => pillar.nayin) },
    { label: locale === "zh" ? "空亡" : "Void", values: chart.pillars.map((pillar) => pillar.xunkong ?? "—") },
    { label: locale === "zh" ? "地势" : "Life stage", values: chart.pillars.map((pillar) => pillar.di_shi ?? "—") },
    { label: locale === "zh" ? "自坐" : "Self seat", values: chart.pillars.map((pillar) => pillar.self_seat ?? "—") },
    { label: locale === "zh" ? "神煞" : "Shen Sha", values: chart.pillars.map((pillar) => chart.shen_sha.filter((hit) => hit.pillar_labels.includes(pillar.label)).map((hit) => `${hit.name}${hit.state ? `·${hit.state}` : ""}`).join(" / ") || "—") },
  ]
  const status = Object.entries(chart.element_season_status ?? {})
  return (
    <div className="overflow-x-auto rounded-xl border border-border/50 bg-surface-elevated/35 custom-scrollbar">
      <div className="min-w-[22rem] md:min-w-[48rem]">
        <div className="grid grid-cols-[3.75rem_repeat(4,minmax(4.6rem,1fr))] border-b border-border/50 bg-primary/[0.06] md:grid-cols-[7rem_repeat(4,minmax(0,1fr))]">
          <div className="px-2 py-3 text-xs font-semibold text-muted-foreground">{locale === "zh" ? "四柱" : "Pillars"}</div>
          {chart.pillars.map((pillar) => <div key={pillar.label} className="border-l border-border/35 px-2 py-3 text-center text-sm font-semibold">{pillar.label}{locale === "zh" ? "柱" : ""}</div>)}
        </div>
        {rows.map((row, rowIndex) => (
          <div key={row.label} className={`grid grid-cols-[3.75rem_repeat(4,minmax(4.6rem,1fr))] border-b border-border/30 last:border-b-0 md:grid-cols-[7rem_repeat(4,minmax(0,1fr))] ${rowIndex % 2 ? "bg-background/50" : ""}`}>
            <div className="sticky left-0 z-10 flex items-center border-r border-border/30 bg-background px-2 py-3 text-xs font-medium text-muted-foreground md:px-3">{row.label}</div>
            {row.values.map((value, index) => (
              <div key={`${row.label}-${chart.pillars[index].label}`} data-element={row.elements?.[index]} className="flex min-h-12 items-center justify-center border-l border-border/30 px-1.5 py-2 text-center text-xs leading-5 md:px-3 md:text-sm">
                <span className={row.prominent ? "chart-element-text text-3xl font-semibold leading-none md:text-4xl" : "break-words"}>{value}</span>
              </div>
            ))}
          </div>
        ))}
        <div className="space-y-3 border-t border-border/50 bg-primary/[0.035] px-3 py-4 text-sm leading-6 md:px-5">
          <p><strong>{locale === "zh" ? "天干关系" : "Stem relations"}：</strong>{(chart.stem_relations ?? []).join(" / ") || "—"}</p>
          <p><strong>{locale === "zh" ? "地支关系" : "Branch relations"}：</strong>{(chart.branch_relations ?? []).join(" / ") || "—"}</p>
          <div className="flex flex-wrap gap-x-5 gap-y-2" aria-label={locale === "zh" ? "五行旺相休囚死" : "Seasonal element states"}>
            {status.map(([element, value]) => <span key={element} data-element={element} className="chart-element-text font-semibold">{element}{value}</span>)}
          </div>
        </div>
      </div>
    </div>
  )
}

function BaziPeriodNavigator({ cycles, locale, currentYear, selectedCycleIndex, selectedYear, selectedMonthIndex, loadingCycleIndex, error, onCycleChange, onYearChange, onMonthChange }: {
  cycles: DayunCycle[]
  locale: Locale
  currentYear: number
  selectedCycleIndex: number
  selectedYear: number
  selectedMonthIndex: number
  loadingCycleIndex: number | null
  error: string | null
  onCycleChange: (cycle: DayunCycle) => void
  onYearChange: (year: PeriodYear) => void
  onMonthChange: (month: PeriodMonth) => void
}) {
  const selectedCycle = cycles.find((cycle) => cycle.index === selectedCycleIndex) ?? cycles[0]
  const year = selectedCycle?.years.find((item) => item.year === selectedYear) ?? selectedCycle?.years[0]
  const month = year?.months.find((item) => item.index === selectedMonthIndex) ?? year?.months[0]
  if (!selectedCycle) return <p className="text-sm text-muted-foreground">{locale === "zh" ? "需要准确出生时辰和性别后才可计算运限。" : "An exact birth hour and gender are required for period calculations."}</p>
  return (
    <div className="space-y-6">
      <PeriodRail label={locale === "zh" ? "大运" : "Da Yun"}>
        {cycles.map((cycle) => <PeriodButton key={cycle.index} selected={cycle.index === selectedCycle.index} current={cycle.is_current ?? (cycle.start_year <= currentYear && currentYear <= cycle.end_year)} onClick={() => onCycleChange(cycle)} title={cycle.ganzhi || cycle.label} meta={`${cycle.start_age}–${cycle.end_age}${locale === "zh" ? "岁" : "y"}`} footer={loadingCycleIndex === cycle.index ? (locale === "zh" ? "载入中…" : "Loading…") : `${cycle.start_year}–${cycle.end_year}`} />)}
      </PeriodRail>
      {loadingCycleIndex === selectedCycle.index ? <p role="status" className="rounded-xl bg-primary/[0.055] px-4 py-3 text-sm text-primary">{locale === "zh" ? "正在展开这一段大运、流年与流月…" : "Loading this Da Yun, its years, and months…"}</p> : null}
      {error ? <p role="alert" className="rounded-xl bg-destructive/8 px-4 py-3 text-sm text-destructive">{error}</p> : null}
      <PeriodRail label={locale === "zh" ? "流年" : "Year"}>
        {selectedCycle.years.map((item) => <PeriodButton key={item.year} selected={item.year === year?.year} current={item.is_current ?? item.year === currentYear} onClick={() => onYearChange(item)} title={item.ganzhi} meta={`${item.year}`} footer={`${item.age}${locale === "zh" ? "岁" : "y"} · ${item.ten_god}`} />)}
      </PeriodRail>
      {year ? <PeriodRail label={locale === "zh" ? "流月" : "Month"}>
        {year.months.map((item) => <PeriodButton key={item.index} selected={item.index === month?.index} current={item.is_current} onClick={() => onMonthChange(item)} title={item.ganzhi} meta={item.label} footer={item.ten_god} />)}
      </PeriodRail> : null}
      <div className="grid gap-3 rounded-2xl bg-primary/[0.055] p-4 sm:grid-cols-3">
        <PeriodSummary label={locale === "zh" ? "所选大运" : "Selected Da Yun"} value={`${selectedCycle.ganzhi || selectedCycle.label} · ${selectedCycle.ten_god || "—"}`} detail={`${selectedCycle.start_year}–${selectedCycle.end_year}`} />
        <PeriodSummary label={locale === "zh" ? "所选流年" : "Selected year"} value={year ? `${year.ganzhi} · ${year.ten_god}` : "—"} detail={year ? `${year.year} · ${locale === "zh" ? "旬空" : "Void"} ${year.xunkong}` : "—"} />
        <PeriodSummary label={locale === "zh" ? "所选流月" : "Selected month"} value={month ? `${month.ganzhi} · ${month.ten_god}` : "—"} detail={month ? `${locale === "zh" ? "旬空" : "Void"} ${month.xunkong}` : "—"} />
      </div>
    </div>
  )
}

function PeriodRail({ label, children }: { label: string; children: React.ReactNode }) {
  return <div><div className="mb-2 flex items-center gap-2"><h3 className="text-sm font-semibold">{label}</h3><ChevronRight aria-hidden="true" className="size-3.5 text-muted-foreground" /></div><div className="overflow-x-auto pb-2 custom-scrollbar"><div className="flex min-w-max gap-2">{children}</div></div></div>
}

function PeriodButton({ selected, current, onClick, title, meta, footer }: { selected: boolean; current?: boolean; onClick: () => void; title: string; meta: string; footer: string }) {
  return <button type="button" aria-pressed={selected} onClick={onClick} className={`w-28 shrink-0 rounded-xl border px-3 py-2.5 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selected ? "border-primary bg-primary/10 shadow-sm" : "border-border/55 bg-surface hover:border-primary/45"}`}><span className="flex items-center justify-between gap-1 text-[0.68rem] text-muted-foreground"><span>{meta}</span>{current ? <span className="rounded-full bg-primary/12 px-1.5 py-0.5 font-semibold text-primary">今</span> : null}</span><strong className="mt-1 block text-lg">{title}</strong><span className="mt-1 block text-xs text-muted-foreground">{footer}</span></button>
}

function PeriodSummary({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div><p className="text-xs font-semibold text-muted-foreground">{label}</p><p className="mt-1 font-semibold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div>
}

function ShenShaPanel({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const [showExtended, setShowExtended] = useState(false)
  const metrics = new Map(chart.statistics.rarity_metrics.map((metric) => [metric.feature_id, metric]))
  const visible = chart.shen_sha.filter((hit) => showExtended || hit.level === "core")
  const categories = ["助力", "才学", "情缘", "执行", "迁动", "考验"]
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">{locale === "zh" ? `核心命中 ${chart.shen_sha.filter((hit) => hit.level === "core").length} 项 · 扩展命中 ${chart.shen_sha.filter((hit) => hit.level === "extended").length} 项` : `${chart.shen_sha.filter((hit) => hit.level === "core").length} core · ${chart.shen_sha.filter((hit) => hit.level === "extended").length} extended hits`}</p>
        <button type="button" aria-pressed={showExtended} onClick={() => setShowExtended((value) => !value)} className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold transition hover:border-primary/50 hover:text-primary">{showExtended ? (locale === "zh" ? "隐藏扩展规则" : "Hide extended") : (locale === "zh" ? "显示扩展规则" : "Show extended")}</button>
      </div>
      {categories.map((category) => {
        const hits = visible.filter((hit) => hit.category === category)
        if (!hits.length) return null
        return <section key={category}><h3 className="text-sm font-semibold">{category}</h3><div className="mt-2 grid gap-2 lg:grid-cols-2">{hits.map((hit) => <ShenShaRow key={hit.rule_id} hit={hit} metric={metrics.get(hit.feature_id)} locale={locale} />)}</div></section>
      })}
      <p className="text-xs leading-5 text-muted-foreground">{chart.statistics.disclaimer}</p>
    </div>
  )
}

function ShenShaRow({ hit, metric, locale }: { hit: ShenShaHit; metric?: RarityMetric; locale: Locale }) {
  const rarityLabels = locale === "zh" ? { common: "常见", less_common: "较少", rare: "稀有", very_rare: "罕见" } : { common: "Common", less_common: "Less common", rare: "Rare", very_rare: "Very rare" }
  const frequency = !metric || metric.status === "unsupported"
    ? (locale === "zh" ? "暂无基线数据" : "No baseline data")
    : metric.status === "zero"
      ? (locale === "zh" ? "0% · 本参考周期未出现" : "0% · not observed in this reference")
      : `${metric.display_percentage} · ${rarityLabels[metric.level as keyof typeof rarityLabels]}`
  return <details className="group rounded-xl border border-border/50 bg-surface px-4 py-3 open:border-primary/35 open:bg-primary/[0.035]"><summary className="cursor-pointer list-none"><span className="flex items-center justify-between gap-4"><span><strong>{hit.name}</strong>{hit.state ? <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary">{hit.state}</span> : null}<span className="ml-2 text-xs text-muted-foreground">{hit.pillar_labels.join("、")}{locale === "zh" ? "柱" : " pillar"}</span></span><span className="text-right text-xs font-semibold text-primary">{frequency}</span></span></summary><div className="mt-3 space-y-2 border-t border-border/45 pt-3 text-xs leading-5 text-muted-foreground">{hit.state_reason ? <p className="font-medium text-foreground">{hit.state_reason}</p> : null}<p>{hit.trigger}</p><p><strong className="text-foreground">{locale === "zh" ? "来源" : "Source"}：</strong>{hit.source.title} · {hit.source.note}</p>{hit.school_note ? <p><strong className="text-foreground">{locale === "zh" ? "口径备注" : "Convention note"}：</strong>{hit.school_note}</p> : null}{metric && metric.status !== "unsupported" ? <p>{locale === "zh" ? "分母" : "Denominator"}：{metric.total_weight.toLocaleString()} {locale === "zh" ? "历法分钟权重" : "calendar-minute weight"}</p> : null}{hit.formula_digest ? <p className="font-mono text-[0.68rem]">{hit.formula_digest}</p> : null}</div></details>
}

function ThemeProfilePanel({ profiles, baselineLabel, locale }: { profiles: ThemeProfile[]; baselineLabel: string; locale: Locale }) {
  const english: Record<string, string> = { 事业: "Career", 财富: "Wealth", 感情: "Relationship", 五行与承压结构: "Elements & pressure" }
  if (!profiles.length) return <p className="text-sm text-muted-foreground">{locale === "zh" ? "旧版命盘尚无四主题结构数据；按新版重新排盘后可查看。" : "This legacy chart has no four-theme structure data. Recalculate with the current version."}</p>
  return <section aria-labelledby="theme-profile-title"><div className="flex flex-wrap items-end justify-between gap-3"><div><h3 id="theme-profile-title" className="text-xl font-semibold">{locale === "zh" ? "哪些结构更有辨识度" : "Which structures are more distinctive"}</h3><p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{locale === "zh" ? "直接对照每项结构在历法样本中的位置，看清哪些更常见、哪些最能形成你的个人辨识度。" : "Compare each structure with the calendar sample space to see what is common and what most strongly distinguishes your chart."}</p></div><p className="text-xs text-muted-foreground">{baselineLabel}</p></div><div className="mt-5 grid gap-4 lg:grid-cols-2">{profiles.map((profile) => <ThemeProfileCard key={profile.theme} profile={profile} label={locale === "zh" ? profile.theme : english[profile.theme]} locale={locale} />)}</div></section>
}

function ThemeProfileCard({ profile, label, locale }: { profile: ThemeProfile; label: string; locale: Locale }) {
  const comparisons = profile.comparisons ?? []
  const families = profile.active_families ?? Array.from(new Set(profile.evidence.map((item) => item.family)))
  return <section className="rounded-2xl border border-border/55 bg-surface px-5 py-5"><div className="flex items-start justify-between gap-5"><div><h4 className="text-xl font-semibold">{label}</h4><p className="mt-2 text-sm text-muted-foreground">{comparisons.length ? (locale === "zh" ? `${comparisons.length} 项结构对照` : `${comparisons.length} structure comparisons`) : (locale === "zh" ? "重新排盘后显示分布" : "Recalculate to see distributions")}</p></div><div className="flex flex-wrap justify-end gap-1.5">{families.slice(0, 3).map((family) => <span key={family} className="rounded-full bg-primary/8 px-2.5 py-1 text-xs font-medium text-primary">{family}</span>)}</div></div><div className="mt-5 space-y-5">{comparisons.map((item) => <MetricComparisonView key={item.metric_id} item={item} locale={locale} />)}</div><details className="mt-5 border-t border-border/45 pt-4"><summary className="cursor-pointer text-sm font-semibold text-primary">{locale === "zh" ? `查看 ${profile.evidence.length} 条结构依据` : `View ${profile.evidence.length} evidence items`}</summary><div className="mt-4 space-y-4">{profile.evidence.map((item) => <div key={item.id} className="grid gap-2 sm:grid-cols-[5rem_1fr]"><span className="w-fit rounded-full bg-primary/8 px-2.5 py-1 text-xs font-semibold text-primary">{item.evidence_type}</span><div><p className="text-base font-medium">{item.title}</p><p className="mt-1 text-sm leading-6 text-muted-foreground">{item.detail}</p><p className="mt-1 text-xs text-muted-foreground">{item.source}</p></div></div>)}</div></details></section>
}

function MetricComparisonView({ item, locale }: { item: ThemeComparison; locale: Locale }) {
  if (item.status === "unsupported") return <div><p className="text-sm font-semibold">{item.label}</p><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "暂无可比基线" : "No comparable baseline yet"}</p></div>
  if (item.comparison_mode === "incidence") {
    const hit = item.hit_percentage ?? 0
    const incidenceLabel = locale === "zh" ? (item.display_label ?? `出现率 ${hit.toFixed(1)}%`) : `${hit.toFixed(1)}% incidence`
    return <div><div className="flex items-end justify-between gap-3"><p className="text-sm font-semibold">{item.label} <strong className="ml-1 text-xl text-primary">{item.value ? (locale === "zh" ? "命中" : "Present") : (locale === "zh" ? "未命中" : "Absent")}</strong></p><p className="text-xs font-semibold text-primary">{incidenceLabel}</p></div><div className="mt-2 h-3 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary/75" style={{ width: `${hit}%` }} /></div></div>
  }
  const lower = item.lower_percentage ?? 0
  const same = item.same_percentage ?? 0
  const higher = item.higher_percentage ?? 0
  const max = Math.max(1, ...(item.histogram ?? []).map((entry) => entry.percentage))
  const englishDisplay = item.display_mode === "exact_tail"
    ? item.display_direction === "high"
      ? `Distinct high-side structure · upper tail ${item.tail_percentage?.toFixed(1) ?? "—"}%`
      : `Distinct low-side structure · lower tail ${item.tail_percentage?.toFixed(1) ?? "—"}%`
    : item.display_mode === "directional"
      ? item.display_direction === "high" ? "Relatively pronounced" : "Relatively restrained"
      : item.display_mode === "reference_zero"
        ? "Not observed in this reference"
        : "Common range"
  const displayLabel = locale === "zh" ? (item.display_label ?? item.semantic_pole ?? "常见区间") : englishDisplay
  return <div><div className="flex flex-wrap items-end justify-between gap-3"><p className="text-sm font-semibold">{item.label} <strong className="ml-1 text-xl text-primary">{item.value}</strong></p><p className="rounded-full bg-primary/8 px-2.5 py-1 text-xs font-semibold text-primary">{displayLabel}</p></div><details className="mt-3 border-t border-border/45 pt-3"><summary className="cursor-pointer text-xs font-semibold text-muted-foreground hover:text-foreground">{locale === "zh" ? "查看完整历法分布" : "View full calendar distribution"}</summary>{item.histogram?.length ? <div className="mt-3 flex h-16 items-end gap-1" role="img" aria-label={locale === "zh" ? `${item.label}离散分布` : `${item.label} discrete distribution`}>{item.histogram.map((entry) => <div key={String(entry.value)} className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1"><span className="text-[0.6rem] tabular-nums text-muted-foreground">{entry.percentage >= 5 ? `${entry.percentage.toFixed(0)}%` : ""}</span><span className={`w-full rounded-t-sm ${String(entry.value) === String(item.value) ? "bg-primary" : "bg-primary/20"}`} style={{ height: `${Math.max(4, entry.percentage / max * 38)}px` }} /><span className="text-[0.6rem] tabular-nums text-muted-foreground">{entry.value}</span></div>)}</div> : <div className="mt-3 flex h-3 overflow-hidden rounded-full bg-muted"><span className="bg-muted-foreground/25" style={{ width: `${lower}%` }} /><span className="bg-primary/80" style={{ width: `${same}%` }} /><span className="bg-primary/25" style={{ width: `${higher}%` }} /></div>}<div className="mt-2 grid grid-cols-3 text-[0.68rem] text-muted-foreground"><span>{locale === "zh" ? "低于" : "Lower"} {lower.toFixed(1)}%</span><span className="text-center">{locale === "zh" ? "相同" : "Same"} {same.toFixed(1)}%</span><span className="text-right">{locale === "zh" ? "高于" : "Higher"} {higher.toFixed(1)}%</span></div></details></div>
}

function BaziStatistics({ chart, locale, currentYear }: { chart: MetaphysicsChart; locale: Locale; currentYear: number }) {
  const elements = ["木", "火", "土", "金", "水"]
  const layers = chart.structure?.layered_distribution
  const visibleElements = layers?.elements.visible_stems ?? chart.element_counts
  const mainQiElements = layers?.elements.branch_main_qi ?? Object.fromEntries(elements.map((element) => [element, 0]))
  const hiddenElements = layers?.elements.hidden_stems ?? Object.fromEntries(elements.map((element) => [element, 0]))
  const visibleGods = new Map(Object.entries(layers?.ten_gods.visible_stems ?? {}))
  const hiddenGods = new Map(Object.entries(layers?.ten_gods.hidden_stems ?? {}))
  const yangStems = new Set(["甲", "丙", "戊", "庚", "壬"])
  const yinStems = new Set(["乙", "丁", "己", "辛", "癸"])
  const yangBranches = new Set(["子", "寅", "辰", "午", "申", "戌"])
  const yinBranches = new Set(["丑", "卯", "巳", "未", "酉", "亥"])
  const visibleCharacters = chart.pillars.flatMap((pillar) => [pillar.stem, pillar.branch])
  const yangCount = visibleCharacters.filter((value, index) => index % 2 === 0 ? yangStems.has(value) : yangBranches.has(value)).length
  const yinCount = visibleCharacters.filter((value, index) => index % 2 === 0 ? yinStems.has(value) : yinBranches.has(value)).length
  const unknownCount = 8 - yangCount - yinCount
  const currentCycle = chart.birth_profile.dayun.cycles.find((cycle) => cycle.is_current)
    ?? chart.birth_profile.dayun.cycles.find((cycle) => cycle.start_year <= currentYear && currentYear <= cycle.end_year)
  const relationshipGroups = [
    { key: "合", label: locale === "zh" ? "合" : "Combine" },
    { key: "会", label: locale === "zh" ? "会" : "Meeting" },
    { key: "冲", label: locale === "zh" ? "冲" : "Clash" },
    { key: "克", label: locale === "zh" ? "克" : "Control" },
    { key: "刑", label: locale === "zh" ? "刑" : "Punish" },
    { key: "害", label: locale === "zh" ? "害" : "Harm" },
    { key: "破", label: locale === "zh" ? "破" : "Break" },
  ]
  const allRelations = chart.structure?.structural_relations.map((item) => item.label) ?? [...chart.stem_relations, ...chart.branch_relations]
  const tenGodLabels = Array.from(new Set([...visibleGods.keys(), ...hiddenGods.keys()])).filter((item) => item !== "日主" && item !== "—").sort()
  const dayMasterRelations = chart.structure?.day_master_relations ?? []
  const relationLabels = ["同我", "生我", "我生", "我克", "克我"]
  const relationCounts = relationLabels.map((label) => ({ label, value: dayMasterRelations.filter((item) => item.day_master_relation === label).length }))
  const visibleGodTotal = Array.from(visibleGods.values()).reduce((sum, value) => sum + value, 0)
  const hiddenGodTotal = Array.from(hiddenGods.values()).reduce((sum, value) => sum + value, 0)
  const yinYangTotal = Math.max(1, yangCount + yinCount)
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <StatisticBlock title={locale === "zh" ? "五行分层" : "Five-element layers"} description={locale === "zh" ? "明干、地支主气与全部藏干分开计数，不混成能量分数。" : "Visible stems, branch main qi, and all hidden stems remain separate counts."}>
        <LayeredCountChart
          rows={elements.map((element) => ({ label: element, element, values: [visibleElements[element] ?? 0, mainQiElements[element] ?? 0, hiddenElements[element] ?? 0] }))}
          legends={locale === "zh" ? ["明干", "地支主气", "藏干"] : ["Visible", "Main qi", "Hidden"]}
        />
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "日主关系分布" : "Day-master relations"} description={locale === "zh" ? `分母 ${dayMasterRelations.length}：四柱明干、地支主气与藏干逐项标注。` : `Denominator ${dayMasterRelations.length}: visible stems, branch main qi, and hidden stems.`}>
        <HorizontalCountChart rows={relationCounts} denominator={Math.max(1, dayMasterRelations.length)} />
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "十神分层" : "Ten-God layers"} description={locale === "zh" ? `明干分母 ${visibleGodTotal} · 藏干分母 ${hiddenGodTotal}；两层不可直接相加为强弱。` : `Visible denominator ${visibleGodTotal}; hidden denominator ${hiddenGodTotal}. Layers are not a strength score.`}>
        <LayeredCountChart rows={tenGodLabels.map((label) => ({ label, values: [visibleGods.get(label) ?? 0, hiddenGods.get(label) ?? 0] }))} legends={locale === "zh" ? ["明干", "藏干"] : ["Visible", "Hidden"]} />
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "干支关系图" : "Stem-branch relations"} description={locale === "zh" ? `共识别 ${allRelations.length} 条结构关系；同一组干支可能同时命中不同规则。` : `${allRelations.length} recognized relationships; one pair may match multiple rules.`}>
        <HorizontalCountChart rows={relationshipGroups.map((group) => ({ label: group.label, value: allRelations.filter((item) => item.includes(group.key)).length }))} denominator={Math.max(1, allRelations.length)} />
        <details className="mt-4 border-t border-border/45 pt-3"><summary className="cursor-pointer text-sm font-semibold text-primary">{locale === "zh" ? "查看全部关系" : "View every relationship"}</summary><p className="mt-2 text-sm leading-6 text-muted-foreground">{allRelations.join(" / ") || "—"}</p></details>
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "阴阳明字" : "Visible Yin / Yang"} description={unknownCount ? (locale === "zh" ? `${unknownCount} 个待定明字未计入` : `${unknownCount} uncertain characters excluded`) : (locale === "zh" ? "只计算四柱八个明字。" : "Only the eight visible characters are counted.")}>
        <div className="mt-5 flex h-5 overflow-hidden rounded-full bg-muted" role="img" aria-label={`${locale === "zh" ? "阳" : "Yang"} ${yangCount}, ${locale === "zh" ? "阴" : "Yin"} ${yinCount}`}><span className="bg-primary" style={{ width: `${yangCount / yinYangTotal * 100}%` }} /><span className="bg-primary/35" style={{ width: `${yinCount / yinYangTotal * 100}%` }} /></div>
        <div className="mt-3 grid grid-cols-2 gap-3"><RawNumber label={locale === "zh" ? "阳" : "Yang"} value={yangCount} /><RawNumber label={locale === "zh" ? "阴" : "Yin"} value={yinCount} /></div>
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "当前大运定位" : "Current Da Yun"} description={locale === "zh" ? "按精确起运与交接时刻定位。" : "Located from the exact start and handoff instant."}>
        {currentCycle ? <div className="mt-5 flex items-end justify-between gap-4"><div><p className="text-4xl font-semibold text-primary">{currentCycle.ganzhi}</p><p className="mt-2 text-sm text-muted-foreground">{currentCycle.start_year}–{currentCycle.end_year}</p></div><div className="text-right"><p className="text-2xl font-semibold">{Math.max(0, currentCycle.end_year - currentYear)}</p><p className="text-xs text-muted-foreground">{locale === "zh" ? "距周期末（年）" : "years remaining"}</p></div></div> : <p className="mt-3 text-sm text-muted-foreground">—</p>}
      </StatisticBlock>
    </div>
  )
}

function StatisticBlock({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <section className="min-w-0 rounded-2xl border border-border/55 bg-surface px-5 py-5"><h3 className="text-lg font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>{children}</section>
}

function LayeredCountChart({ rows, legends }: { rows: Array<{ label: string; element?: string; values: number[] }>; legends: string[] }) {
  const max = Math.max(1, ...rows.flatMap((row) => row.values))
  const colors = ["bg-primary", "bg-amber-500/80", "bg-cyan-600/75"]
  return <div className="mt-5"><div className="mb-4 flex flex-wrap gap-4 text-xs text-muted-foreground">{legends.map((legend, index) => <span key={legend}><span className={`mr-1.5 inline-block size-2.5 rounded-sm ${colors[index]}`} />{legend}</span>)}</div><div className="space-y-3">{rows.map((row) => <div key={row.label} className="grid grid-cols-[3.5rem_1fr] items-center gap-3"><span data-element={row.element} className="chart-element-text text-sm font-semibold">{row.label}</span><div className="space-y-1.5">{row.values.map((value, index) => <div key={`${row.label}-${legends[index]}`} className="flex items-center gap-2"><div className="h-2.5 flex-1 rounded-full bg-muted"><div className={`h-full rounded-full ${colors[index]}`} style={{ width: `${value / max * 100}%` }} /></div><span className="w-5 text-right text-xs font-semibold tabular-nums">{value}</span></div>)}</div></div>)}</div></div>
}

function HorizontalCountChart({ rows, denominator }: { rows: Array<{ label: string; value: number }>; denominator: number }) {
  const max = Math.max(1, ...rows.map((row) => row.value))
  return <div className="mt-5 space-y-3">{rows.map((row) => <div key={row.label} className="grid grid-cols-[3.5rem_1fr_4rem] items-center gap-3"><span className="text-sm font-medium">{row.label}</span><div className="h-3 rounded-full bg-muted"><div className="h-full rounded-full bg-primary/75" style={{ width: `${row.value / max * 100}%` }} /></div><span className="text-right text-xs tabular-nums text-muted-foreground"><strong className="text-sm text-foreground">{row.value}</strong> / {denominator}</span></div>)}</div>
}

function RawNumber({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl bg-muted/35 px-4 py-3"><p className="text-3xl font-semibold">{value}</p><p className="mt-1 text-sm text-muted-foreground">{label}</p></div>
}

function HourCandidates({ candidates, locale }: { candidates: MetaphysicsChart["birth_profile"]["hour_candidates"]; locale: Locale }) {
  return <section><h3 className="text-sm font-semibold">{locale === "zh" ? "可能时柱" : "Possible hour pillars"}</h3><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "时辰未定，因此不输出伪精确大运；晚子时单列以保留换日差异。" : "Da Yun is withheld while the birth hour is unknown; late Zi remains separate."}</p><div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-7">{candidates.map((candidate) => <div key={candidate.label} className="border-t border-border/60 py-2 text-center"><p className="text-xs text-muted-foreground">{candidate.label}</p><p className="mt-1 font-semibold">{candidate.pillar}</p></div>)}</div></section>
}

function ShareFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value}</p></div>
}

function RawFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value}</p></div>
}

function formatTermDistance(totalSeconds: number, locale: Locale) {
  const seconds = Math.max(0, Math.floor(totalSeconds)); const days = Math.floor(seconds / 86400); const hours = Math.floor((seconds % 86400) / 3600); const minutes = Math.floor((seconds % 3600) / 60); const rest = seconds % 60
  return locale === "zh" ? `${days} 天 ${hours} 时 ${minutes} 分 ${rest} 秒` : `${days}d ${hours}h ${minutes}m ${rest}s`
}

function LiveSolarTermCountdown({ term, locale }: { term: SolarTerm; locale: Locale }) {
  const [remaining, setRemaining] = useState(() => Math.max(0, new Date(term.timestamp).getTime() - Date.now()))
  useEffect(() => { const timer = window.setInterval(() => setRemaining(Math.max(0, new Date(term.timestamp).getTime() - Date.now())), 1000); return () => window.clearInterval(timer) }, [term.timestamp])
  if (remaining <= 0) return <p role="status" className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "节气已到，正在刷新时令…" : "Solar term reached; refreshing…"}</p>
  return <p role="status" className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? `还有 ${formatTermDistance(remaining / 1000, locale)}` : `${formatTermDistance(remaining / 1000, locale)} remaining`}</p>
}

function HistoricalSolarTerm({ term, calculationTimestamp, locale, timeZone }: { term: SolarTerm; calculationTimestamp: string; locale: Locale; timeZone: string }) {
  const distance = formatTermDistance(term.seconds_away, locale)
  const exactTimestamp = formatChartTimestamp(term.timestamp, locale, timeZone)
  return <div className="mt-2 text-xs leading-5 text-muted-foreground"><p>{locale === "zh" ? `距排盘时刻 ${distance}（${term.days_away.toFixed(2)} 天）` : `${distance} after chart time (${term.days_away.toFixed(2)} days)`}</p><p>{locale === "zh" ? "排盘时刻" : "Chart time"}: <time dateTime={calculationTimestamp}>{formatChartTimestamp(calculationTimestamp, locale, timeZone)}</time></p><p>{locale === "zh" ? "节气准确时刻" : "Exact term time"}: <time dateTime={term.timestamp}>{exactTimestamp}</time></p></div>
}

function BaziExportCanvas({ exportTargetId, chart, locale, subjectName, calculationRule, currentCycleText, generatedAt, trustNote }: { exportTargetId: string; chart: MetaphysicsChart; locale: Locale; subjectName: string; calculationRule: string; currentCycleText: string; generatedAt: string; trustNote: string }) {
  const consumerProfile = chart.consumer?.twin ? { identity: chart.consumer.identity, subjects: chart.consumer.subjects, fingerprints: chart.consumer.fingerprints, twin: chart.consumer.twin } : null
  return (
    <div aria-hidden="true" className="chart-export-stage">
      <article id={exportTargetId} aria-hidden="true" data-chart-export-root className="chart-share-canvas chart-export-canvas">
        {consumerProfile ? <><ConsumerIdentity profile={consumerProfile} locale={locale} /><div className="mt-8"><MetaphysicsAchievements achievements={chart.consumer?.achievements ?? []} locale={locale} /></div></> : <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={generatedAt} trustNote={trustNote} />}
        <div className="mt-8"><ThemeProfilePanel profiles={chart.theme_profiles ?? chart.structure?.theme_profiles ?? []} baselineLabel={chart.statistics.baseline.label} locale={locale} /></div>
        <div className="mt-8"><BaziStatistics chart={chart} locale={locale} currentYear={currentYearInTimeZone(chart.timezone)} /></div>
        <div className="mt-8"><BaziProfessionalTable chart={chart} locale={locale} /></div>
      </article>
    </div>
  )
}
