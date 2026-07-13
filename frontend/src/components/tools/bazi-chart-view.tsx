"use client"

import { useEffect, useId, useRef, useState } from "react"
import { ChevronRight } from "lucide-react"
import { ChartExportButton } from "@/components/tools/chart-export-button"
import { ChartAssetExportButton } from "@/components/tools/chart-asset-export-button"
import { buildBaziMarkdown } from "@/lib/chart-markdown"
import type { DayunCycle, MetaphysicsChart, PeriodMonth, PeriodYear, RarityMetric, ShenShaHit } from "@/types/api"

type Locale = "en" | "zh"
type SolarTerm = NonNullable<MetaphysicsChart["next_solar_term"]>
type BaziChartViewProps =
  | { chart: MetaphysicsChart; locale: Locale; mode: "current"; generatedAt?: never }
  | { chart: MetaphysicsChart; locale: Locale; mode: "birth"; generatedAt: string; subjectName: string }

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
  const currentCycle = dayun.cycles.find(
    (cycle) => cycle.start_year <= currentYear && currentYear <= cycle.end_year,
  )
  const [selectedCycleIndex, setSelectedCycleIndex] = useState(() => currentCycle?.index ?? dayun.cycles[0]?.index ?? 0)
  const initialYear = dayun.current?.year?.year ?? currentYear
  const [selectedYear, setSelectedYear] = useState(initialYear)
  const [selectedMonthIndex, setSelectedMonthIndex] = useState(() => dayun.current?.month?.index ?? 0)
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
    ? "确定性历法事实；不自动判断旺衰、格局、喜用神、性格或命运结果。"
    : "Deterministic calendar facts; no strength, pattern, favorable-element, personality, or fate claim is inferred."
  const currentCycleText = currentCycle
    ? `${currentCycle.label} · ${currentCycle.start_year}–${currentCycle.end_year}`
    : (locale === "zh" ? "当前年份不在已列周期内" : "Current year is outside the listed cycles")
  const resultGeneratedAt = generatedAt

  return (
    <section className="chart-report space-y-8" aria-label={locale === "zh" ? "八字排盘结果" : "BaZi chart result"}>
      <div data-export-exclude className="flex justify-end">
        <ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出命盘" : "Export chart"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "命盘图片生成失败，请重试。" : "Chart image could not be generated. Try again."} safeBaseFilename={`bazi-${chart.birth_profile.input_date}`} copyLabel={locale === "zh" ? "复制 Markdown" : "Copy Markdown"} copySuccess={locale === "zh" ? "Markdown 已复制" : "Markdown copied"} copyError={locale === "zh" ? "复制失败，请改用下载。" : "Copy failed. Use the download instead."} />
      </div>

      <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={resultGeneratedAt} trustNote={trustNote} />

      <ChartSectionNav locale={locale} />

      <ReportChapter id="bazi-chart" title={locale === "zh" ? "命盘" : "Chart"} intro={locale === "zh" ? "四柱、十神、藏干与神煞按列对照；左侧字段固定，手机可横向滑动。" : "Compare pillars, Ten Gods, hidden stems, and Shen Sha by column. The field column stays visible on mobile."}>
        <div data-export-exclude className="mb-3 flex justify-end"><ChartAssetExportButton targetId={tableExportTargetId} label={locale === "zh" ? "单独导出四柱表" : "Export pillar table"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "四柱表导出失败。" : "Pillar table export failed."} safeBaseFilename={`bazi-pillars-${chart.birth_profile.input_date}`} /></div>
        <div id={tableExportTargetId}><BaziProfessionalTable chart={chart} locale={locale} /></div>
      </ReportChapter>

      <ReportChapter id="bazi-periods" title={locale === "zh" ? "运限" : "Periods"} intro={locale === "zh" ? "依次选择大运、流年和流月；每层显示干支、十神、旬空与该层新增命中。当前标记按公历年份定位，精确交接以所选起运规则为准。" : "Select a Da Yun, year, and month to inspect its stems, Ten God, void, and newly activated rules. The current marker uses the calendar year. Exact handoff follows the configured start rule."}>
        <BaziPeriodNavigator
          cycles={dayun.cycles}
          locale={locale}
          currentYear={currentYear}
          selectedCycleIndex={selectedCycleIndex}
          selectedYear={selectedYear}
          selectedMonthIndex={selectedMonthIndex}
          onCycleChange={(cycle) => { setSelectedCycleIndex(cycle.index); setSelectedYear(cycle.years.find((year) => year.year === currentYear)?.year ?? cycle.years[0]?.year ?? cycle.start_year); setSelectedMonthIndex(0) }}
          onYearChange={(year) => { setSelectedYear(year.year); setSelectedMonthIndex(0) }}
          onMonthChange={(month) => setSelectedMonthIndex(month.index)}
        />
      </ReportChapter>

      <ReportChapter id="bazi-shensha" title={locale === "zh" ? "神煞" : "Shen Sha"} intro={locale === "zh" ? "默认先看核心规则；每项可核对命中柱位、公式、样本频率与传统来源。" : "Core rules appear first. Every item exposes its pillar, trigger, calendar-sample frequency, and traditional source."}>
        <ShenShaPanel chart={chart} locale={locale} />
      </ReportChapter>

      <ReportChapter id="bazi-statistics" title={locale === "zh" ? "统计" : "Statistics"} intro={locale === "zh" ? "只展示透明计数与同规则基线百分位；不是命运分数，也不代表吉凶。" : "Transparent counts and within-rule-set percentiles only; these are not fate or luck scores."}>
        <div className="space-y-8">
          <RuleIndexPanel chart={chart} locale={locale} />
          <BaziStatistics chart={chart} locale={locale} currentYear={currentYear} />
        </div>
      </ReportChapter>

      <ReportChapter title={locale === "zh" ? "排盘规则与版本" : "Rules and versions"}>
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
      </ReportChapter>

      <BaziExportCanvas exportTargetId={exportTargetId} chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={resultGeneratedAt} trustNote={trustNote} />
    </section>
  )
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
      <footer className="mt-6 text-xs leading-5 text-muted-foreground"><p>{locale === "zh" ? "生成于" : "Generated"}: {formatChartTimestamp(generatedAt, locale, chart.timezone)}</p><p className="mt-1">{trustNote}</p></footer>
    </section>
  )
}

