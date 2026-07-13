"use client"

import { useEffect, useId, useRef, useState } from "react"
import { ChartExportButton } from "@/components/tools/chart-export-button"
import { buildBaziMarkdown } from "@/lib/chart-markdown"
import type { MetaphysicsChart } from "@/types/api"

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
  const facts = chart.calendar_facts
  const currentYear = currentYearInTimeZone(chart.timezone)
  const dayun = chart.birth_profile.dayun
  const currentCycle = dayun.cycles.find(
    (cycle) => cycle.start_year <= currentYear && currentYear <= cycle.end_year,
  )
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
    <section className="chart-report space-y-10" aria-label={locale === "zh" ? "八字排盘结果" : "BaZi chart result"}>
      <div data-export-exclude className="flex justify-end">
        <ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出命盘" : "Export chart"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "命盘图片生成失败，请重试。" : "Chart image could not be generated. Try again."} safeBaseFilename={`bazi-${chart.birth_profile.input_date}`} />
      </div>

      <BaziIdentitySummary chart={chart} locale={locale} subjectName={subjectName} calculationRule={calculationRule} currentCycleText={currentCycleText} generatedAt={resultGeneratedAt} trustNote={trustNote} />

      <ReportChapter title={locale === "zh" ? "专业命盘" : "Professional chart"} intro={locale === "zh" ? "四柱信息按列对照；地势、自坐、空亡与干支关系均由当前排盘规则直接计算。" : "Compare all four pillars by column. Life stages, voids, and stem/branch relations are calculated from the selected rules."}>
        <BaziProfessionalTable chart={chart} locale={locale} />
      </ReportChapter>

      <ReportChapter title={locale === "zh" ? "大运时间线" : "Da Yun timeline"} intro={locale === "zh" ? "当前标记按公历年份定位；精确交接以所选起运规则为准。" : "The current marker is located by calendar year. Exact handoff follows the configured start rule."}>
        <DayunTimeline chart={chart} locale={locale} currentYear={currentYear} />
      </ReportChapter>

      <ReportChapter title={locale === "zh" ? "排盘时令与规则" : "Calendar context and rules"}>
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
          <p className="text-xs leading-5 text-muted-foreground">{Object.values(chart.birth_profile.engines).join(" · ")} · {trustNote}</p>
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

function ReportChapter({ title, intro, children }: { title: string; intro?: string; children: React.ReactNode }) {
  return <section className="chart-report-chapter border-t border-border/60 pt-6"><h2 className="text-xl font-semibold">{title}</h2>{intro ? <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{intro}</p> : null}<div className="mt-5">{children}</div></section>
}

function BaziProfessionalTable({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const rows = [
    { label: locale === "zh" ? "干神" : "Stem relation", values: chart.pillars.map((pillar) => pillar.ten_god) },
    { label: locale === "zh" ? "天干" : "Stem", values: chart.pillars.map((pillar) => pillar.stem), elements: chart.pillars.map((pillar) => pillar.stem_element), prominent: true },
    { label: locale === "zh" ? "地支" : "Branch", values: chart.pillars.map((pillar) => pillar.branch), elements: chart.pillars.map((pillar) => pillar.branch_element), prominent: true },
    { label: locale === "zh" ? "藏干" : "Hidden stems", values: chart.pillars.map((pillar) => pillar.hidden_stems.map((item) => `${item.stem}·${item.element}`).join(" / ") || "—") },
    { label: locale === "zh" ? "支神" : "Hidden relations", values: chart.pillars.map((pillar) => pillar.hidden_stems.map((item) => item.ten_god).join(" / ") || "—") },
    { label: locale === "zh" ? "纳音" : "Na Yin", values: chart.pillars.map((pillar) => pillar.nayin) },
    { label: locale === "zh" ? "空亡" : "Void", values: chart.pillars.map((pillar) => pillar.xunkong) },
    { label: locale === "zh" ? "地势" : "Life stage", values: chart.pillars.map((pillar) => pillar.di_shi) },
    { label: locale === "zh" ? "自坐" : "Self seat", values: chart.pillars.map((pillar) => pillar.self_seat) },
  ]
  const status = Object.entries(chart.element_season_status)
  return (
    <div className="overflow-x-auto rounded-xl border border-border/50 bg-surface-elevated/35 custom-scrollbar">
      <div className="min-w-[22rem] md:min-w-[48rem]">
        <div className="grid grid-cols-[3.75rem_repeat(4,minmax(4.6rem,1fr))] border-b border-border/50 bg-primary/[0.06] md:grid-cols-[7rem_repeat(4,minmax(0,1fr))]">
          <div className="px-2 py-3 text-xs font-semibold text-muted-foreground">{locale === "zh" ? "四柱" : "Pillars"}</div>
          {chart.pillars.map((pillar) => <div key={pillar.label} className="border-l border-border/35 px-2 py-3 text-center text-sm font-semibold">{pillar.label}{locale === "zh" ? "柱" : ""}</div>)}
        </div>
        {rows.map((row, rowIndex) => (
          <div key={row.label} className={`grid grid-cols-[3.75rem_repeat(4,minmax(4.6rem,1fr))] border-b border-border/30 last:border-b-0 md:grid-cols-[7rem_repeat(4,minmax(0,1fr))] ${rowIndex % 2 ? "bg-background/50" : ""}`}>
            <div className="flex items-center px-2 py-3 text-xs font-medium text-muted-foreground md:px-3">{row.label}</div>
            {row.values.map((value, index) => (
              <div key={`${row.label}-${chart.pillars[index].label}`} data-element={row.elements?.[index]} className="flex min-h-12 items-center justify-center border-l border-border/30 px-1.5 py-2 text-center text-xs leading-5 md:px-3 md:text-sm">
                <span className={row.prominent ? "chart-element-text text-3xl font-semibold leading-none md:text-4xl" : "break-words"}>{value}</span>
              </div>
            ))}
          </div>
        ))}
        <div className="space-y-3 border-t border-border/50 bg-primary/[0.035] px-3 py-4 text-sm leading-6 md:px-5">
          <p><strong>{locale === "zh" ? "天干关系" : "Stem relations"}：</strong>{chart.stem_relations.join(" / ") || "—"}</p>
          <p><strong>{locale === "zh" ? "地支关系" : "Branch relations"}：</strong>{chart.branch_relations.join(" / ") || "—"}</p>
          <div className="flex flex-wrap gap-x-5 gap-y-2" aria-label={locale === "zh" ? "五行旺相休囚死" : "Seasonal element states"}>
            {status.map(([element, value]) => <span key={element} data-element={element} className="chart-element-text font-semibold">{element}{value}</span>)}
          </div>
        </div>
      </div>
    </div>
  )
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
        <div className="mt-8"><BaziProfessionalTable chart={chart} locale={locale} /></div>
      </article>
    </div>
  )
}
