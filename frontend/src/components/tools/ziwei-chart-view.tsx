"use client"

import { useEffect, useId, useState } from "react"
import { Maximize2 } from "lucide-react"
import { ChartExportButton } from "@/components/tools/chart-export-button"
import { ChartAssetExportButton } from "@/components/tools/chart-asset-export-button"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { buildZiweiMarkdown } from "@/lib/chart-markdown"
import type { MetaphysicsStatistics, RarityMetric } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import type { IFunctionalPalace } from "iztro/lib/astro/FunctionalPalace"

type Locale = "en" | "zh"
type DisplayMode = "simple" | "study" | "professional"

const PALACE_POSITIONS = [[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3], [2, 3], [1, 3], [0, 3], [0, 2], [0, 1]] as const

export type ZiweiProvenance = {
  configId?: string
  algorithm: "default" | "zhongzhou"
  astroType: "heaven" | "earth" | "human"
  yearDivide: "normal" | "exact"
  dayBoundary: "current" | "forward"
  calendar: "solar" | "lunar"
  fixLeap: boolean
  isLeapMonth: boolean
}

export type ZiweiArchiveMode = "standard" | "legacy-static" | "legacy-nonstandard"
export type ZiweiStatisticsStatus = "loading" | "ready" | "unavailable"

function getProvenanceLabels(provenance: ZiweiProvenance, locale: Locale) {
  if (locale === "zh") {
    return {
      algorithm: provenance.algorithm === "zhongzhou" ? "中州派" : "通行法",
      astroType: provenance.astroType === "earth" ? "地盘" : provenance.astroType === "human" ? "人盘" : "天盘",
      yearDivide: provenance.yearDivide === "exact" ? "立春" : "农历正月初一",
      dayBoundary: provenance.dayBoundary === "forward" ? "晚子时换日" : "晚子时不换日",
      calendar: provenance.calendar === "lunar" ? "农历" : "公历",
      fixLeap: provenance.fixLeap ? "修正闰月" : "不修正闰月",
      leapMonth: provenance.isLeapMonth ? "闰月" : "非闰月",
      notApplicable: "不适用",
    }
  }
  return {
    algorithm: provenance.algorithm === "zhongzhou" ? "Zhongzhou" : "Standard",
    astroType: provenance.astroType === "earth" ? "Earth chart" : provenance.astroType === "human" ? "Human chart" : "Heaven chart",
    yearDivide: provenance.yearDivide === "exact" ? "Start of Spring" : "Lunar New Year",
    dayBoundary: provenance.dayBoundary === "forward" ? "Late Zi advances the day" : "Late Zi stays on the current day",
    calendar: provenance.calendar === "lunar" ? "Lunar calendar" : "Solar calendar",
    fixLeap: provenance.fixLeap ? "Adjust leap month" : "Do not adjust leap month",
    leapMonth: provenance.isLeapMonth ? "Leap month" : "Non-leap month",
    notApplicable: "Not applicable",
  }
}

function formatTransformations(horoscope: IFunctionalHoroscope, locale: Locale) {
  const labels = locale === "zh" ? ["禄", "权", "科", "忌"] : ["Prosperity", "Power", "Merit", "Obstacle"]
  return horoscope.yearly.mutagen.map((star, index) => `${labels[index]} ${star || "—"}`).join(" · ")
}

