"use client"

import { useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react"
import { cn } from "@/lib/utils"

export type LifeKlineLocale = "en" | "zh"
export type LifeKlineKey = "overall" | "career" | "wealth" | "relationship" | "health" | "rhythm" | string
type CanonicalLifeKlineKey = "career" | "wealth" | "relationship" | "rhythm"
type LifeKlineViewMode = "trend" | "candles"

export interface LifeKlineDriver {
  id?: string
  label: string
  kind?: string
  role?: string
  layer?: string
  delta?: number
  activity?: number
}

export interface LifeKlineMonthPoint {
  index: number
  label: string
  ganzhi: string
  value: number
  delta: number
  drivers: Array<string | LifeKlineDriver>
}

export interface LifeKlinePoint {
  year: number
  open: number
  close: number
  high: number
  low: number
  volume: number
  ma3: number | null
  ma5: number | null
  ma10: number | null
  months: LifeKlineMonthPoint[]
}

export interface LifeKlineThemeSeries {
  key: LifeKlineKey
  label: string
  color: string
  points: LifeKlinePoint[]
}

export interface LifeKlinePeriodBand {
  label: string
  start_year: number
  end_year: number
}

export interface LifeKlineStage {
  key: string
  label: string
  year: number
  /** @deprecated Old snapshots used `score`; it is a relative activity value, not a life score. */
  score?: number
  value?: number
  relative_index?: number
  theme: string
  summary: string
  drivers?: Array<string | LifeKlineDriver>
}

export interface LifeKlineBaselineEntry {
  raw_value?: number
  value?: number
}

export interface LifeKlineBaseline {
  raw_value?: number
  value?: number
  normalized_value?: number
  scope?: string
  method?: string
  start_year?: number
  end_year?: number
  values_are_relative?: boolean
  by_series?: Record<string, number | LifeKlineBaselineEntry>
  series?: Record<string, number | LifeKlineBaselineEntry>
}

export interface LifeKlineSeries {
  default_window: {
    start_year: number
    end_year: number
  }
  series: LifeKlineThemeSeries[]
  period_bands: LifeKlinePeriodBand[]
  stages: LifeKlineStage[]
  method: string
  baseline?: LifeKlineBaseline
}

export interface LifeKlineChartProps {
  lifeKline: LifeKlineSeries
  locale?: LifeKlineLocale
  currentYear?: number
  initialSeriesKey?: LifeKlineKey
  fullLifeLoading?: boolean
  onRequestFullLife?: () => boolean | Promise<boolean>
  onSeriesChange?: (key: LifeKlineKey) => void
  onYearChange?: (year: number) => void
  staticMode?: boolean
  className?: string
}

interface TurningPoint {
  year: number
  kind: "peak" | "trough"
  value: number
  prominence: number
}

const WINDOW_SIZE = 10
const CHART_HEIGHT = 432
const PRICE_TOP = 42
const PRICE_BOTTOM = 294
const VOLUME_TOP = 334
const VOLUME_BOTTOM = 394
const LEFT_GUTTER = 54
const RIGHT_GUTTER = 24

function formatNumber(value: number, locale: LifeKlineLocale, maximumFractionDigits = 1) {
  return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", { maximumFractionDigits }).format(value)
}

function average(values: number[]) {
  if (!values.length) return 100
  return values.reduce((total, value) => total + value, 0) / values.length
}

function legacyPersonalBaseline(points: LifeKlinePoint[]) {
  const monthValues = points.flatMap((point) => point.months.map((month) => month.value))
    .filter((value) => Number.isFinite(value) && value > 0)
  const closes = points.map((point) => point.close).filter((value) => Number.isFinite(value) && value > 0)
  return Math.max(0.001, average(monthValues.length ? monthValues : closes))
}

function baselineEntryValue(entry: number | LifeKlineBaselineEntry | undefined) {
  if (typeof entry === "number") return Number.isFinite(entry) && entry > 0 ? entry : null
  if (!entry) return null
  const candidate = entry.raw_value ?? entry.value
  return typeof candidate === "number" && Number.isFinite(candidate) && candidate > 0 ? candidate : null
}

function personalBaseline(lifeKline: LifeKlineSeries, series: LifeKlineThemeSeries) {
  const metadata = lifeKline.baseline
  if (metadata?.values_are_relative || (metadata?.normalized_value && metadata.series)) return metadata.normalized_value || 100
  const canonicalKey = series.key === "health" ? "rhythm" : series.key
  const entry = metadata?.by_series?.[series.key]
    ?? metadata?.by_series?.[canonicalKey]
    ?? metadata?.series?.[series.key]
    ?? metadata?.series?.[canonicalKey]
  return baselineEntryValue(entry)
    ?? baselineEntryValue(metadata?.raw_value ?? metadata?.value)
    ?? legacyPersonalBaseline(series.points)
}

function usesServerRelativeValues(lifeKline: LifeKlineSeries) {
  const metadata = lifeKline.baseline
  return Boolean(metadata?.values_are_relative || (metadata?.normalized_value && metadata.series))
}

function toPersonalIndex(value: number, baseline: number) {
  return (value / baseline) * 100
}

function normalizePoint(point: LifeKlinePoint, baseline: number, valuesAreRelative = false): LifeKlinePoint {
  if (valuesAreRelative) return point
  return {
    ...point,
    open: toPersonalIndex(point.open, baseline),
    close: toPersonalIndex(point.close, baseline),
    high: toPersonalIndex(point.high, baseline),
    low: toPersonalIndex(point.low, baseline),
    ma3: point.ma3 == null ? null : toPersonalIndex(point.ma3, baseline),
    ma5: point.ma5 == null ? null : toPersonalIndex(point.ma5, baseline),
    ma10: point.ma10 == null ? null : toPersonalIndex(point.ma10, baseline),
    months: point.months.map((month) => ({
      ...month,
      value: toPersonalIndex(month.value, baseline),
      delta: (month.delta / baseline) * 100,
    })),
  }
}

function driverLabel(driver: string | LifeKlineDriver) {
  return typeof driver === "string" ? driver : driver.label
}

function canonicalSeriesKey(key: LifeKlineKey): CanonicalLifeKlineKey | null {
  if (key === "health" || key === "rhythm") return "rhythm"
  if (key === "career" || key === "wealth" || key === "relationship") return key
  return null
}

function relativeState(value: number, locale: LifeKlineLocale) {
  if (locale === "zh") {
    if (value >= 110) return "高活跃"
    if (value >= 103) return "较活跃"
    if (value <= 92) return "低活跃"
    return "接近常态"
  }
  if (value >= 110) return "High activity"
  if (value >= 103) return "Above-baseline activity"
  if (value <= 92) return "Low activity"
  return "Near baseline"
}

function relativeSummary(value: number, locale: LifeKlineLocale) {
  const state = relativeState(value, locale)
  if (locale === "zh") {
    if (state === "高活跃") return "这一主题出现的结构信号明显多于个人长期常态。"
    if (state === "较活跃") return "这一主题出现的结构信号略多于个人长期常态。"
    if (state === "低活跃") return "这一主题出现的结构信号少于个人长期常态。"
    return "这一主题的结构信号密度接近个人长期常态。"
  }
  if (state === "High activity") return "This theme has substantially more structural signals than your long-term baseline."
  if (state === "Above-baseline activity") return "This theme has somewhat more structural signals than your long-term baseline."
  if (state === "Low activity") return "This theme has fewer structural signals than your long-term baseline."
  return "This theme's structural-signal density is close to your long-term baseline."
}

function displaySeriesLabel(series: LifeKlineThemeSeries, locale: LifeKlineLocale) {
  if (series.key === "health") return locale === "zh" ? "身心节奏" : "Body rhythm"
  return series.label
}

function displayStageText(value: string, locale: LifeKlineLocale) {
  return locale === "zh" ? value.replaceAll("健康", "身心节奏").replaceAll("运势", "走势") : value.replaceAll(/health/gi, "body rhythm")
}

function pathForMovingAverage(
  points: LifeKlinePoint[],
  key: "ma3" | "ma5" | "ma10",
  xAt: (index: number) => number,
  yAt: (value: number) => number,
) {
  let path = ""
  let drawing = false
  points.forEach((point, index) => {
    const value = point[key]
    if (value == null || !Number.isFinite(value)) {
      drawing = false
      return
    }
    path += `${drawing ? " L" : "M"} ${xAt(index).toFixed(2)} ${yAt(value).toFixed(2)}`
    drawing = true
  })
  return path
}

function pathForValues(
  points: LifeKlinePoint[],
  xAt: (index: number) => number,
  yAt: (value: number) => number,
) {
  return points.map((point, index) => `${index ? "L" : "M"} ${xAt(index).toFixed(2)} ${yAt(point.close).toFixed(2)}`).join(" ")
}

function stageValue(stage: LifeKlineStage) {
  const value = stage.relative_index ?? stage.value ?? stage.score
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function stageDriverLabels(stage: LifeKlineStage) {
  return (stage.drivers ?? []).map(driverLabel).filter(Boolean).slice(0, 3)
}

function findTurningPoints(points: LifeKlinePoint[]) {
  const candidates: TurningPoint[] = []
  for (let index = 1; index < points.length - 1; index += 1) {
    const previous = points[index - 1].close
    const current = points[index].close
    const next = points[index + 1].close
    const neighborAverage = (previous + next) / 2
    if (current > previous && current > next) {
      candidates.push({ year: points[index].year, kind: "peak", value: points[index].high, prominence: current - neighborAverage })
    } else if (current < previous && current < next) {
      candidates.push({ year: points[index].year, kind: "trough", value: points[index].low, prominence: neighborAverage - current })
    }
  }

  const strongest = (kind: TurningPoint["kind"]) => candidates
    .filter((point) => point.kind === kind)
    .sort((left, right) => right.prominence - left.prominence || left.year - right.year)
    .slice(0, 3)

  return [...strongest("peak"), ...strongest("trough")]
}

function defaultStartIndex(points: LifeKlinePoint[], startYear: number) {
  const index = points.findIndex((point) => point.year >= startYear)
  if (index < 0) return Math.max(0, points.length - WINDOW_SIZE)
  return Math.min(index, Math.max(0, points.length - WINDOW_SIZE))
}

function preferredPoint(points: LifeKlinePoint[], startIndex: number, currentYear?: number) {
  const current = currentYear == null ? undefined : points.find((point) => point.year === currentYear)
  return current ?? points[startIndex] ?? points[0]
}

export function LifeKlineChart({
  lifeKline,
  locale = "zh",
  currentYear,
  initialSeriesKey = "career",
  fullLifeLoading = false,
  onRequestFullLife,
  onSeriesChange,
  onYearChange,
  staticMode = false,
  className,
}: LifeKlineChartProps) {
  const id = useId()
  const titleId = `${id}-title`
  const descriptionId = `${id}-description`
  const interactionHintId = `${id}-interaction-hint`
  const panelId = `${id}-panel`
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])
  const consumerSeries = (["career", "wealth", "relationship", "rhythm"] as const).flatMap((key) => {
    const series = lifeKline.series.find((item) => canonicalSeriesKey(item.key) === key)
    return series ? [series] : []
  })
  const requestedInitialKey = canonicalSeriesKey(initialSeriesKey) ?? "career"
  const initialSeries = consumerSeries.find((series) => canonicalSeriesKey(series.key) === requestedInitialKey) ?? consumerSeries[0]
  const initialStart = initialSeries ? defaultStartIndex(initialSeries.points, lifeKline.default_window.start_year) : 0
  const [activeKey, setActiveKey] = useState<LifeKlineKey>(initialSeries?.key ?? initialSeriesKey)
  const [windowStart, setWindowStart] = useState(initialStart)
  const [showFullLife, setShowFullLife] = useState(false)
  const [viewMode, setViewMode] = useState<LifeKlineViewMode>("trend")
  const [selectedYear, setSelectedYear] = useState<number | null>(() => preferredPoint(initialSeries?.points ?? [], initialStart, currentYear)?.year ?? null)
  const [hoveredYear, setHoveredYear] = useState<number | null>(null)

  const activeSeries = consumerSeries.find((series) => series.key === activeKey)
    ?? consumerSeries.find((series) => canonicalSeriesKey(series.key) === canonicalSeriesKey(activeKey))
    ?? consumerSeries[0]
  if (!activeSeries) {
    return (
      <section className={cn("min-w-0 border-y border-border/60 py-7", className)} aria-label={locale === "zh" ? "人生 K 线" : "Life K-line"}>
        <h2 className="text-2xl font-semibold">{locale === "zh" ? "人生 K 线" : "Life K-line"}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "当前命盘尚无可展示的主题活跃序列。" : "No theme-activity series is available for this chart."}</p>
      </section>
    )
  }

  const baseline = personalBaseline(lifeKline, activeSeries)
  const serverRelativeValues = usesServerRelativeValues(lifeKline)
  const allPoints = activeSeries.points.map((point) => normalizePoint(point, baseline, serverRelativeValues))
  const activeSeriesLabel = displaySeriesLabel(activeSeries, locale)
  const safeWindowStart = Math.min(Math.max(0, windowStart), Math.max(0, allPoints.length - WINDOW_SIZE))
  const visiblePoints = showFullLife ? allPoints : allPoints.slice(safeWindowStart, safeWindowStart + WINDOW_SIZE)
  const selectedPoint = allPoints.find((point) => point.year === selectedYear) ?? visiblePoints[0] ?? allPoints[0]
  const selectedVisibleIndex = visiblePoints.findIndex((point) => point.year === selectedPoint?.year)
  const hoveredVisibleIndex = visiblePoints.findIndex((point) => point.year === hoveredYear)
  const focusIndex = hoveredVisibleIndex >= 0 ? hoveredVisibleIndex : selectedVisibleIndex
  const focusPoint = focusIndex >= 0 ? visiblePoints[focusIndex] : undefined
  const loadedStartYear = allPoints[0]?.year
  const loadedEndYear = allPoints.at(-1)?.year
  const horizonStartYear = lifeKline.baseline?.start_year
  const horizonEndYear = lifeKline.baseline?.end_year
  const hasKnownFullHorizon = horizonStartYear != null && horizonEndYear != null
  const hasFullLifeData = hasKnownFullHorizon
    ? loadedStartYear != null
      && loadedEndYear != null
      && loadedStartYear <= horizonStartYear
      && loadedEndYear >= horizonEndYear
    : allPoints.some((point) => point.year < lifeKline.default_window.start_year || point.year > lifeKline.default_window.end_year)
  const canShowFullLife = hasFullLifeData || Boolean(onRequestFullLife)
  const windowEnd = Math.min(allPoints.length, safeWindowStart + WINDOW_SIZE)
  const canMovePrevious = !showFullLife && safeWindowStart > 0
  const canMoveNext = !showFullLife && windowEnd < allPoints.length
  const futureStages = lifeKline.stages.filter((stage) => currentYear == null || stage.year >= currentYear)
  const visibleStages = futureStages.slice(0, 3)
  const turningPoints = findTurningPoints(allPoints)
  const turningByYear = new Map(turningPoints.map((point) => [point.year, point]))

  const chartWidth = Math.max(720, LEFT_GUTTER + RIGHT_GUTTER + visiblePoints.length * 58)
  const plotWidth = chartWidth - LEFT_GUTTER - RIGHT_GUTTER
  const slotWidth = visiblePoints.length ? plotWidth / visiblePoints.length : plotWidth
  const candleWidth = Math.min(24, Math.max(8, slotWidth * 0.44))
  const xAt = (index: number) => LEFT_GUTTER + slotWidth * (index + 0.5)
  const plottedValues = [
    100,
    ...visiblePoints.flatMap((point) => (
      viewMode === "trend"
        ? [point.close]
        : [point.low, point.high, point.ma3, point.ma5, point.ma10]
    ).filter((value): value is number => value != null && Number.isFinite(value))),
  ]
  const dataMinimum = plottedValues.length ? Math.min(...plottedValues) : 0
  const dataMaximum = plottedValues.length ? Math.max(...plottedValues) : 100
  const rawRange = Math.max(1, dataMaximum - dataMinimum)
  const valueMinimum = dataMinimum - rawRange * 0.08
  const valueMaximum = dataMaximum + rawRange * 0.08
  const valueRange = valueMaximum - valueMinimum
  const yAt = (value: number) => PRICE_BOTTOM - ((value - valueMinimum) / valueRange) * (PRICE_BOTTOM - PRICE_TOP)
  const maximumVolume = Math.max(1, ...visiblePoints.map((point) => point.volume))
  const volumeY = (value: number) => VOLUME_BOTTOM - (Math.max(0, value) / maximumVolume) * (VOLUME_BOTTOM - VOLUME_TOP)
  const axisTicks = Array.from({ length: 5 }, (_, index) => valueMaximum - (valueRange * index) / 4)
  const ma3Path = pathForMovingAverage(visiblePoints, "ma3", xAt, yAt)
  const ma5Path = pathForMovingAverage(visiblePoints, "ma5", xAt, yAt)
  const ma10Path = pathForMovingAverage(visiblePoints, "ma10", xAt, yAt)
  const trendPath = pathForValues(visiblePoints, xAt, yAt)
  const trendAreaPath = visiblePoints.length
    ? `${trendPath} L ${xAt(visiblePoints.length - 1).toFixed(2)} ${PRICE_BOTTOM} L ${xAt(0).toFixed(2)} ${PRICE_BOTTOM} Z`
    : ""
  const displayChartHeight = viewMode === "trend" ? 336 : CHART_HEIGHT
  const activeColor = activeSeries.color || "hsl(var(--primary))"
  const selectedDescription = selectedPoint
    ? `${selectedPoint.year}, ${locale === "zh" ? "相对活跃指数" : "relative activity index"}, ${locale === "zh" ? "年初" : "open"} ${formatNumber(selectedPoint.open, locale)}, ${locale === "zh" ? "最高" : "high"} ${formatNumber(selectedPoint.high, locale)}, ${locale === "zh" ? "最低" : "low"} ${formatNumber(selectedPoint.low, locale)}, ${locale === "zh" ? "年末" : "close"} ${formatNumber(selectedPoint.close, locale)}`
    : ""

  function selectSeries(series: LifeKlineThemeSeries) {
    const nextStart = defaultStartIndex(series.points, lifeKline.default_window.start_year)
    const nextPoint = preferredPoint(series.points, nextStart, currentYear)
    setActiveKey(series.key)
    setWindowStart(nextStart)
    setSelectedYear(nextPoint?.year ?? null)
    setHoveredYear(null)
    onSeriesChange?.(series.key)
    if (nextPoint) onYearChange?.(nextPoint.year)
  }

  function selectPoint(point: LifeKlinePoint) {
    setSelectedYear(point.year)
    onYearChange?.(point.year)
  }

  function moveWindow(direction: -1 | 1) {
    const nextStart = Math.min(Math.max(0, safeWindowStart + direction * WINDOW_SIZE), Math.max(0, allPoints.length - WINDOW_SIZE))
    const nextPoint = allPoints[nextStart]
    setWindowStart(nextStart)
    if (nextPoint) selectPoint(nextPoint)
  }

  async function selectWindowMode(fullLife: boolean) {
    if (fullLife && !hasFullLifeData) {
      const loaded = await onRequestFullLife?.()
      setShowFullLife(Boolean(loaded))
      setHoveredYear(null)
      return
    }
    setShowFullLife(fullLife)
    setHoveredYear(null)
  }

  function handleTabKeyDown(event: ReactKeyboardEvent<HTMLButtonElement>, index: number) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return
    event.preventDefault()
    const count = consumerSeries.length
    if (!count) return
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? count - 1
        : (index + (event.key === "ArrowRight" ? 1 : -1) + count) % count
    const nextSeries = consumerSeries[nextIndex]
    selectSeries(nextSeries)
    tabRefs.current[nextIndex]?.focus()
  }

  function handleChartKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key) || !visiblePoints.length) return
    event.preventDefault()
    const currentIndex = selectedVisibleIndex >= 0 ? selectedVisibleIndex : 0
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? visiblePoints.length - 1
        : Math.min(visiblePoints.length - 1, Math.max(0, currentIndex + (event.key === "ArrowRight" ? 1 : -1)))
    selectPoint(visiblePoints[nextIndex])
  }

  return (
    <section className={cn("min-w-0 max-w-full overflow-hidden rounded-3xl border border-border/65 bg-surface/95 shadow-[var(--surface-shadow-soft)]", className)} aria-labelledby={titleId}>
      <header className="border-b border-border/60 px-4 py-5 sm:px-6 sm:py-6">
        <div className="flex min-w-0 flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="kicker">{locale === "zh" ? "未来活跃节奏" : "YOUR ACTIVITY TIMELINE"}</p>
            <h2 id={titleId} className="mt-2 text-2xl font-semibold">{locale === "zh" ? "人生 K 线" : "Life K-line"}</h2>
            <p id={descriptionId} className="mt-2 max-w-3xl text-base leading-7 text-muted-foreground">{locale === "zh" ? "以你的长期主题活跃常态为 100，展示每一年和每个月的结构信号密度变化。" : "Your long-term theme-activity baseline is set to 100, showing changes in structural-signal density by year and month."}</p>
          </div>
          {staticMode ? <p className="max-w-xs shrink-0 text-xs leading-5 text-muted-foreground">{locale === "zh" ? "100 是个人长期活跃常态；高于 100 表示结构信号更密集，低于 100 表示结构信号更少。" : "100 is the personal activity baseline; values above it mean denser signals and values below it mean fewer signals."}</p> : <details className="shrink-0 text-xs text-muted-foreground">
            <summary className="min-h-11 cursor-pointer rounded-lg px-2 py-3 font-semibold text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{locale === "zh" ? "K 线怎么看" : "How to read it"}</summary>
            <p className="max-w-xs break-words border-t border-border/55 pt-2 leading-5">{locale === "zh" ? "100 是你自己的长期活跃常态。每根年线汇总十二个月；高于 100 表示结构信号更密集，低于 100 表示结构信号更少。" : "100 is your own long-term activity baseline. Each candle summarizes twelve months; above 100 means denser structural signals, while below 100 means fewer signals."}</p>
          </details>}
        </div>

        {staticMode ? <div className="mt-5 inline-flex items-center gap-2 rounded-xl bg-muted/60 px-3 py-2 text-sm font-semibold"><span aria-hidden="true" className="size-2 rounded-full" style={{ backgroundColor: activeSeries.color }} />{activeSeriesLabel}</div> : <div className="mt-5 max-w-full overflow-x-auto pb-1 custom-scrollbar">
          <div role="tablist" aria-label={locale === "zh" ? "人生 K 线主题" : "Life K-line theme"} className="inline-flex min-w-max rounded-xl bg-muted/60 p-1">
            {consumerSeries.map((series, index) => {
              const selected = series.key === activeSeries.key
              return (
                <button
                  key={series.key}
                  ref={(element) => { tabRefs.current[index] = element }}
                  id={`${id}-tab-${series.key}`}
                  type="button"
                  role="tab"
                  aria-selected={selected}
                  aria-controls={panelId}
                  tabIndex={selected ? 0 : -1}
                  onClick={() => selectSeries(series)}
                  onKeyDown={(event) => handleTabKeyDown(event, index)}
                  className={cn("inline-flex min-h-11 min-w-20 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", selected ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}
                >
                  <span aria-hidden="true" className="size-2 rounded-full" style={{ backgroundColor: series.color }} />
                  {displaySeriesLabel(series, locale)}
                </button>
              )
            })}
          </div>
        </div>}
      </header>

      <div id={panelId} role={staticMode ? undefined : "tabpanel"} aria-labelledby={staticMode ? undefined : `${id}-tab-${activeSeries.key}`} className="min-w-0 px-3 py-5 sm:px-5">
        {visibleStages.length ? (
          <section className="mb-5 min-w-0 rounded-2xl border border-border/60 bg-background/55 p-4 sm:p-5" aria-labelledby={`${id}-stages`}>
            <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
              <div>
                <p className="kicker">{locale === "zh" ? "未来三个活跃窗口" : "THREE ACTIVITY WINDOWS"}</p>
                <h3 id={`${id}-stages`} className="mt-2 text-xl font-semibold">{locale === "zh" ? "相对个人常态差异较大的阶段" : "Periods furthest from your activity baseline"}</h3>
              </div>
              <span className="text-xs text-muted-foreground">{locale === "zh" ? "全盘窗口 · 个人常态 100" : "All themes · baseline 100"}</span>
            </div>
            <ol className="mt-4 grid min-w-0 gap-px overflow-hidden rounded-2xl border border-border/60 bg-border/60 md:grid-cols-3">
              {visibleStages.map((stage, index) => {
                const rawValue = stageValue(stage)
                const relativeIndex = stage.relative_index != null
                  ? stage.relative_index
                  : rawValue == null
                    ? 100
                    : serverRelativeValues
                      ? rawValue
                      : toPersonalIndex(rawValue, baseline)
                const drivers = stageDriverLabels(stage)
                return (
                  <li key={`${stage.key}-${stage.year}-${stage.label}`} className="min-w-0 bg-surface px-4 py-5">
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-xs font-semibold tabular-nums text-primary">0{index + 1}</span>
                      <p className="text-right text-[0.7rem] font-semibold text-muted-foreground"><span className="block">{relativeState(relativeIndex, locale)}</span><strong className="text-2xl tabular-nums text-primary">{formatNumber(relativeIndex, locale)}</strong></p>
                    </div>
                    <p className="mt-2 text-xs font-semibold text-muted-foreground">{stage.year} · {displayStageText(stage.theme, locale)}</p>
                    <h4 className="mt-1 font-semibold leading-6">{displayStageText(stage.label, locale)}</h4>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{stage.summary || relativeSummary(relativeIndex, locale)}</p>
                    {drivers.length ? <p className="mt-3 border-t border-border/50 pt-3 text-xs leading-5 text-foreground/75">{drivers.join(" · ")}</p> : null}
                  </li>
                )
              })}
            </ol>
          </section>
        ) : null}

        {staticMode ? <p className="px-1 text-xs font-semibold tabular-nums text-muted-foreground">{visiblePoints.length ? `${visiblePoints[0].year}–${visiblePoints[visiblePoints.length - 1].year}` : "—"}</p> : <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 px-1">
          <div className="inline-flex rounded-xl border border-border/60 bg-background p-1" role="group" aria-label={locale === "zh" ? "K 线时间范围" : "K-line time range"}>
            <button type="button" aria-pressed={!showFullLife} onClick={() => void selectWindowMode(false)} className={cn("min-h-10 rounded-lg px-3 py-2 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", !showFullLife ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{locale === "zh" ? "十年窗口" : "10-year window"}</button>
            {canShowFullLife ? <button type="button" aria-pressed={showFullLife} disabled={fullLifeLoading} onClick={() => void selectWindowMode(true)} className={cn("min-h-10 rounded-lg px-3 py-2 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50", showFullLife ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{fullLifeLoading ? (locale === "zh" ? "载入中…" : "Loading…") : (locale === "zh" ? "全人生" : "Full life")}</button> : null}
          </div>
          <div className="inline-flex rounded-xl border border-border/60 bg-background p-1" role="group" aria-label={locale === "zh" ? "走势显示方式" : "Trend display mode"}>
            <button type="button" aria-pressed={viewMode === "trend"} onClick={() => setViewMode("trend")} className={cn("min-h-10 rounded-lg px-3 py-2 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", viewMode === "trend" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{locale === "zh" ? "简明趋势" : "Simple trend"}</button>
            <button type="button" aria-pressed={viewMode === "candles"} onClick={() => setViewMode("candles")} className={cn("min-h-10 rounded-lg px-3 py-2 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", viewMode === "candles" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}>{locale === "zh" ? "专业 K 线" : "Pro candles"}</button>
          </div>
          {!showFullLife ? (
            <div className="flex items-center gap-2">
              <button type="button" disabled={!canMovePrevious} onClick={() => moveWindow(-1)} aria-label={locale === "zh" ? "查看前十年" : "Show previous ten years"} className="inline-flex size-11 items-center justify-center rounded-xl border border-border/60 text-lg transition hover:border-primary/45 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-35"><span aria-hidden="true">←</span></button>
              <p className="min-w-24 text-center text-xs font-semibold tabular-nums text-muted-foreground">{visiblePoints.length ? `${visiblePoints[0].year}–${visiblePoints[visiblePoints.length - 1].year}` : "—"}</p>
              <button type="button" disabled={!canMoveNext} onClick={() => moveWindow(1)} aria-label={locale === "zh" ? "查看后十年" : "Show next ten years"} className="inline-flex size-11 items-center justify-center rounded-xl border border-border/60 text-lg transition hover:border-primary/45 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-35"><span aria-hidden="true">→</span></button>
            </div>
          ) : <p className="text-xs font-semibold tabular-nums text-muted-foreground">{visiblePoints.length ? `${visiblePoints[0].year}–${visiblePoints[visiblePoints.length - 1].year}` : "—"}</p>}
        </div>}

        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 px-1 text-xs text-muted-foreground" aria-label={locale === "zh" ? "图例" : "Legend"}>
          {viewMode === "trend" ? <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-5" style={{ backgroundColor: activeColor }} />{locale === "zh" ? "年度活跃趋势" : "Annual activity trend"}</span> : <>
            <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-5" style={{ backgroundColor: activeColor }} />MA3</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-5 bg-[hsl(var(--imperial-metal))]" />MA5</span>
            <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-5 bg-muted-foreground" />MA10</span>
          </>}
          <span className="inline-flex items-center gap-1.5"><span className="w-5 border-t border-dashed border-foreground/55" />{locale === "zh" ? "个人常态 100" : "Personal baseline 100"}</span>
          {viewMode === "candles" ? <><span>{locale === "zh" ? "朱红 = 年末活跃度高于年初" : "Red = year-end activity above year-open"}</span><span>{locale === "zh" ? "青绿 = 年末活跃度低于年初" : "Green = year-end activity below year-open"}</span></> : null}
        </div>

        {!staticMode ? <p id={interactionHintId} className="mt-3 px-1 text-xs text-muted-foreground">{locale === "zh" ? `点击或轻触${viewMode === "trend" ? "年份节点" : "年线"}查看详情；聚焦图表后可用左右方向键切换年份。` : `Click or tap a ${viewMode === "trend" ? "year point" : "candle"} for details. Focus the chart and use Left/Right Arrow to change year.`}</p> : null}

        <div
          tabIndex={staticMode ? undefined : 0}
          role="group"
          aria-label={`${activeSeriesLabel} ${locale === "zh" ? (viewMode === "trend" ? "个人相对趋势图" : "个人相对年线图") : (viewMode === "trend" ? "personal relative trend chart" : "personal relative annual candlestick chart")}`}
          aria-describedby={staticMode ? descriptionId : `${descriptionId} ${interactionHintId}`}
          onKeyDown={staticMode ? undefined : handleChartKeyDown}
          onPointerLeave={staticMode ? undefined : () => setHoveredYear(null)}
          className="custom-scrollbar mt-3 min-w-0 max-w-full overflow-x-auto rounded-2xl border border-border/55 bg-background/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <svg role="img" aria-labelledby={`${titleId} ${descriptionId}`} viewBox={`0 0 ${chartWidth} ${displayChartHeight}`} className="block h-auto w-full max-w-none" style={{ minWidth: `${chartWidth}px` }}>
            <rect width={chartWidth} height={displayChartHeight} fill="transparent" />

            {lifeKline.period_bands.map((band, bandIndex) => {
              const firstIndex = visiblePoints.findIndex((point) => point.year >= band.start_year && point.year <= band.end_year)
              let lastIndex = -1
              visiblePoints.forEach((point, pointIndex) => {
                if (point.year >= band.start_year && point.year <= band.end_year) lastIndex = pointIndex
              })
              if (firstIndex < 0 || lastIndex < firstIndex) return null
              const x = LEFT_GUTTER + firstIndex * slotWidth
              const width = (lastIndex - firstIndex + 1) * slotWidth
              return (
                <g key={`${band.label}-${band.start_year}`} aria-hidden="true">
                  <rect x={x} y={PRICE_TOP - 18} width={width} height={VOLUME_BOTTOM - PRICE_TOP + 18} fill={activeColor} opacity={bandIndex % 2 === 0 ? 0.045 : 0.075} />
                  {width >= 64 ? <text x={x + 5} y={PRICE_TOP - 5} fill="hsl(var(--muted-foreground))" fontSize="10">{band.label}</text> : null}
                </g>
              )
            })}

            {axisTicks.map((tick) => {
              const y = yAt(tick)
              return <g key={tick} aria-hidden="true"><line x1={LEFT_GUTTER} x2={chartWidth - RIGHT_GUTTER} y1={y} y2={y} stroke="hsl(var(--border))" strokeOpacity="0.55" strokeDasharray="3 5" /><text x={LEFT_GUTTER - 8} y={y + 3.5} textAnchor="end" fill="hsl(var(--muted-foreground))" fontSize="10">{formatNumber(tick, locale, 0)}</text></g>
            })}
            {100 >= valueMinimum && 100 <= valueMaximum ? <g aria-hidden="true"><line x1={LEFT_GUTTER} x2={chartWidth - RIGHT_GUTTER} y1={yAt(100)} y2={yAt(100)} stroke="hsl(var(--foreground))" strokeOpacity="0.42" strokeDasharray="6 5" /><text x={chartWidth - RIGHT_GUTTER} y={yAt(100) - 5} textAnchor="end" fill="hsl(var(--muted-foreground))" fontSize="9">{locale === "zh" ? "个人常态 100" : "BASELINE 100"}</text></g> : null}
            {viewMode === "trend" ? <>
              {trendAreaPath ? <path d={trendAreaPath} fill={activeColor} opacity="0.09" pointerEvents="none" /> : null}
              {trendPath ? <path d={trendPath} fill="none" stroke={activeColor} strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" pointerEvents="none" /> : null}
              {visiblePoints.map((point, index) => {
                const x = xAt(index)
                const selected = point.year === selectedPoint?.year
                const current = point.year === currentYear
                return (
                  <g key={point.year} onPointerEnter={() => setHoveredYear(point.year)} onClick={() => selectPoint(point)} className="cursor-pointer">
                    <title>{`${point.year}: ${locale === "zh" ? "相对活跃指数" : "relative activity index"} ${formatNumber(point.close, locale)}`}</title>
                    {selected ? <rect x={LEFT_GUTTER + index * slotWidth + 2} y={PRICE_TOP - 16} width={Math.max(1, slotWidth - 4)} height={PRICE_BOTTOM - PRICE_TOP + 42} rx="6" fill={activeColor} opacity="0.075" /> : null}
                    {current ? <><line x1={x} x2={x} y1={PRICE_TOP - 17} y2={PRICE_BOTTOM} stroke={activeColor} strokeWidth="1" strokeDasharray="4 4" opacity="0.85" /><text x={x} y={PRICE_TOP - 23} textAnchor="middle" fill={activeColor} fontSize="10" fontWeight="700">{locale === "zh" ? "当前" : "NOW"}</text></> : null}
                    <circle cx={x} cy={yAt(point.close)} r={selected ? 5 : 3.25} fill="hsl(var(--surface))" stroke={activeColor} strokeWidth={selected ? 3 : 2} />
                    <text x={x} y={PRICE_BOTTOM + 21} textAnchor="middle" fill={selected ? activeColor : "hsl(var(--muted-foreground))"} fontSize="10" fontWeight={selected ? "700" : "400"}>{point.year}</text>
                    <rect x={LEFT_GUTTER + index * slotWidth} y={PRICE_TOP - 24} width={slotWidth} height={PRICE_BOTTOM - PRICE_TOP + 52} fill="transparent" />
                  </g>
                )
              })}
            </> : <>
              <line x1={LEFT_GUTTER} x2={chartWidth - RIGHT_GUTTER} y1={VOLUME_TOP - 15} y2={VOLUME_TOP - 15} stroke="hsl(var(--border))" strokeOpacity="0.75" />
              <text x={LEFT_GUTTER} y={VOLUME_TOP - 21} fill="hsl(var(--muted-foreground))" fontSize="10">{locale === "zh" ? "结构活跃度" : "ACTIVITY"}</text>
              {visiblePoints.map((point, index) => {
                const x = xAt(index)
                const rising = point.close >= point.open
                const candleColor = rising ? "hsl(var(--destructive))" : "hsl(158 52% 42%)"
                const bodyTop = yAt(Math.max(point.open, point.close))
                const bodyBottom = yAt(Math.min(point.open, point.close))
                const bodyHeight = Math.max(2, bodyBottom - bodyTop)
                const volumeTop = volumeY(point.volume)
                const selected = point.year === selectedPoint?.year
                const turning = turningByYear.get(point.year)
                const current = point.year === currentYear
                return (
                  <g key={point.year} onPointerEnter={() => setHoveredYear(point.year)} onClick={() => selectPoint(point)} className="cursor-pointer">
                    <title>{`${point.year}: ${locale === "zh" ? "相对活跃指数" : "relative activity index"} O ${formatNumber(point.open, locale)} H ${formatNumber(point.high, locale)} L ${formatNumber(point.low, locale)} C ${formatNumber(point.close, locale)} V ${formatNumber(point.volume, locale)}`}</title>
                    {selected ? <rect x={LEFT_GUTTER + index * slotWidth + 2} y={PRICE_TOP - 16} width={Math.max(1, slotWidth - 4)} height={VOLUME_BOTTOM - PRICE_TOP + 16} rx="6" fill={activeColor} opacity="0.075" /> : null}
                    {current ? <><line x1={x} x2={x} y1={PRICE_TOP - 17} y2={VOLUME_BOTTOM} stroke={activeColor} strokeWidth="1" strokeDasharray="4 4" opacity="0.85" /><text x={x} y={PRICE_TOP - 23} textAnchor="middle" fill={activeColor} fontSize="10" fontWeight="700">{locale === "zh" ? "当前" : "NOW"}</text></> : null}
                    <line x1={x} x2={x} y1={yAt(point.high)} y2={yAt(point.low)} stroke={candleColor} strokeWidth="1.5" />
                    <rect x={x - candleWidth / 2} y={bodyTop} width={candleWidth} height={bodyHeight} rx="1.5" fill={candleColor} stroke={candleColor} strokeWidth="1.5" />
                    <rect x={x - candleWidth / 2} y={volumeTop} width={candleWidth} height={Math.max(1, VOLUME_BOTTOM - volumeTop)} rx="1" fill={candleColor} opacity="0.28" />
                    {turning ? turning.kind === "peak"
                      ? <><path d={`M ${x - 4} ${Math.max(PRICE_TOP - 4, yAt(turning.value) - 10)} L ${x + 4} ${Math.max(PRICE_TOP - 4, yAt(turning.value) - 10)} L ${x} ${Math.max(PRICE_TOP + 2, yAt(turning.value) - 3)} Z`} fill={activeColor} /><text x={x} y={Math.max(PRICE_TOP - 9, yAt(turning.value) - 14)} textAnchor="middle" fill={activeColor} fontSize="9">{locale === "zh" ? "活跃高" : "HIGH"}</text></>
                      : <><path d={`M ${x - 4} ${Math.min(PRICE_BOTTOM + 2, yAt(turning.value) + 10)} L ${x + 4} ${Math.min(PRICE_BOTTOM + 2, yAt(turning.value) + 10)} L ${x} ${Math.min(PRICE_BOTTOM - 4, yAt(turning.value) + 3)} Z`} fill="hsl(var(--imperial-metal))" /><text x={x} y={Math.min(PRICE_BOTTOM + 17, yAt(turning.value) + 21)} textAnchor="middle" fill="hsl(var(--imperial-metal))" fontSize="9">{locale === "zh" ? "活跃低" : "LOW"}</text></>
                      : null}
                    <text x={x} y={VOLUME_BOTTOM + 21} textAnchor="middle" fill={selected ? activeColor : "hsl(var(--muted-foreground))"} fontSize="10" fontWeight={selected ? "700" : "400"}>{point.year}</text>
                    <rect x={LEFT_GUTTER + index * slotWidth} y={PRICE_TOP - 24} width={slotWidth} height={VOLUME_BOTTOM - PRICE_TOP + 52} fill="transparent" />
                  </g>
                )
              })}
              {ma10Path ? <path d={ma10Path} fill="none" stroke="hsl(var(--muted-foreground))" strokeWidth="1.5" strokeLinejoin="round" opacity="0.72" pointerEvents="none" /> : null}
              {ma5Path ? <path d={ma5Path} fill="none" stroke="hsl(var(--imperial-metal))" strokeWidth="1.75" strokeLinejoin="round" opacity="0.88" pointerEvents="none" /> : null}
              {ma3Path ? <path d={ma3Path} fill="none" stroke={activeColor} strokeWidth="2" strokeLinejoin="round" pointerEvents="none" /> : null}
            </>}

            {focusPoint ? <g aria-hidden="true" pointerEvents="none"><line x1={xAt(focusIndex)} x2={xAt(focusIndex)} y1={PRICE_TOP - 18} y2={viewMode === "trend" ? PRICE_BOTTOM : VOLUME_BOTTOM} stroke={activeColor} strokeWidth="1" strokeDasharray="2 3" opacity="0.7" /><line x1={LEFT_GUTTER} x2={chartWidth - RIGHT_GUTTER} y1={yAt(focusPoint.close)} y2={yAt(focusPoint.close)} stroke={activeColor} strokeWidth="1" strokeDasharray="2 3" opacity="0.7" /><rect x={chartWidth - RIGHT_GUTTER - 42} y={yAt(focusPoint.close) - 9} width="40" height="17" rx="4" fill="hsl(var(--surface))" stroke={activeColor} /><text x={chartWidth - RIGHT_GUTTER - 22} y={yAt(focusPoint.close) + 3} textAnchor="middle" fill={activeColor} fontSize="9" fontWeight="700">{formatNumber(focusPoint.close, locale)}</text></g> : null}
          </svg>
        </div>
        <p className="sr-only" aria-live="polite">{selectedDescription}</p>
      </div>

      {selectedPoint ? (
        <section className="min-w-0 border-t border-border/60 px-4 py-6 sm:px-6" aria-labelledby={`${id}-selected-year`}>
          <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
            <div>
              <p className="kicker">{locale === "zh" ? "所选年份" : "SELECTED YEAR"}</p>
              <h3 id={`${id}-selected-year`} className="mt-2 text-2xl font-semibold tabular-nums">{selectedPoint.year} · {activeSeriesLabel}</h3>
              <p className="mt-2 text-sm font-semibold text-primary">{relativeState(selectedPoint.close, locale)} · {locale === "zh" ? `相对活跃指数 ${formatNumber(selectedPoint.close, locale)}` : `Relative activity index ${formatNumber(selectedPoint.close, locale)}`}</p>
            </div>
            <dl className="grid grid-cols-3 gap-x-5 gap-y-3 text-right text-sm sm:grid-cols-6">
              {([
                [locale === "zh" ? "年初活跃" : "Open activity", selectedPoint.open],
                [locale === "zh" ? "最高活跃" : "Highest activity", selectedPoint.high],
                [locale === "zh" ? "最低活跃" : "Lowest activity", selectedPoint.low],
                [locale === "zh" ? "年末活跃" : "Close activity", selectedPoint.close],
                ["MA5", selectedPoint.ma5],
                [locale === "zh" ? "活跃" : "V", selectedPoint.volume],
              ] as Array<[string, number | null]>).map(([label, value]) => <div key={label}><dt className="text-muted-foreground">{label}</dt><dd className="mt-1 font-semibold tabular-nums text-foreground">{value == null ? "—" : formatNumber(value, locale)}</dd></div>)}
            </dl>
          </div>

          {selectedPoint.months.length ? (
            <div className="mt-5 grid min-w-0 border-y border-border/60 sm:grid-cols-2 xl:grid-cols-3">
              {selectedPoint.months.map((month, index) => (
                <article key={`${month.index}-${month.label}`} className={cn("min-w-0 border-border/55 px-3 py-4", index > 0 && "border-t sm:border-t-0", index % 2 === 1 && "sm:border-l", index >= 2 && "sm:border-t", index % 3 !== 0 && "xl:border-l", index >= 3 && "xl:border-t")}>
                  <div className="flex min-w-0 items-baseline justify-between gap-3">
                    <h4 className="min-w-0 truncate text-sm font-semibold"><span className="mr-2 text-xs tabular-nums text-muted-foreground">{String(month.index).padStart(2, "0")}</span>{month.label} · {month.ganzhi}</h4>
                    <p className="shrink-0 text-right text-base font-semibold tabular-nums" style={{ color: month.delta === 0 ? "hsl(var(--foreground))" : activeColor }}><span className="block text-[0.65rem] font-semibold text-muted-foreground">{relativeState(month.value, locale)}</span>{formatNumber(month.value, locale)} <span className="text-xs">{month.delta > 0 ? "+" : ""}{formatNumber(month.delta, locale)}</span></p>
                  </div>
                  {month.drivers.length ? <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">{month.drivers.map(driverLabel).join(" · ")}</p> : null}
                </article>
              ))}
            </div>
          ) : <p className="mt-5 border-y border-border/60 py-5 text-sm text-muted-foreground">{locale === "zh" ? "该年份的十二月明细尚未载入。" : "Twelve-month detail has not been loaded for this year."}</p>}
        </section>
      ) : null}

    </section>
  )
}