function CurrentBaziView({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const facts = chart.calendar_facts
  return (
    <section className="space-y-6" aria-label={locale === "zh" ? "当前时令结果" : "Current calendar result"}>
      <header className="border-b border-border/60 pb-5"><p className="kicker">{chart.lunar_date}</p><h2 className="mt-2 text-3xl font-semibold">{chart.bazi}</h2><p className="mt-1 text-xs text-muted-foreground">{formatChartTimestamp(facts.gregorian, locale, chart.timezone)} · {chart.timezone}</p></header>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><RawFact label={locale === "zh" ? "四柱" : "Four pillars"} value={chart.bazi} /><RawFact label={locale === "zh" ? "月建" : "Month command"} value={facts.month_command} /><RawFact label={locale === "zh" ? "日辰" : "Day branch"} value={`${facts.day_pillar} · ${facts.day_branch}`} /><RawFact label={locale === "zh" ? "旬空" : "Void branches"} value={chart.xunkong} /></div>
      <div className="border-t border-border/60 pt-5"><h3 className="text-sm font-semibold">{locale === "zh" ? "下一节气" : "Next solar term"}</h3><p className="mt-2 text-sm">{chart.previous_solar_term?.name || "—"} → {chart.next_solar_term?.name || "—"}</p>{chart.next_solar_term ? <LiveSolarTermCountdown key={chart.next_solar_term.timestamp} term={chart.next_solar_term} locale={locale} /> : null}</div>
    </section>
  )
}

function ReportChapter({ id, title, intro, children }: { id?: string; title: string; intro?: string; children: React.ReactNode }) {
  return <section id={id} className="chart-report-chapter scroll-mt-28 border-t border-border/60 pt-6"><h2 className="text-xl font-semibold">{title}</h2>{intro ? <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{intro}</p> : null}<div className="mt-5">{children}</div></section>
}

function ChartSectionNav({ locale }: { locale: Locale }) {
  const items = locale === "zh" ? [["#bazi-chart", "命盘"], ["#bazi-periods", "运限"], ["#bazi-shensha", "神煞"], ["#bazi-statistics", "统计"]] : [["#bazi-chart", "Chart"], ["#bazi-periods", "Periods"], ["#bazi-shensha", "Shen Sha"], ["#bazi-statistics", "Statistics"]]
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
    { label: locale === "zh" ? "神煞" : "Shen Sha", values: chart.pillars.map((pillar) => chart.shen_sha.filter((hit) => hit.pillar_labels.includes(pillar.label)).map((hit) => hit.name).join(" / ") || "—") },
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

function BaziPeriodNavigator({ cycles, locale, currentYear, selectedCycleIndex, selectedYear, selectedMonthIndex, onCycleChange, onYearChange, onMonthChange }: {
  cycles: DayunCycle[]
  locale: Locale
  currentYear: number
  selectedCycleIndex: number
  selectedYear: number
  selectedMonthIndex: number
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
        {cycles.map((cycle) => <PeriodButton key={cycle.index} selected={cycle.index === selectedCycle.index} current={cycle.start_year <= currentYear && currentYear <= cycle.end_year} onClick={() => onCycleChange(cycle)} title={cycle.ganzhi || cycle.label} meta={`${cycle.start_age}–${cycle.end_age}${locale === "zh" ? "岁" : "y"}`} footer={`${cycle.start_year}–${cycle.end_year}`} />)}
      </PeriodRail>
      <PeriodRail label={locale === "zh" ? "流年" : "Year"}>
        {selectedCycle.years.map((item) => <PeriodButton key={item.year} selected={item.year === year?.year} current={item.year === currentYear} onClick={() => onYearChange(item)} title={item.ganzhi} meta={`${item.year}`} footer={`${item.age}${locale === "zh" ? "岁" : "y"} · ${item.ten_god}`} />)}
      </PeriodRail>
      {year ? <PeriodRail label={locale === "zh" ? "流月" : "Month"}>
        {year.months.map((item) => <PeriodButton key={item.index} selected={item.index === month?.index} onClick={() => onMonthChange(item)} title={item.ganzhi} meta={item.label} footer={item.ten_god} />)}
      </PeriodRail> : null}
      <div className="grid gap-3 rounded-2xl bg-primary/[0.055] p-4 sm:grid-cols-3">
        <PeriodSummary label={locale === "zh" ? "所选大运" : "Selected Da Yun"} value={`${selectedCycle.ganzhi || selectedCycle.label} · ${selectedCycle.ten_god || "—"}`} detail={`${selectedCycle.start_year}–${selectedCycle.end_year}`} />
        <PeriodSummary label={locale === "zh" ? "所选流年" : "Selected year"} value={year ? `${year.ganzhi} · ${year.ten_god}` : "—"} detail={year ? `${year.year} · ${locale === "zh" ? "旬空" : "Void"} ${year.xunkong}` : "—"} />
        <PeriodSummary label={locale === "zh" ? "所选流月" : "Selected month"} value={month ? `${month.ganzhi} · ${month.ten_god}` : "—"} detail={month ? `${locale === "zh" ? "旬空" : "Void"} ${month.xunkong}` : "—"} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <PeriodActivations title={locale === "zh" ? "流年新增命中与关系" : "Year activations and relations"} values={[...(year?.shen_sha ?? []), ...(year?.relations ?? [])]} locale={locale} />
        <PeriodActivations title={locale === "zh" ? "流月新增命中与关系" : "Month activations and relations"} values={[...(month?.shen_sha ?? []), ...(month?.relations ?? [])]} locale={locale} />
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

function PeriodActivations({ title, values, locale }: { title: string; values: string[]; locale: Locale }) {
  return <section className="border-t border-border/55 pt-3"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-muted-foreground">{values.join(" · ") || (locale === "zh" ? "没有新增命中；这不等于无事发生。" : "No newly matched rule; this does not mean nothing happens.")}</p></section>
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
  return <details className="group rounded-xl border border-border/50 bg-surface px-4 py-3 open:border-primary/35 open:bg-primary/[0.035]"><summary className="cursor-pointer list-none"><span className="flex items-center justify-between gap-4"><span><strong>{hit.name}</strong><span className="ml-2 text-xs text-muted-foreground">{hit.pillar_labels.join("、")}{locale === "zh" ? "柱" : " pillar"}</span></span><span className="text-right text-xs"><strong className="text-primary">{metric?.display_percentage ?? "—"}</strong><span className="ml-1 text-muted-foreground">{metric ? rarityLabels[metric.level] : ""}</span></span></span></summary><div className="mt-3 space-y-2 border-t border-border/45 pt-3 text-xs leading-5 text-muted-foreground"><p>{hit.trigger}</p><p><strong className="text-foreground">{locale === "zh" ? "来源" : "Source"}：</strong>{hit.source.title} · {hit.source.note}</p>{hit.school_note ? <p><strong className="text-foreground">{locale === "zh" ? "流派备注" : "School note"}：</strong>{hit.school_note}</p> : null}<p>{locale === "zh" ? "分母" : "Denominator"}：{metric?.total_weight.toLocaleString() ?? "—"} {locale === "zh" ? "历法分钟权重" : "calendar-minute weight"}</p></div></details>
}

function RuleIndexPanel({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  return <section aria-labelledby="rule-index-title"><div className="flex flex-wrap items-end justify-between gap-2"><div><h3 id="rule-index-title" className="text-base font-semibold">{locale === "zh" ? "六项规则指数" : "Six rule indices"}</h3><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "同一规则集内的百分位；条形长度不是吉凶。" : "Percentiles within the same rule set; bar length is not luck."}</p></div><p className="text-xs text-muted-foreground">{chart.statistics.baseline.label}</p></div><div className="mt-4 grid gap-x-8 gap-y-4 md:grid-cols-2">{chart.statistics.rule_indices.map((item) => <div key={item.dimension}><div className="flex items-end justify-between gap-3 text-sm"><span className="font-semibold">{item.dimension}</span><span><strong>{item.percentile.toFixed(0)}</strong><span className="ml-1 text-xs text-muted-foreground">{locale === "zh" ? "百分位" : "percentile"}</span></span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-primary/10"><div className="h-full rounded-full bg-primary/65" style={{ width: `${Math.max(1, item.percentile)}%` }} /></div><p className="mt-1.5 text-xs text-muted-foreground">{locale === "zh" ? `核心命中 ${item.raw_count} 项` : `${item.raw_count} core hits`} · {item.contribution_rules.join("、") || "—"}</p></div>)}</div></section>
}

function BaziStatistics({ chart, locale, currentYear }: { chart: MetaphysicsChart; locale: Locale; currentYear: number }) {
  const elements = ["木", "火", "土", "金", "水"]
  const hiddenElements = Object.fromEntries(elements.map((element) => [element, 0])) as Record<string, number>
  const visibleGods = new Map<string, number>()
  const hiddenGods = new Map<string, number>()
  chart.pillars.forEach((pillar) => {
    visibleGods.set(pillar.ten_god || "—", (visibleGods.get(pillar.ten_god || "—") ?? 0) + 1)
    pillar.hidden_stems.forEach((stem) => {
      hiddenElements[stem.element] = (hiddenElements[stem.element] ?? 0) + 1
      hiddenGods.set(stem.ten_god || "—", (hiddenGods.get(stem.ten_god || "—") ?? 0) + 1)
    })
  })
  const yangStems = new Set(["甲", "丙", "戊", "庚", "壬"])
  const yinStems = new Set(["乙", "丁", "己", "辛", "癸"])
  const yangBranches = new Set(["子", "寅", "辰", "午", "申", "戌"])
  const yinBranches = new Set(["丑", "卯", "巳", "未", "酉", "亥"])
  const visibleCharacters = chart.pillars.flatMap((pillar) => [pillar.stem, pillar.branch])
  const yangCount = visibleCharacters.filter((value, index) => index % 2 === 0 ? yangStems.has(value) : yangBranches.has(value)).length
  const yinCount = visibleCharacters.filter((value, index) => index % 2 === 0 ? yinStems.has(value) : yinBranches.has(value)).length
  const unknownCount = 8 - yangCount - yinCount
  const currentCycle = chart.birth_profile.dayun.cycles.find((cycle) => cycle.start_year <= currentYear && currentYear <= cycle.end_year)
  const relationshipGroups = [
    { key: "合", label: locale === "zh" ? "合" : "Combine" },
    { key: "会", label: locale === "zh" ? "会" : "Meeting" },
    { key: "冲", label: locale === "zh" ? "冲" : "Clash" },
    { key: "克", label: locale === "zh" ? "克" : "Control" },
    { key: "刑", label: locale === "zh" ? "刑" : "Punish" },
    { key: "害", label: locale === "zh" ? "害" : "Harm" },
    { key: "破", label: locale === "zh" ? "破" : "Break" },
  ]
  const allRelations = [...chart.stem_relations, ...chart.branch_relations]
  return (
    <div className="grid border-y border-border/60 md:grid-cols-2 xl:grid-cols-5 xl:divide-x xl:divide-border/50">
      <StatisticBlock title={locale === "zh" ? "五行数量" : "Five elements"} description={locale === "zh" ? "明字与藏干分列" : "Visible and hidden separated"}>
        <CountRows values={elements.map((element) => ({ label: element, primary: chart.element_counts[element] ?? 0, secondary: hiddenElements[element] ?? 0, element }))} primaryLabel={locale === "zh" ? "明" : "V"} secondaryLabel={locale === "zh" ? "藏" : "H"} />
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "阴阳结构" : "Yin / Yang"} description={unknownCount ? (locale === "zh" ? `${unknownCount} 个待定明字未计入` : `${unknownCount} uncertain characters excluded`) : (locale === "zh" ? "只计算八个明字" : "Eight visible characters")}>
        <div className="mt-4 grid grid-cols-2 divide-x divide-border/50 text-center"><RawNumber label={locale === "zh" ? "阳" : "Yang"} value={yangCount} /><RawNumber label={locale === "zh" ? "阴" : "Yin"} value={yinCount} /></div>
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "十神频次" : "Ten Gods"} description={locale === "zh" ? `分母：明干 ${visibleCharacters.filter((_, index) => index % 2 === 0).length} 项 · 藏干 ${Array.from(hiddenGods.values()).reduce((sum, value) => sum + value, 0)} 项` : `Denominators: ${visibleCharacters.filter((_, index) => index % 2 === 0).length} visible stems · ${Array.from(hiddenGods.values()).reduce((sum, value) => sum + value, 0)} hidden stems`}>
        <div className="mt-3 space-y-2 text-xs leading-5"><p><strong>{locale === "zh" ? "明干" : "Visible stems"}：</strong>{formatCounts(visibleGods)}</p><p><strong>{locale === "zh" ? "藏干" : "Hidden stems"}：</strong>{formatCounts(hiddenGods)}</p></div>
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "干支关系" : "Relationships"} description={locale === "zh" ? "按已识别规则计数" : "Exact recognized rules"}>
        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-2 text-xs">{relationshipGroups.map((group) => <span key={group.key}><strong>{group.label}</strong> {allRelations.filter((item) => item.includes(group.key)).length}</span>)}</div>
        <p className="mt-3 text-xs leading-5 text-muted-foreground">{allRelations.join(" / ") || "—"}</p>
      </StatisticBlock>
      <StatisticBlock title={locale === "zh" ? "当前大运" : "Current Da Yun"} description={locale === "zh" ? "按公历年份定位" : "Located by calendar year"}>
        {currentCycle ? <div className="mt-3"><p className="text-2xl font-semibold text-primary">{currentCycle.ganzhi}</p><p className="mt-1 text-xs text-muted-foreground">{currentCycle.start_year}–{currentCycle.end_year} · {locale === "zh" ? `距周期末 ${Math.max(0, currentCycle.end_year - currentYear)} 年` : `${Math.max(0, currentCycle.end_year - currentYear)} years to cycle end`}</p></div> : <p className="mt-3 text-sm text-muted-foreground">—</p>}
      </StatisticBlock>
    </div>
  )
}

function StatisticBlock({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <section className="min-w-0 px-4 py-4"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs text-muted-foreground">{description}</p>{children}</section>
}

function CountRows({ values, primaryLabel, secondaryLabel }: { values: Array<{ label: string; primary: number; secondary: number; element: string }>; primaryLabel: string; secondaryLabel: string }) {
  return <div className="mt-3 space-y-1.5">{values.map((item) => <div key={item.label} className="grid grid-cols-[1rem_1fr] items-center gap-2 text-xs"><span data-element={item.element} className="chart-element-text font-semibold">{item.label}</span><span className="text-muted-foreground">{primaryLabel} {item.primary} · {secondaryLabel} {item.secondary}</span></div>)}</div>
}

function RawNumber({ label, value }: { label: string; value: number }) {
  return <div className="px-2"><p className="text-3xl font-semibold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{label}</p></div>
}

function formatCounts(counts: Map<string, number>) {
  return Array.from(counts.entries()).map(([label, count]) => `${label} ${count}`).join(" · ") || "—"
}

function DayunTimeline({ chart, locale, currentYear }: { chart: MetaphysicsChart; locale: Locale; currentYear: number }) {
  const dayun = chart.birth_profile.dayun
  const currentRef = useRef<HTMLElement>(null)
  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    currentRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest", inline: "center" })
  }, [currentYear])
  if (dayun.status === "not_requested") return <p className="text-sm text-muted-foreground">—</p>
  if (dayun.status === "requires_hour") return <p className="text-sm leading-6 text-muted-foreground">{locale === "zh" ? dayun.note : "The birth hour is uncertain, so a falsely precise Da Yun cycle is withheld."}</p>
  return <div className="overflow-x-auto pb-3 custom-scrollbar"><div className="flex min-w-max gap-3">{dayun.cycles.map((cycle) => { const isCurrent = cycle.start_year <= currentYear && currentYear <= cycle.end_year; return <article ref={isCurrent ? currentRef : undefined} key={`${cycle.index}-${cycle.start_year}`} aria-current={isCurrent ? "step" : undefined} className={`w-40 shrink-0 border-t-2 px-2 py-3 ${isCurrent ? "border-primary bg-primary/8" : "border-border/60"}`}><div className="flex items-center justify-between gap-2"><strong>{cycle.label}</strong>{isCurrent ? <span className="text-[0.65rem] font-semibold text-primary">{locale === "zh" ? "当前（按年份）" : "Current by year"}</span> : null}</div><p className="mt-2 text-xs text-muted-foreground">{cycle.start_age}–{cycle.end_age} {locale === "zh" ? "岁" : "years"}</p><p className="text-xs text-muted-foreground">{cycle.start_year}–{cycle.end_year}</p></article>})}</div></div>
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
  return (
    <div aria-hidden="true" className="chart-export-stage">
      <article id={exportTargetId} aria-hidden="true" data-chart-export-root className="chart-share-canvas chart-export-canvas">
        <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={generatedAt} trustNote={trustNote} />
        <div className="mt-8"><BaziStatistics chart={chart} locale={locale} currentYear={currentYearInTimeZone(chart.timezone)} /></div>
        <div className="mt-8"><BaziProfessionalTable chart={chart} locale={locale} /></div>
      </article>
    </div>
  )
}