export function ZiweiChartView({ chart, horoscope, horoscopeDate, generatedAt, locale, provenance, subjectName, statistics, statisticsStatus, statisticsError, archiveMode, onHoroscopeDateChange, onCreateStandardCopy }: {
  chart: IFunctionalAstrolabe
  horoscope: IFunctionalHoroscope
  horoscopeDate: string
  generatedAt: string
  locale: Locale
  provenance: ZiweiProvenance
  subjectName: string
  statistics: MetaphysicsStatistics | null
  statisticsStatus: ZiweiStatisticsStatus
  statisticsError?: string
  archiveMode: ZiweiArchiveMode
  onHoroscopeDateChange: (date: string) => void
  onCreateStandardCopy: () => void
}) {
  const exportTargetId = `ziwei-export-${useId().replaceAll(":", "")}`
  const palaceExportTargetId = `ziwei-palace-${useId().replaceAll(":", "")}`
  const [selectedPalaceIndex, setSelectedPalaceIndex] = useState(() => chart.palaces[0]?.index ?? 0)
  const [displayMode, setDisplayMode] = useState<DisplayMode>("simple")
  useEffect(() => {
    const saved = window.localStorage.getItem("iching:ziwei-display-mode")
    if (saved === "simple" || saved === "study" || saved === "professional") setDisplayMode(saved)
  }, [])
  function changeDisplayMode(nextMode: DisplayMode) {
    setDisplayMode(nextMode)
    window.localStorage.setItem("iching:ziwei-display-mode", nextMode)
  }
  const selectedPalace = chart.palaces.find((palace) => palace.index === selectedPalaceIndex) ?? chart.palaces[0]
  const provenanceLabels = getProvenanceLabels(provenance, locale)
  const markdown = buildZiweiMarkdown(chart, horoscope, subjectName, locale, statistics ?? undefined, { archiveMode, provenance })
  const trustNote = locale === "zh"
    ? "按统一通行法排盘，并结合十二宫、星曜与历法统计整理重点。"
    : "Calculated with one standard method, then organized through palaces, stars, and calendar statistics."

  return (
    <section className="chart-report min-w-0 space-y-8" aria-label={locale === "zh" ? "紫微斗数星盘结果" : "Zi Wei Dou Shu chart result"}>
      <div data-export-exclude className="flex justify-end">
        <ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出命盘" : "Export chart"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "命盘图片生成失败，请重试。" : "Chart image could not be generated. Try again."} safeBaseFilename={`ziwei-${horoscopeDate}`} copyLabel={locale === "zh" ? "复制 Markdown" : "Copy Markdown"} copySuccess={locale === "zh" ? "Markdown 已复制" : "Markdown copied"} copyError={locale === "zh" ? "复制失败，请改用下载。" : "Copy failed. Use the download instead."} />
      </div>

      <ZiweiIdentitySummary chart={chart} horoscope={horoscope} horoscopeDate={horoscopeDate} generatedAt={generatedAt} locale={locale} trustNote={trustNote} subjectName={subjectName} />

      <ZiweiArchiveBanner archiveMode={archiveMode} locale={locale} onCreateStandardCopy={onCreateStandardCopy} />

      <ZiweiDisplayModeControl mode={displayMode} locale={locale} onChange={changeDisplayMode} />

      <ZiweiSectionNav locale={locale} mode={displayMode} />

      <section id="ziwei-chart" className="chart-report-chapter min-w-0 scroll-mt-28 border-t border-border/60 pt-6">
        <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-semibold">{locale === "zh" ? "命盘" : "Chart"}</h2><p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "手机先看精简宫位卡；桌面与全盘模式保留完整专业密度。" : "Mobile starts with readable palace cards; desktop and full-chart mode retain professional density."}</p></div><div data-export-exclude className="flex flex-wrap gap-2"><ChartAssetExportButton targetId={palaceExportTargetId} label={locale === "zh" ? "单独导出十二宫" : "Export palace chart"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "十二宫导出失败。" : "Palace chart export failed."} safeBaseFilename={`ziwei-palaces-${horoscopeDate}`} /><FullChartDialog chart={chart} horoscope={horoscope} locale={locale} /></div></div>
        <div className="mt-5 md:hidden"><MobilePalaceRail chart={chart} horoscope={horoscope} locale={locale} selectedPalaceIndex={selectedPalace?.index} onSelect={setSelectedPalaceIndex} /></div>
        <div className="mt-5 hidden max-w-full overflow-x-auto pb-2 md:block" tabIndex={0} aria-label={locale === "zh" ? "十二宫星盘，可横向滚动" : "Twelve-palace chart, horizontally scrollable"}>
          <ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive selectedPalaceIndex={selectedPalace?.index} onSelect={setSelectedPalaceIndex} />
        </div>
        {selectedPalace ? <SelectedPalaceDetail selectedPalace={selectedPalace} locale={locale} /> : null}
      </section>

      <ZiweiThemeSections chart={chart} horoscope={horoscope} statistics={statistics} locale={locale} sectionId="ziwei-themes" />

      <section id="ziwei-periods" className="chart-report-chapter scroll-mt-28 border-t border-border/60 pt-6"><h2 className="text-xl font-semibold">{locale === "zh" ? "运限" : "Periods"}</h2><p className="mt-2 text-sm text-muted-foreground">{archiveMode === "standard" ? (locale === "zh" ? "选择日期后同步查看本命、大限、流年、流月、流日与流时。" : "Choose a date to inspect natal, decadal, yearly, monthly, daily, and hourly layers together.") : (locale === "zh" ? "旧档案保留保存时的运限快照；日期已锁定。" : "Legacy archives retain the saved period snapshot; the date is locked.")}</p><ZiweiPeriodPanel horoscope={horoscope} selectedDate={horoscopeDate} onSelectedDateChange={onHoroscopeDateChange} locked={archiveMode !== "standard"} locale={locale} /></section>

      {displayMode !== "simple" ? <section id="ziwei-stars" className="chart-report-chapter scroll-mt-28 border-t border-border/60 pt-6"><h2 className="text-xl font-semibold">{locale === "zh" ? "星曜" : "Stars"}</h2><p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "按主星、辅星、杂曜与四化反查落宫。" : "Browse major, supporting, adjective, and transformed stars by palace."}</p><StarBrowser chart={chart} locale={locale} /></section> : null}

      {displayMode !== "simple" ? <section id="ziwei-statistics" className="chart-report-chapter scroll-mt-28 border-t border-border/60 pt-6"><h2 className="text-xl font-semibold">{locale === "zh" ? "统计" : "Statistics"}</h2><p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "查看关键结构在 120 年历法样本中的出现频率与辨识度。" : "Explore the frequency and distinctiveness of key structures across the 120-year calendar sample."}</p><div className="mt-5 space-y-7"><ZiweiStatistics chart={chart} horoscope={horoscope} locale={locale} /><ZiweiRarityPanel chart={chart} statistics={statistics} status={statisticsStatus} error={statisticsError} locale={locale} /></div></section> : null}

      {displayMode === "professional" ? <details data-export-exclude className="border-t border-border/60 pt-5">
        <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{locale === "zh" ? "专业排盘数据与来源" : "Professional chart data and provenance"}</summary>
        <div className="mt-4 space-y-2 text-xs leading-5 text-muted-foreground">
          <p><strong className="text-foreground">{locale === "zh" ? "排盘引擎" : "Engine"}:</strong> iztro 2.5.8 · MIT</p>
          {provenance.configId ? <p><strong className="text-foreground">{locale === "zh" ? "统一配置" : "Standard config"}:</strong> {provenance.configId}</p> : null}
          <p><strong className="text-foreground">{locale === "zh" ? "安星算法" : "Algorithm / school"}:</strong> {provenanceLabels.algorithm}{provenance.algorithm === "zhongzhou" ? ` · ${provenanceLabels.astroType}` : ""}</p>
          <p><strong className="text-foreground">{locale === "zh" ? "规则" : "Rules"}:</strong> {provenanceLabels.calendar} · {provenanceLabels.yearDivide} · {provenanceLabels.dayBoundary}</p>
          <p><strong className="text-foreground">{locale === "zh" ? "闰月" : "Leap month"}:</strong> {provenance.calendar === "lunar" ? `${provenanceLabels.fixLeap} · ${provenanceLabels.leapMonth}` : provenanceLabels.notApplicable}</p>
          <p>{locale === "zh" ? "星曜、四化与运限为确定性排盘数据；解释层不混入排盘事实，也不自动生成预测断语。" : "Stars, transformations, and periods are deterministic chart data. Interpretation remains separate from chart facts, and no predictive prose is generated."}</p>
          {statistics ? <><p>{statistics.baseline.id} · {statistics.baseline.hash}</p><p>{statistics.disclaimer}</p></> : <p>{statisticsError ?? (locale === "zh" ? "频率样本未载入。" : "Frequency samples were not loaded.")}</p>}
        </div>
      </details> : null}

      <ZiweiExportCanvas exportTargetId={exportTargetId} chart={chart} horoscope={horoscope} horoscopeDate={horoscopeDate} generatedAt={generatedAt} locale={locale} trustNote={`${trustNote}${statistics ? ` ${statistics.disclaimer}` : ""}`} subjectName={subjectName} statistics={statistics} statisticsStatus={statisticsStatus} statisticsError={statisticsError} archiveMode={archiveMode} provenance={provenance} />
      <div aria-hidden="true" className="chart-export-stage"><article id={palaceExportTargetId} className="chart-share-canvas chart-export-canvas"><ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive={false} /></article></div>
    </section>
  )
}

function ZiweiArchiveBanner({ archiveMode, locale, onCreateStandardCopy }: { archiveMode: ZiweiArchiveMode; locale: Locale; onCreateStandardCopy: () => void }) {
  if (archiveMode === "standard") return null
  const nonstandard = archiveMode === "legacy-nonstandard"
  return (
    <aside data-export-exclude className="flex flex-col gap-3 rounded-xl border border-border/60 bg-surface px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-semibold">{nonstandard ? (locale === "zh" ? "非标准旧规则档案" : "Legacy nonstandard chart") : (locale === "zh" ? "旧档案静态快照" : "Legacy static snapshot")}</p>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">{nonstandard
          ? (locale === "zh" ? "此档案使用旧规则，以只读快照保留；日期与频率统计不会重算。" : "This archive used legacy rules and is preserved read-only; its date and frequency statistics are not recalculated.")
          : (locale === "zh" ? "此档案缺少完整标准化输入；当前日期锁定，仅展示保存时的结果。" : "This archive lacks complete normalized inputs. Its date is locked and only the saved result is shown.")}</p>
      </div>
      {nonstandard ? <Button type="button" variant="outline" onClick={onCreateStandardCopy}>{locale === "zh" ? "按统一规则创建副本" : "Create standard copy"}</Button> : null}
    </aside>
  )
}

