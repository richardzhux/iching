import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import { frequencyLabel } from "@/lib/frequency-display"
import { canonicalZiweiStarName } from "@/lib/ziwei-terms"
import { lifeComboId, lifeStateId, ziweiLifeStars, ZIWEI_BASELINE_ID, ZIWEI_LIFE_RULES_VERSION } from "@/lib/ziwei-statistics"
import type { MetaphysicsStatistics } from "@/types/api"

export const ZIWEI_CONSUMER_RULES_VERSION = ZIWEI_LIFE_RULES_VERSION
export type ZiweiKlineMonth = { index: number; label: string; ganzhi: string; value: number; delta: number; drivers: string[] }
export type ZiweiKlinePoint = { year: number; open: number; close: number; high: number; low: number; volume: number; ma3: number | null; ma5: number | null; ma10: number | null; months: ZiweiKlineMonth[] }
export type ZiweiLifeKline = {
  default_window: { start_year: number; end_year: number }
  series: Array<{ key: "overall"; label: string; color: string; points: ZiweiKlinePoint[] }>
  period_bands: Array<{ label: string; start_year: number; end_year: number }>
  stages: Array<{ key: string; label: string; year: number; score: number; theme: string; summary: string }>
  method: string
  baseline: { normalized_value: number; values_are_relative: boolean; start_year: number; end_year: number; series: { overall: { raw_value: number } }; method: string }
}
export type ZiweiConsumerProfile = {
  version: string; system: "ziwei"
  identity: { system_title: string; archetype_title: string; archetype_subtitle: string }
  subjects: []; achievements: []; twin: null; capability_key: null
  fingerprints: Array<{ id: string; title: string; detail: string; rarity_label: string; incidence_percentage: number | null }>
  life_kline: ZiweiLifeKline
  metadata: { rules_version: string; cohort_id: string; baseline_id: string | null; selected_period: string | null }
}

function emptyKline(year: number): ZiweiLifeKline {
  return { default_window: { start_year: year, end_year: year + 9 }, series: [], period_bands: [], stages: [], method: "experimental_life_palace_activation_v2", baseline: { normalized_value: 100, values_are_relative: true, start_year: year, end_year: year, series: { overall: { raw_value: 1 } }, method: "mean_monthly_activation_density_v2" } }
}

export function lifeFeaturePercentage(statistics: unknown, featureId: string): number | null {
  const stats = statistics as MetaphysicsStatistics | null | undefined
  if (!stats || stats.status !== "available" || stats.baseline?.id !== ZIWEI_BASELINE_ID) return null
  const metric = stats.rarity_metrics?.find((item) => item.feature_id === featureId)
  if (!metric || !["observed", "zero"].includes(metric.status ?? "") || !Number.isFinite(metric.percentage) || metric.percentage < 0 || metric.percentage > 100) return null
  return metric.percentage
}

export function buildZiweiConsumerProfile(chart: IFunctionalAstrolabe, horoscope: IFunctionalHoroscope | null | undefined, statistics?: unknown): ZiweiConsumerProfile {
  const zh = chart.palaces.some((palace) => /[\u3400-\u9fff]/.test(palace.name))
  const locale = zh ? "zh" : "en"
  const stars = ziweiLifeStars(chart)
  const names = stars.map((star) => canonicalZiweiStarName(star.name, locale)).join(" × ") || (zh ? "命宫无十四主星" : "No major stars in the life palace")
  const state = stars.map((star) => `${canonicalZiweiStarName(star.name, locale)} · ${star.brightness_label}`).join("；")
  const features = [
    { id: lifeComboId(stars), title: names, detail: zh ? "只统计命宫内十四主星的无序组合；不借入对宫主星。" : "The unordered combination of the fourteen major stars in the life palace; opposite-palace stars are not borrowed." },
    ...(stars.length ? [{ id: lifeStateId(stars), title: state, detail: zh ? "同时匹配上述每颗主星与各自亮度；未标明的状态保留为未知，不代替任何亮度档。" : "Matches each star and its brightness together; missing brightness remains unknown." }] : []),
  ]
  return { version: ZIWEI_CONSUMER_RULES_VERSION, system: "ziwei",
    identity: { system_title: zh ? "紫微 · 命宫" : "Zi Wei · Life palace", archetype_title: names, archetype_subtitle: state || (zh ? "空宫是一种结构，不代表缺少能力或命运较差。" : "An empty life palace does not imply inferior ability or fortune.") },
    subjects: [], achievements: [], twin: null, capability_key: null,
    fingerprints: features.map((item) => { const percentage = lifeFeaturePercentage(statistics, item.id); return { ...item, incidence_percentage: percentage, rarity_label: frequencyLabel(percentage, locale) } }),
    life_kline: emptyKline(new Date().getFullYear()),
    metadata: { rules_version: ZIWEI_CONSUMER_RULES_VERSION, cohort_id: lifeComboId(stars), baseline_id: lifeFeaturePercentage(statistics, lifeComboId(stars)) === null ? null : ZIWEI_BASELINE_ID, selected_period: horoscope ? String(horoscope.solarDate) : null },
  }
}

