import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import { canonicalZiweiPalaceName, canonicalZiweiStarName } from "@/lib/ziwei-terms"

export const ZIWEI_BASELINE_ID = "ziwei-calendar-1950-2030-life-v2"
export const ZIWEI_LIFE_RULES_VERSION = "ziwei-life-2026.09-v2"
export const MAJOR_STAR_IDS: Record<string, string> = { 紫微: "ziwei", 天机: "tianji", 太阳: "taiyang", 武曲: "wuqu", 天同: "tiantong", 廉贞: "lianzhen", 天府: "tianfu", 太阴: "taiyin", 贪狼: "tanlang", 巨门: "jumen", 天相: "tianxiang", 天梁: "tianliang", 七杀: "qisha", 破军: "pojun" }
export const BRIGHTNESS_IDS: Record<string, string> = { 庙: "miao", 廟: "miao", "[+3]": "miao", 旺: "wang", "[+2]": "wang", 得: "de", "[+1]": "de", 利: "li", "[0]": "li", 平: "ping", "[-1]": "ping", 不: "bu", "[-2]": "bu", 陷: "xian", "[-3]": "xian" }
export const BRIGHTNESS_LABELS: Record<string, string> = { miao: "庙", wang: "旺", de: "得", li: "利", ping: "平", bu: "不", xian: "陷", unknown: "未标明" }
export type LifeStar = { id: string; name: string; brightness: string; brightness_label: string }

export function ziweiLifeStars(chart: IFunctionalAstrolabe): LifeStar[] {
  const palace = chart.palaces.find((item) => canonicalZiweiPalaceName(item.name, "zh") === "命宫")
  if (!palace) throw new Error("命盘缺少命宫，无法计算命宫统计。")
  return palace.majorStars.flatMap((star) => {
    const name = canonicalZiweiStarName(star.name, "zh")
    const id = MAJOR_STAR_IDS[name]
    if (!id) return []
    const brightness = BRIGHTNESS_IDS[String(star.brightness ?? "")] ?? "unknown"
    return [{ id, name, brightness, brightness_label: BRIGHTNESS_LABELS[brightness] }]
  }).sort((a, b) => a.id.localeCompare(b.id))
}

export function lifeComboId(stars: LifeStar[]) { return `ziwei.life_combo.${stars.map((star) => star.id).join("-") || "empty"}` }
export function lifeStateId(stars: LifeStar[]) { return `ziwei.life_state.${stars.map((star) => `${star.id}_${star.brightness}`).join("-") || "empty"}` }

export function ziweiFeatureIds(chart: IFunctionalAstrolabe): string[] {
  const stars = ziweiLifeStars(chart)
  return [lifeComboId(stars), lifeStateId(stars), `ziwei.life_count.${stars.length}`,
    ...stars.flatMap((star) => [`ziwei.life_star.${star.id}.present`, `ziwei.life_star.${star.id}.${star.brightness}`])]
}

export function ziweiLifeFeatureLabel(featureId: string, chart: IFunctionalAstrolabe, locale: "zh" | "en") {
  const stars = ziweiLifeStars(chart)
  const label = (star: LifeStar) => canonicalZiweiStarName(star.name, locale)
  const combo = stars.map(label).join(" × ") || (locale === "zh" ? "无十四主星" : "No major stars")
  if (featureId === lifeComboId(stars)) return `${locale === "zh" ? "命宫主星组合" : "Life-palace combination"} · ${combo}`
  if (featureId === lifeStateId(stars)) return `${locale === "zh" ? "命宫组合与亮度" : "Combination and brightness"} · ${stars.map((star) => `${label(star)}（${star.brightness_label}）`).join(" × ") || combo}`
  if (featureId.startsWith("ziwei.life_count.")) return locale === "zh" ? `命宫有 ${stars.length} 颗主星` : `${stars.length} major stars in the life palace`
  const star = stars.find((item) => featureId.startsWith(`ziwei.life_star.${item.id}.`))
  if (star) return `${label(star)} · ${featureId.endsWith(".present") ? (locale === "zh" ? "在命宫" : "in life palace") : star.brightness_label}`
  return locale === "zh" ? "非当前命宫统计项目" : "Outside the current life-palace reference"
}