function ZiweiDisplayModeControl({ mode, locale, onChange }: { mode: DisplayMode; locale: Locale; onChange: (mode: DisplayMode) => void }) {
  const options: Array<{ value: DisplayMode; zh: string; en: string }> = [
    { value: "simple", zh: "简明", en: "Simple" },
    { value: "study", zh: "研习", en: "Study" },
    { value: "professional", zh: "专业", en: "Professional" },
  ]
  return <div data-export-exclude className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/55 bg-surface px-4 py-3"><div><p className="text-sm font-semibold">{locale === "zh" ? "查看深度" : "Detail level"}</p><p className="mt-0.5 text-xs text-muted-foreground">{locale === "zh" ? "先看命盘、重点与运限，需要时再展开星曜和统计。" : "Start with the chart, themes, and periods; expand stars and statistics when needed."}</p></div><div className="inline-flex rounded-xl bg-muted/60 p-1" role="group" aria-label={locale === "zh" ? "紫微查看深度" : "Zi Wei detail level"}>{options.map((option) => <button key={option.value} type="button" aria-pressed={mode === option.value} onClick={() => onChange(option.value)} className={`min-w-16 rounded-lg px-3 py-2 text-sm font-semibold transition ${mode === option.value ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>{locale === "zh" ? option.zh : option.en}</button>)}</div></div>
}

function ZiweiSectionNav({ locale, mode }: { locale: Locale; mode: DisplayMode }) {
  const coreItems = locale === "zh" ? [["#ziwei-chart", "命盘"], ["#ziwei-themes", "重点"], ["#ziwei-periods", "运限"]] : [["#ziwei-chart", "Chart"], ["#ziwei-themes", "Themes"], ["#ziwei-periods", "Periods"]]
  const studyItems = locale === "zh" ? [["#ziwei-stars", "星曜"], ["#ziwei-statistics", "统计"]] : [["#ziwei-stars", "Stars"], ["#ziwei-statistics", "Statistics"]]
  const items = mode === "simple" ? coreItems : [...coreItems, ...studyItems]
  return <nav aria-label={locale === "zh" ? "紫微命盘章节" : "Zi Wei chart sections"} className="sticky top-20 z-20 -mx-2 flex gap-1 overflow-x-auto rounded-2xl border border-border/60 bg-background/90 p-1.5 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-background/75">{items.map(([href, label]) => <a key={href} href={href} className="min-w-20 flex-1 whitespace-nowrap rounded-xl px-4 py-2.5 text-center text-sm font-semibold text-muted-foreground transition hover:bg-primary/8 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{label}</a>)}</nav>
}

function FullChartDialog({ chart, horoscope, locale }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale }) {
  return <Dialog><DialogTrigger asChild><Button type="button" variant="outline"><Maximize2 aria-hidden="true" className="mr-2 size-4" />{locale === "zh" ? "全盘模式" : "Full chart"}</Button></DialogTrigger><DialogContent className="h-[94dvh] max-w-[96vw] overflow-auto p-4 sm:max-w-[96vw]"><DialogHeader><DialogTitle>{locale === "zh" ? "紫微斗数全盘" : "Full Zi Wei chart"}</DialogTitle><DialogDescription>{locale === "zh" ? "适合桌面、平板横屏或投屏查看。" : "Optimized for desktop, landscape tablet, or presentation."}</DialogDescription></DialogHeader><div className="min-w-[72rem]"><ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive={false} /></div></DialogContent></Dialog>
}

function MobilePalaceRail({ chart, horoscope, locale, selectedPalaceIndex, onSelect }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale; selectedPalaceIndex?: number; onSelect: (index: number) => void }) {
  return <div className="grid grid-cols-2 gap-2">{chart.palaces.slice(0, 12).map((palace) => { const selected = palace.index === selectedPalaceIndex; const decadal = palace.index === horoscope.decadal.index; const yearly = palace.index === horoscope.yearly.index; return <button type="button" key={`${palace.name}-${palace.index}`} onClick={() => onSelect(palace.index)} aria-pressed={selected} className={`min-h-32 rounded-xl border p-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${selected ? "border-primary bg-primary/10" : "border-border/55 bg-surface"}`}><span className="flex items-start justify-between gap-2"><strong>{palace.name}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-xs text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></span><span className="mt-2 flex flex-wrap gap-1">{decadal ? <small className="rounded-full bg-primary/12 px-1.5 py-0.5 font-semibold text-primary">{locale === "zh" ? "大限" : "Decadal"}</small> : null}{yearly ? <small className="rounded-full bg-primary/12 px-1.5 py-0.5 font-semibold text-primary">{locale === "zh" ? "流年" : "Year"}</small> : null}</span><span className="mt-2 block text-sm font-semibold text-primary">{palace.majorStars.map((star) => star.name).join(" · ") || (locale === "zh" ? "空宫" : "Empty")}</span><span className="mt-2 line-clamp-2 block text-xs leading-5 text-muted-foreground">{[...palace.minorStars, ...palace.adjectiveStars].map((star) => star.name).join(" · ") || "—"}</span></button> })}</div>
}