const klineCache = new WeakMap<IFunctionalAstrolabe, ZiweiLifeKline>()
export function buildZiweiLifeKline(chart: IFunctionalAstrolabe): ZiweiLifeKline {
  const cached = klineCache.get(chart)
  if (cached) return cached
  const currentYear = new Date().getFullYear()
  const result = emptyKline(currentYear)
  const birthParts = String(chart.solarDate).split(/[-/]/).map(Number)
  const [birthYear, birthMonth = 1, birthDay = 1] = birthParts
  if (!Number.isInteger(birthYear) || typeof chart.horoscope !== "function") return result
  const start = Math.max(1900, birthYear), end = Math.min(2100, birthYear + 79)
  const names = new Set(ziweiLifeStars(chart).map((star) => star.name))
  const rawYears: Array<{ year: number; months: ZiweiKlineMonth[] }> = []
  const raw: number[] = []
  for (let year = start; year <= end; year++) {
    const months: ZiweiKlineMonth[] = []
    for (let month = 1; month <= 12; month++) {
      if (year === birthYear && (month < birthMonth || (month === birthMonth && birthDay > 15))) continue
      const period = chart.horoscope(`${year}-${month}-15`)
      const drivers = [period.decadal, period.yearly, period.monthly].flatMap((item, layer) => [...new Set(item.mutagen.map((star) => canonicalZiweiStarName(star, "zh")))].filter((star) => names.has(star)).map((star) => `${["大限", "流年", "流月"][layer]} · ${star}`))
      const value = 1 + drivers.length
      raw.push(value)
      months.push({ index: month, label: `${year}-${String(month).padStart(2, "0")}`, ganzhi: `${period.monthly.heavenlyStem}${period.monthly.earthlyBranch}`, value, delta: 0, drivers })
    }
    if (months.length) rawYears.push({ year, months })
  }
  const mean = raw.reduce((a, b) => a + b, 0) / (raw.length || 1) || 1
  const normalize = (value: number) => Math.round((100 + 35 * Math.tanh(((value / mean - 1) * 100) / 35)) * 10) / 10
  const points: ZiweiKlinePoint[] = rawYears.map(({ year, months }) => {
    const volume = months.reduce((sum, month) => sum + month.value - 1, 0)
    const normalized = months.map((month) => ({ ...month, value: normalize(month.value), delta: Math.round((normalize(month.value) - 100) * 10) / 10 }))
    const values = normalized.map((month) => month.value)
    return { year, open: values[0], close: values[values.length - 1], high: Math.max(...values), low: Math.min(...values), volume, ma3: null, ma5: null, ma10: null, months: normalized }
  })
  points.forEach((point, index) => { for (const window of [3, 5, 10] as const) if (index + 1 >= window) point[`ma${window}`] = Math.round(points.slice(index + 1 - window, index + 1).reduce((sum, item) => sum + item.close, 0) / window * 10) / 10 })
  result.series = [{ key: "overall", label: "命宫主星触发", color: "#a85a42", points }]
  result.baseline = { normalized_value: 100, values_are_relative: true, start_year: rawYears[0]?.year ?? start, end_year: end, series: { overall: { raw_value: mean } }, method: "mean_monthly_activation_density_v2" }
  klineCache.set(chart, result)
  return result
}