function ZiweiThemeSections({ chart, horoscope, statistics, locale, sectionId }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; statistics: MetaphysicsStatistics | null; locale: Locale; sectionId?: string }) {
  const themes = locale === "zh"
    ? [
        { key: "career", title: "事业", palaceAliases: [["命"], ["官禄", "事业"], ["财帛"], ["迁移"]], note: "从命宫、官禄、财帛与迁移宫看事业结构如何展开。" },
        { key: "wealth", title: "财富", palaceAliases: [["命"], ["财帛"], ["田宅"], ["福德"]], note: "从命宫、财帛、田宅与福德宫看资源与积累结构。" },
        { key: "relationship", title: "感情", palaceAliases: [["命"], ["夫妻"], ["福德"], ["迁移"]], note: "从命宫、夫妻、福德与迁移宫看关系互动结构。" },
        { key: "health", title: "身心结构", palaceAliases: [["命"], ["疾厄"], ["福德"]], note: "从命宫、疾厄与福德宫看传统身心承压结构。" },
      ]
    : [
        { key: "career", title: "Career", palaceAliases: [["soul", "life"], ["career", "official"], ["wealth", "finance"], ["surface", "travel"]], note: "Connects the life, career, wealth, and travel palaces into one career structure." },
        { key: "wealth", title: "Wealth", palaceAliases: [["soul", "life"], ["wealth", "finance"], ["property"], ["spirit", "fortune"]], note: "Connects the life, wealth, property, and spirit palaces into one resource structure." },
        { key: "relationship", title: "Relationships", palaceAliases: [["soul", "life"], ["spouse", "marriage"], ["spirit", "fortune"], ["surface", "travel"]], note: "Connects the life, spouse, spirit, and travel palaces into one relationship structure." },
        { key: "health", title: "Mind-body structure", palaceAliases: [["soul", "life"], ["health", "illness"], ["spirit", "fortune"]], note: "Connects the life, health, and spirit palaces into a traditional pressure structure." },
      ]
  const allStars = (palace: IFunctionalPalace) => [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]
  const sixAuspicious = new Set(locale === "zh" ? ["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"] : ["officer", "helper", "scholar", "artist", "assistant", "aide"])
  const sixChallenging = new Set(locale === "zh" ? ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"] : ["driven", "tangled", "impulsive", "spark", "ideologue", "fickle"])
  return (
    <section id={sectionId} className="chart-report-chapter scroll-mt-28 border-t border-border/60 pt-6">
      <h2 className="text-xl font-semibold">{locale === "zh" ? "四类主题结构" : "Four structural themes"}</h2>
      <p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "把十二宫、星曜、四化与样本频率连成四条最值得先看的主题主线。" : "Connects palaces, stars, transformations, and sample frequency into four themes worth seeing first."}</p>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        {themes.map((theme) => {
          const palaces = theme.palaceAliases.flatMap((aliases) => {
            const palace = chart.palaces.find((item) => aliases.some((name) => item.name.toLowerCase().includes(name.toLowerCase())))
            return palace ? [palace] : []
          }).filter((palace, index, values) => values.findIndex((item) => item.index === palace.index) === index)
          if (!palaces.length) return <article key={theme.key} className="rounded-xl border border-border/50 bg-surface p-4"><h3 className="font-semibold">{theme.title}</h3><p className="mt-3 text-sm text-muted-foreground">{locale === "zh" ? "当前语言数据中未识别对应宫位。" : "The corresponding palaces were not identified in this locale."}</p><p className="mt-3 text-xs leading-5 text-muted-foreground">{theme.note}</p></article>
          const relatedIndexes = new Set(palaces.map((palace) => palace.index))
          const rarity = statistics?.rarity_metrics.filter((metric) => metric.status !== "unsupported" && metric.feature_id.includes(".mutagen.") && [...relatedIndexes].some((index) => metric.feature_id.includes(`palace-${index}`))).slice(0, 4) ?? []
          return (
            <article key={theme.key} className="rounded-xl border border-border/50 bg-surface p-4">
              <h3 className="font-semibold">{theme.title}</h3>
              <div className="mt-3 divide-y divide-border/45 border-y border-border/45">{palaces.map((palace) => { const stars = allStars(palace); const transformations = stars.filter((star) => star.mutagen).map((star) => `${star.name}·${locale === "zh" ? "化" : ""}${star.mutagen}`); const markers = [palace.index === horoscope.decadal.index ? (locale === "zh" ? "大限" : "Decadal") : null, palace.index === horoscope.yearly.index ? (locale === "zh" ? "流年" : "Annual") : null].filter(Boolean); return <div key={palace.index} className="grid gap-1 py-3 sm:grid-cols-[6rem_1fr]"><div><p className="text-sm font-semibold">{palace.name}</p><p className="text-xs text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}{markers.length ? ` · ${markers.join("/")}` : ""}</p></div><div><p className="text-sm font-medium text-primary">{palace.majorStars.map((star) => `${star.name}${star.brightness ? `(${star.brightness})` : ""}`).join(" · ") || (locale === "zh" ? "空宫" : "Empty")}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{transformations.join(" · ") || (locale === "zh" ? "无生年四化标记" : "No natal transformation")} · {locale === "zh" ? "六吉星分类" : "Six-auxiliary category"} {stars.filter((star) => sixAuspicious.has(star.name)).length} · {locale === "zh" ? "六煞星分类" : "Six-challenging category"} {stars.filter((star) => sixChallenging.has(star.name)).length} · {locale === "zh" ? "仅计数，不作加减分" : "counts only; not an additive score"}</p></div></div> })}</div>
              {rarity.length ? <div className="mt-3 border-t border-border/45 pt-3"><p className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "相关结构样本频率" : "Related structural sample frequency"}</p><ul className="mt-2 space-y-1 text-xs text-muted-foreground">{rarity.map((metric) => <li key={metric.feature_id}>{ziweiMetricLabel(metric.feature_id, chart, locale)} · {metric.display_percentage}</li>)}</ul></div> : null}
              <p className="mt-3 border-t border-border/45 pt-3 text-xs leading-5 text-muted-foreground">{theme.note}</p>
            </article>
          )
        })}
      </div>
    </section>
  )
}

function ZiweiPeriodPanel({ horoscope, selectedDate, onSelectedDateChange, locked, locale, showDateControl = true }: { horoscope: IFunctionalHoroscope; selectedDate: string; onSelectedDateChange: (date: string) => void; locked: boolean; locale: Locale; showDateControl?: boolean }) {
  const items = [
    { label: locale === "zh" ? "本命" : "Natal", name: horoscope.astrolabe.chineseDate, stem: horoscope.astrolabe.soul, branch: horoscope.astrolabe.body, mutagen: [] as string[] },
    { label: locale === "zh" ? "大限" : "Decadal", ...horoscope.decadal },
    { label: locale === "zh" ? "流年" : "Yearly", ...horoscope.yearly },
    { label: locale === "zh" ? "流月" : "Monthly", ...horoscope.monthly },
    { label: locale === "zh" ? "流日" : "Daily", ...horoscope.daily },
    { label: locale === "zh" ? "流时" : "Hourly", ...horoscope.hourly },
  ]
  return <div className="mt-5 space-y-5">{showDateControl ? <div className="max-w-xs"><label htmlFor="ziwei-period-date" className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "查看日期" : "Horoscope date"}</label><Input id="ziwei-period-date" className="mt-2" type="date" min="1900-01-31" max="2100-12-31" value={selectedDate} disabled={locked} onChange={(event) => onSelectedDateChange(event.target.value)} />{locked ? <p className="mt-2 text-xs text-muted-foreground">{locale === "zh" ? "静态档案日期已锁定" : "Date locked for static archive"}</p> : null}</div> : null}<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{items.map((item) => <article key={item.label} className="rounded-xl border border-border/50 bg-surface p-4"><p className="text-xs font-semibold text-muted-foreground">{item.label}</p><p className="mt-2 text-lg font-semibold">{"heavenlyStem" in item ? `${item.heavenlyStem}${item.earthlyBranch}` : `${item.stem} / ${item.branch}`}</p><p className="mt-1 text-sm text-muted-foreground">{item.name}</p><p className="mt-3 text-xs leading-5 text-muted-foreground">{item.mutagen?.length ? item.mutagen.map((star, index) => `${["禄", "权", "科", "忌"][index]} ${star}`).join(" · ") : "—"}</p></article>)}</div></div>
}

function StarBrowser({ chart, locale }: { chart: IFunctionalAstrolabe; locale: Locale }) {
  const all = chart.palaces.flatMap((palace) => [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars].map((star) => ({ ...star, palace: palace.name })))
  const auspicious = new Set(locale === "zh" ? ["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"] : ["officer", "helper", "scholar", "artist", "assistant", "aide"])
  const challenging = new Set(locale === "zh" ? ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"] : ["driven", "tangled", "impulsive", "spark", "ideologue", "fickle"])
  const groups = [
    { label: locale === "zh" ? "十四主星" : "Major stars", stars: chart.palaces.flatMap((palace) => palace.majorStars.map((star) => ({ ...star, palace: palace.name }))) },
    { label: locale === "zh" ? "六吉" : "Six auspicious", stars: all.filter((star) => auspicious.has(star.name)) },
    { label: locale === "zh" ? "六煞" : "Six challenging", stars: all.filter((star) => challenging.has(star.name)) },
    { label: locale === "zh" ? "其他星曜" : "Other stars", stars: chart.palaces.flatMap((palace) => palace.adjectiveStars.map((star) => ({ ...star, palace: palace.name }))) },
    { label: locale === "zh" ? "生年四化" : "Natal transformations", stars: chart.palaces.flatMap((palace) => [...palace.majorStars, ...palace.minorStars].filter((star) => star.mutagen).map((star) => ({ ...star, palace: palace.name }))) },
  ]
  return <div className="mt-5"><p className="mb-3 text-xs leading-5 text-muted-foreground">{locale === "zh" ? "六吉与六煞仅按传统星曜类别归档和计数，不相减，也不构成吉凶分数。" : "The six auxiliary and six challenging stars are traditional categories and counts only; they are not subtracted or scored."}</p><div className="grid gap-3 md:grid-cols-2">{groups.map((group) => <details key={group.label} open={group.stars.length <= 14} className="rounded-xl border border-border/50 bg-surface px-4 py-3"><summary className="cursor-pointer font-semibold">{group.label}<span className="ml-2 text-xs font-normal text-muted-foreground">{group.stars.length}</span></summary><div className="mt-3 flex flex-wrap gap-2 border-t border-border/45 pt-3">{group.stars.map((star, index) => <span key={`${star.name}-${star.palace}-${index}`} className="rounded-full bg-primary/[0.07] px-2.5 py-1 text-xs"><strong>{star.name}</strong>{star.mutagen ? ` · 化${star.mutagen}` : ""}{star.brightness ? ` · ${star.brightness}` : ""} → {star.palace}</span>)}</div></details>)}</div></div>
}

function ZiweiRarityPanel({ chart, statistics, status, error, locale }: { chart: IFunctionalAstrolabe; statistics: MetaphysicsStatistics | null; status: ZiweiStatisticsStatus; error?: string; locale: Locale }) {
  const level = locale === "zh" ? { common: "常见", less_common: "较少", rare: "稀有", very_rare: "罕见", unavailable: "不可用" } : { common: "Common", less_common: "Less common", rare: "Rare", very_rare: "Very rare", unavailable: "Unavailable" }
  if (status === "loading") return <section aria-live="polite"><h3 className="text-base font-semibold">{locale === "zh" ? "结构出现频率" : "Structural frequency"}</h3><p className="mt-3 text-sm text-muted-foreground">{locale === "zh" ? "频率样本正在后台载入；命盘与主题结构可先查看。" : "Frequency samples are loading in the background; the chart and structural themes are already available."}</p></section>
  if (!statistics) return <section aria-live="polite"><h3 className="text-base font-semibold">{locale === "zh" ? "结构出现频率" : "Structural frequency"}</h3><p className="mt-3 text-sm text-muted-foreground">{error ?? (locale === "zh" ? "频率样本暂时不可用；命盘事实不受影响。" : "Frequency samples are temporarily unavailable; chart facts are unaffected.")}</p></section>
  return <section><div className="flex flex-wrap items-end justify-between gap-2"><div><h3 className="text-base font-semibold">{locale === "zh" ? "结构出现频率" : "Structural frequency"}</h3><p className="mt-1 text-xs text-muted-foreground">{statistics.baseline.label} · {statistics.baseline.unique_state_count?.toLocaleString() ?? "—"} {locale === "zh" ? "个唯一日期时辰状态" : "unique date-time states"} · {statistics.baseline.sample_weight.toLocaleString()} {locale === "zh" ? "民用小时权重" : "civil-hour weight"}</p></div></div><div className="mt-4 grid gap-2 md:grid-cols-2">{statistics.rarity_metrics.map((metric) => <RarityRow key={metric.feature_id} metric={metric} label={ziweiMetricLabel(metric.feature_id, chart, locale)} levelLabel={level[metric.level]} locale={locale} />)}</div><p className="mt-4 text-xs leading-5 text-muted-foreground">{statistics.disclaimer}</p></section>
}

function RarityRow({ metric, label, levelLabel, locale }: { metric: RarityMetric; label: string; levelLabel: string; locale: Locale }) {
  const unsupported = metric.status === "unsupported"
  const zero = metric.status === "zero"
  const display = unsupported ? (locale === "zh" ? "暂无基线数据" : "No baseline data") : zero ? "0%" : metric.display_percentage
  const detail = unsupported ? (locale === "zh" ? "当前配置未收录此特征" : "Feature is not catalogued for this configuration") : zero ? (locale === "zh" ? "本参考周期未出现" : "Not observed in this reference") : `${levelLabel} · ${metric.hit_weight.toLocaleString()} / ${metric.total_weight.toLocaleString()}`
  return <div className="flex items-center justify-between gap-4 rounded-xl border border-border/45 px-4 py-3"><div><p className="text-sm font-semibold">{label}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></div><strong className="text-right text-primary">{display}</strong></div>
}

function ziweiMetricLabel(featureId: string, chart: IFunctionalAstrolabe, locale: Locale) {
  const zh = locale === "zh"
  const life = chart.palaces.find((palace) => palace.name === "命宫" || palace.name.toLowerCase().includes("soul"))
  const body = chart.palaces.find((palace) => palace.isBodyPalace)
  if (featureId.includes(".life_combo.")) return zh ? `命宫主星 · ${life?.majorStars.map((star) => star.name).join("、") || "空宫"}` : `Life palace · ${life?.majorStars.map((star) => star.name).join(", ") || "empty"}`
  if (featureId.includes(".body_branch.")) return zh ? `身宫 · ${body?.name ?? "—"}${body ? `（${body.earthlyBranch}）` : ""}` : `Body palace · ${body?.name ?? "—"}`
  if (featureId.includes(".five_elements.")) return zh ? `五行局 · ${chart.fiveElementsClass}` : `Five-element class · ${chart.fiveElementsClass}`
  if (featureId.includes(".empty_palaces.")) return zh ? `空宫数量 ${featureId.split(".").at(-1)}` : `${featureId.split(".").at(-1)} empty palaces`
  if (featureId.includes(".brightness.")) return zh ? `主星亮度组合 · ${featureId.split(".").slice(-2).join(" ")}` : `Major-star brightness · ${featureId.split(".").slice(-2).join(" ")}`
  if (featureId.includes(".mutagen.")) { const parts = featureId.split("."); const mutagen = ({ lu: "禄", quan: "权", ke: "科", ji: "忌" } as Record<string, string>)[parts.at(-2) ?? ""] ?? parts.at(-2); const palaceIndex = Number(parts.at(-1)?.replace("palace-", "")); const palace = chart.palaces.find((item) => item.index === palaceIndex); return zh ? `化${mutagen}落宫 · ${palace?.name ?? parts.at(-1)}` : `Transformation ${mutagen} · ${palace?.name ?? parts.at(-1)}` }
  if (featureId.includes(".auspicious_palaces.")) return zh ? `六吉分布 · ${featureId.split(".").at(-1)} 宫` : `Six auspicious stars across ${featureId.split(".").at(-1)} palaces`
  if (featureId.includes(".auspicious_max_density.")) return zh ? `六吉单宫最高密度 · ${featureId.split(".").at(-1)}` : `Max auspicious density · ${featureId.split(".").at(-1)}`
  if (featureId.includes(".challenging_palaces.")) return zh ? `六煞分布 · ${featureId.split(".").at(-1)} 宫` : `Six challenging stars across ${featureId.split(".").at(-1)} palaces`
  if (featureId.includes(".challenging_max_density.")) return zh ? `六煞单宫最高密度 · ${featureId.split(".").at(-1)}` : `Max challenging density · ${featureId.split(".").at(-1)}`
  return featureId
}

function ZiweiExportCanvas({ exportTargetId, chart, horoscope, horoscopeDate, generatedAt, locale, trustNote, subjectName, statistics, statisticsStatus, statisticsError, archiveMode, provenance }: { exportTargetId: string; chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; horoscopeDate: string; generatedAt: string; locale: Locale; trustNote: string; subjectName: string; statistics: MetaphysicsStatistics | null; statisticsStatus: ZiweiStatisticsStatus; statisticsError?: string; archiveMode: ZiweiArchiveMode; provenance: ZiweiProvenance }) {
  const labels = getProvenanceLabels(provenance, locale)
  return (
    <div aria-hidden="true" className="chart-export-stage">
      <article id={exportTargetId} aria-hidden="true" data-chart-export-root className="chart-share-canvas chart-export-canvas">
        <ZiweiIdentitySummary chart={chart} horoscope={horoscope} horoscopeDate={horoscopeDate} generatedAt={generatedAt} locale={locale} trustNote={trustNote} subjectName={subjectName} />
        {archiveMode !== "standard" ? <aside className="mt-6 rounded-xl border border-border/60 bg-surface p-4"><strong>{archiveMode === "legacy-nonstandard" ? (locale === "zh" ? "非标准旧规则档案" : "Legacy nonstandard chart") : (locale === "zh" ? "旧档案静态快照" : "Legacy static snapshot")}</strong><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "此导出保留原档案规则与锁定日期，不应视为统一通行法新版命盘。" : "This export retains the archive's original rules and locked date; it is not a new standard-config chart."}</p></aside> : null}
        <p className="mt-5 text-xs text-muted-foreground">{locale === "zh" ? "排盘规则" : "Chart rules"}: {provenance.configId ?? "legacy"} · {labels.algorithm} · {labels.astroType} · {labels.yearDivide} · {labels.dayBoundary} · {labels.calendar} · {labels.fixLeap}{provenance.calendar === "lunar" ? ` · ${labels.leapMonth}` : ""}</p>
        <div className="mt-8"><ZiweiThemeSections chart={chart} horoscope={horoscope} statistics={statistics} locale={locale} /></div>
        <div className="mt-8"><h2 className="text-xl font-semibold">{locale === "zh" ? "运限" : "Periods"}</h2><ZiweiPeriodPanel horoscope={horoscope} selectedDate={horoscopeDate} onSelectedDateChange={() => undefined} locked={archiveMode !== "standard"} locale={locale} showDateControl={false} /></div>
        <div className="mt-8"><ZiweiStatistics chart={chart} horoscope={horoscope} locale={locale} /></div>
        <div className="mt-8"><ZiweiRarityPanel chart={chart} statistics={statistics} status={statisticsStatus} error={statisticsError} locale={locale} /></div>
        <div className="mt-8">
          <ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive={false} />
        </div>
      </article>
    </div>
  )
}

type ChartStar = { name: string; brightness?: string; mutagen?: string }

function ZiweiStatistics({ chart, horoscope, locale }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale }) {
  const allStarsByPalace = chart.palaces.map((palace) => ({ palace, stars: [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars] as ChartStar[] }))
  const majorPlacements = chart.palaces.flatMap((palace) => palace.majorStars.map((star) => `${star.name}→${palace.name}`))
  const emptyPalaces = chart.palaces.filter((palace) => palace.majorStars.length === 0)
  const brightnessCounts = new Map<string, number>()
  chart.palaces.flatMap((palace) => palace.majorStars).forEach((star) => {
    const key = star.brightness || (locale === "zh" ? "未标" : "Unmarked")
    brightnessCounts.set(key, (brightnessCounts.get(key) ?? 0) + 1)
  })
  const natalTransformations = allStarsByPalace.flatMap(({ palace, stars }) => stars.filter((star) => star.mutagen).map((star) => `${star.mutagen} ${star.name}→${palace.name}`))
  const annualTransformations = horoscope.yearly.mutagen.map((starName, index) => {
    const palace = allStarsByPalace.find((entry) => entry.stars.some((star) => star.name === starName))?.palace
    const label = locale === "zh" ? ["禄", "权", "科", "忌"][index] : ["Prosperity", "Power", "Merit", "Obstacle"][index]
    return `${label} ${starName || "—"}${palace ? `→${palace.name}` : ""}`
  })
  const auspiciousNames = new Set(locale === "zh" ? ["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"] : ["officer", "helper", "scholar", "artist", "assistant", "aide"])
  const challengingNames = new Set(locale === "zh" ? ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"] : ["driven", "tangled", "impulsive", "spark", "ideologue", "fickle"])
  const importantPlacements = (names: Set<string>) => allStarsByPalace.flatMap(({ palace, stars }) => stars.filter((star) => names.has(star.name)).map((star) => `${star.name}→${palace.name}`))
  const auspiciousPlacements = importantPlacements(auspiciousNames)
  const challengingPlacements = importantPlacements(challengingNames)
  return (
    <div className="grid border-y border-border/60 md:grid-cols-2 xl:grid-cols-5 xl:divide-x xl:divide-border/50">
      <ZiweiStatisticBlock title={locale === "zh" ? "十四主星落宫" : "Major-star positions"} value={`${majorPlacements.length}`}>
        <p>{majorPlacements.join(" · ") || "—"}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "宫位星曜密度" : "Palace density"} value={`${emptyPalaces.length} ${locale === "zh" ? "空宫" : "empty"}`}>
        <p>{chart.palaces.map((palace) => `${palace.name} ${palace.majorStars.length + palace.minorStars.length + palace.adjectiveStars.length}`).join(" · ")}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "主星亮度" : "Major-star brightness"} value={`${chart.palaces.flatMap((palace) => palace.majorStars).length}`}>
        <p>{Array.from(brightnessCounts.entries()).map(([name, count]) => `${name} ${count}`).join(" · ") || "—"}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "四化落宫" : "Transformations"} value={`${natalTransformations.length} / ${annualTransformations.length}`}>
        <p><strong>{locale === "zh" ? "生年" : "Natal"}：</strong>{natalTransformations.join(" · ") || "—"}</p><p className="mt-2"><strong>{locale === "zh" ? "流年" : "Annual"}：</strong>{annualTransformations.join(" · ")}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "六吉与六煞（分类计数）" : "Six-star categories (counts)"} value={locale === "zh" ? `六吉 ${auspiciousPlacements.length} · 六煞 ${challengingPlacements.length}` : `Auxiliary ${auspiciousPlacements.length} · Challenging ${challengingPlacements.length}`}>
        <p>{locale === "zh" ? "仅分类计数，不相减、不作吉凶分数。" : "Category counts only; not subtracted or scored."}</p><p className="mt-2"><strong>{locale === "zh" ? "六吉" : "Auxiliary"}：</strong>{auspiciousPlacements.join(" · ") || "—"}</p><p className="mt-2"><strong>{locale === "zh" ? "六煞" : "Challenging"}：</strong>{challengingPlacements.join(" · ") || "—"}</p>
      </ZiweiStatisticBlock>
    </div>
  )
}

function ZiweiStatisticBlock({ title, value, children }: { title: string; value: string; children: React.ReactNode }) {
  return <section className="min-w-0 px-4 py-4"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-2 text-2xl font-semibold text-primary">{value}</p><div className="mt-3 text-xs leading-5 text-muted-foreground">{children}</div></section>
}

function ZiweiIdentitySummary({ chart, horoscope, horoscopeDate, generatedAt, locale, trustNote, subjectName }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; horoscopeDate: string; generatedAt: string; locale: Locale; trustNote: string; subjectName: string }) {
  return (
    <section className="border-b border-border/60 pb-6" aria-label={locale === "zh" ? "命盘身份摘要" : "Chart identity summary"}>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="kicker">State of I Ching · 易经决策</p><h3 className="mt-3 text-3xl font-semibold">{subjectName || (locale === "zh" ? "匿名命主 · 紫微斗数" : "Anonymous · Zi Wei")}</h3><p className="mt-2 text-sm text-muted-foreground">{chart.chineseDate}</p></div>
        <div className="text-right"><p className="text-xs text-muted-foreground">{locale === "zh" ? "五行局" : "Five-element class"}</p><p className="mt-1 text-2xl font-semibold text-primary">{chart.fiveElementsClass}</p></div>
      </header>
      <div className="mt-6 grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
        <ShareFact label={locale === "zh" ? "农历出生" : "Lunar birth date"} value={chart.lunarDate || chart.chineseDate || "—"} />
        <ShareFact label={locale === "zh" ? "出生时辰" : "Birth time"} value={`${chart.time || "—"}${chart.timeRange ? ` · ${chart.timeRange}` : ""}`} />
        <ShareFact label={locale === "zh" ? "性别" : "Gender"} value={chart.gender || "—"} />
        <ShareFact label={locale === "zh" ? "命主 / 身主" : "Soul / Body rulers"} value={`${chart.soul} / ${chart.body}`} />
        <ShareFact label={locale === "zh" ? "运限日期" : "Horoscope date"} value={`${horoscopeDate} · ${horoscope.lunarDate}`} />
        <ShareFact label={locale === "zh" ? "所选日期大限" : "Selected-date decadal period"} value={`${horoscope.decadal.name} · ${horoscope.decadal.heavenlyStem}${horoscope.decadal.earthlyBranch}`} />
        <ShareFact label={locale === "zh" ? "所选日期流年" : "Selected-date annual period"} value={`${horoscope.yearly.name} · ${horoscope.yearly.heavenlyStem}${horoscope.yearly.earthlyBranch}`} />
        <ShareFact label={locale === "zh" ? "流年四化" : "Annual four transformations"} value={formatTransformations(horoscope, locale)} />
      </div>
      <footer className="mt-6 text-xs leading-5 text-muted-foreground"><p>{locale === "zh" ? "生成于" : "Generated"}: {new Date(generatedAt).toLocaleString(locale === "zh" ? "zh-CN" : "en-US")}</p><p className="mt-1">{trustNote}</p></footer>
    </section>
  )
}

function ZiweiPalaceChart({ chart, horoscope, locale, interactive, selectedPalaceIndex, onSelect }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale; interactive: boolean; selectedPalaceIndex?: number; onSelect?: (index: number) => void }) {
  return (
    <div className={`grid grid-cols-4 grid-rows-4 gap-px overflow-hidden border border-border/60 bg-border/60 ${interactive ? "min-h-[46rem] min-w-[64rem]" : "h-[760px] w-full"}`}>
      {chart.palaces.slice(0, 12).map((palace, index) => {
        const isSelected = selectedPalaceIndex === palace.index
        const isDecadal = horoscope?.decadal.index === palace.index
        const isYearly = horoscope?.yearly.index === palace.index
        if (interactive) {
          return <PalaceButton key={`${palace.name}-${palace.earthlyBranch}`} palace={palace} position={PALACE_POSITIONS[index]} locale={locale} isSelected={isSelected} isDecadal={isDecadal} isYearly={isYearly} onSelect={() => onSelect?.(palace.index)} />
        }
        return (
          <section key={`${palace.name}-${palace.earthlyBranch}`} style={{ gridColumnStart: PALACE_POSITIONS[index][0] + 1, gridRowStart: PALACE_POSITIONS[index][1] + 1 }} className="bg-surface p-3.5">
            <div className="flex items-start justify-between gap-2"><strong className="text-base">{palace.name}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-sm text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></div>
            <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-sm leading-5">{palace.majorStars.length ? palace.majorStars.map((star, starIndex) => <span key={`${star.name}-${starIndex}`} className="font-semibold text-primary">{star.name}{star.brightness ? `(${star.brightness})` : ""}{star.mutagen ? ` · ${star.mutagen}` : ""}</span>) : <span className="text-muted-foreground">{locale === "zh" ? "空宫" : "Empty palace"}</span>}</div>
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{[...palace.minorStars, ...palace.adjectiveStars].map((star) => star.name).join(" · ") || "—"}</p>
            <p className="mt-2 text-xs text-muted-foreground">{isDecadal ? `${locale === "zh" ? "大限" : "Decadal"} · ` : ""}{isYearly ? `${locale === "zh" ? "流年" : "Annual"} · ` : ""}{palace.changsheng12} · {palace.decadal.range[0]}–{palace.decadal.range[1]}</p>
          </section>
        )
      })}
      <div className="col-start-2 col-end-4 row-start-2 row-end-4 flex flex-col items-center justify-center bg-primary/[0.07] p-6 text-center">
        <p className="text-2xl font-semibold">{locale === "zh" ? "十二宫命盘" : "Twelve-palace chart"}</p>
        <p className="mt-4 text-base font-medium">{horoscope.solarDate}</p>
        <p className="mt-1 text-sm text-muted-foreground">{horoscope.lunarDate}</p>
        <p className="mt-5 text-sm text-muted-foreground">{locale === "zh" ? "宫位 · 干支 · 主星 · 四化" : "Palace · stems/branches · major stars · transformations"}</p>
      </div>
    </div>
  )
}

function PalaceButton({ palace, position, locale, isSelected, isDecadal, isYearly, onSelect }: { palace: IFunctionalPalace; position: readonly [number, number]; locale: Locale; isSelected: boolean; isDecadal: boolean; isYearly: boolean; onSelect: () => void }) {
  const palaceLabel = `${palace.name} ${palace.heavenlyStem}${palace.earthlyBranch}${isDecadal ? `, ${locale === "zh" ? "大限" : "Decadal period"}` : ""}${isYearly ? `, ${locale === "zh" ? "流年" : "Annual period"}` : ""}`
  return (
    <button
      type="button"
      style={{ gridColumnStart: position[0] + 1, gridRowStart: position[1] + 1 }}
      aria-label={palaceLabel}
      aria-pressed={isSelected}
      onClick={onSelect}
      className={`min-w-0 p-3.5 text-left transition focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${isSelected ? "bg-primary/12 shadow-[inset_0_0_0_2px_var(--primary)]" : "bg-surface hover:bg-primary/[0.055]"}`}
    >
      <span className="flex items-start justify-between gap-2"><strong className="text-base">{palace.name}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-sm text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></span>
      <span className="mt-2 flex flex-wrap gap-1">
        {isDecadal ? <span className="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-semibold">{locale === "zh" ? "大限" : "Decadal"}</span> : null}
        {isYearly ? <span className="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-semibold">{locale === "zh" ? "流年" : "Annual"}</span> : null}
      </span>
      <span className="mt-2 flex flex-wrap gap-x-2 gap-y-1">{palace.majorStars.length ? palace.majorStars.map((star, index) => <span key={`${star.name}-${index}`} className="text-sm font-semibold text-primary">{star.name}{star.brightness ? `(${star.brightness})` : ""}{star.mutagen ? ` · ${star.mutagen}` : ""}</span>) : <span className="text-sm text-muted-foreground">{locale === "zh" ? "空宫" : "Empty palace"}</span>}</span>
      <span className="mt-2 line-clamp-2 block text-xs leading-5 text-muted-foreground">{[...palace.minorStars, ...palace.adjectiveStars].map((star) => star.name).join(" · ") || "—"}</span>
      <span className="mt-2 block text-xs text-muted-foreground">{palace.changsheng12} · {palace.decadal.range[0]}–{palace.decadal.range[1]}</span>
    </button>
  )
}

function SelectedPalaceDetail({ selectedPalace, locale }: { selectedPalace: IFunctionalPalace; locale: Locale }) {
  return (
    <section aria-labelledby="selected-palace-title" className="border-t border-border/60 pt-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{locale === "zh" ? "所选宫位" : "Selected palace"}</p><h2 id="selected-palace-title" className="mt-1 text-xl font-semibold">{selectedPalace.name}{selectedPalace.isBodyPalace ? ` · ${locale === "zh" ? "身宫" : "Body palace"}` : ""}</h2></div>
        <p className="text-sm font-semibold">{selectedPalace.heavenlyStem}{selectedPalace.earthlyBranch}</p>
      </div>
      <div className="mt-4 grid divide-y divide-border/60 md:grid-cols-3 md:divide-x md:divide-y-0">
        <StarGroup title={locale === "zh" ? "主星" : "Major stars"} stars={selectedPalace.majorStars} locale={locale} emptyLabel={locale === "zh" ? "空宫（无主星）" : "Empty palace (no major stars)"} />
        <StarGroup title={locale === "zh" ? "辅星" : "Minor stars"} stars={selectedPalace.minorStars} locale={locale} />
        <StarGroup title={locale === "zh" ? "杂耀" : "Adjective stars"} stars={selectedPalace.adjectiveStars} locale={locale} />
      </div>
      <div className="mt-2 grid gap-2 border-t border-border/60 pt-4 text-xs text-muted-foreground sm:grid-cols-2">
        <p>{locale === "zh" ? "长生" : "Changsheng"}: {selectedPalace.changsheng12}</p>
        <p>{locale === "zh" ? "大限年龄" : "Decadal ages"}: {selectedPalace.decadal.range[0]}–{selectedPalace.decadal.range[1]}</p>
      </div>
    </section>
  )
}

function StarGroup({ title, stars, locale, emptyLabel }: { title: string; stars: IFunctionalPalace["majorStars"]; locale: Locale; emptyLabel?: string }) {
  return (
    <section className="py-4 md:px-4 md:first:pl-0 md:last:pr-0">
      <h3 className="text-sm font-semibold">{title}</h3>
      {stars.length ? <ul className="mt-2 divide-y divide-border/50">{stars.map((star, index) => <li key={`${star.name}-${index}`} className="py-2 text-sm"><span className="font-medium">{star.name}</span><span className="ml-2 text-xs text-muted-foreground">{star.mutagen ? `${locale === "zh" ? "化" : "Transformation"} ${star.mutagen}` : ""}{star.mutagen && star.brightness ? " · " : ""}{star.brightness ? `${locale === "zh" ? "亮度" : "Brightness"} ${star.brightness}` : ""}</span></li>)}</ul> : <p className="mt-2 text-xs text-muted-foreground">{emptyLabel || (locale === "zh" ? "无" : "None")}</p>}
    </section>
  )
}

function ShareFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value}</p></div>
}
