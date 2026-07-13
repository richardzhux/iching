import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"

const MAJOR: Record<string, string> = { 紫微: "ziwei", 天机: "tianji", 太阳: "taiyang", 武曲: "wuqu", 天同: "tiantong", 廉贞: "lianzhen", 天府: "tianfu", 太阴: "taiyin", 贪狼: "tanlang", 巨门: "jumen", 天相: "tianxiang", 天梁: "tianliang", 七杀: "qisha", 破军: "pojun" }
const BRANCH: Record<string, string> = { 子: "zi", 丑: "chou", 寅: "yin", 卯: "mao", 辰: "chen", 巳: "si", 午: "wu", 未: "wei", 申: "shen", 酉: "you", 戌: "xu", 亥: "hai" }
const ELEMENT: Record<string, string> = { 木: "wood", 火: "fire", 土: "earth", 金: "metal", 水: "water" }
const NUMBER: Record<string, string> = { 一: "1", 二: "2", 三: "3", 四: "4", 五: "5", 六: "6" }
const BRIGHTNESS: Record<string, string> = { 庙: "miao", 旺: "wang", 得: "de", 利: "li", 平: "ping", 陷: "xian", 不: "unmarked" }
const MUTAGEN: Record<string, string> = { 禄: "lu", 权: "quan", 科: "ke", 忌: "ji" }
const AUSPICIOUS = new Set(["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"])
const CHALLENGING = new Set(["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"])

export const ZIWEI_BASELINE_ID = "ziwei-calendar-1924-2044-v1"

export function ziweiFeatureIds(chart: IFunctionalAstrolabe) {
  const result: string[] = []
  const life = chart.palaces.find((palace) => palace.name === "命宫" || palace.name.toLowerCase().includes("soul"))
  const lifeStars = (life?.majorStars ?? []).map((star) => MAJOR[star.name]).filter(Boolean).sort()
  result.push(`ziwei.life_combo.${lifeStars.join("-") || "empty"}`)
  const body = chart.palaces.find((palace) => palace.isBodyPalace)
  result.push(`ziwei.body_branch.${BRANCH[body?.earthlyBranch ?? ""] ?? "unknown"}`)
  const fiveClass = `${ELEMENT[chart.fiveElementsClass?.[0]] ?? "unknown"}-${NUMBER[chart.fiveElementsClass?.[1]] ?? "0"}`
  result.push(`ziwei.five_elements.${fiveClass}`)
  result.push(`ziwei.empty_palaces.${chart.palaces.filter((palace) => palace.majorStars.length === 0).length}`)
  const brightness = new Map<string, number>()
  const auspiciousDensity: number[] = []
  const challengingDensity: number[] = []
  chart.palaces.forEach((palace) => {
    let palaceAuspicious = 0
    let palaceChallenging = 0
    palace.majorStars.forEach((star) => {
      const slug = BRIGHTNESS[star.brightness ?? ""] ?? "unmarked"
      brightness.set(slug, (brightness.get(slug) ?? 0) + 1)
    })
    ;[...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars].forEach((star) => {
      if (AUSPICIOUS.has(star.name)) palaceAuspicious += 1
      if (CHALLENGING.has(star.name)) palaceChallenging += 1
      if (star.mutagen && MUTAGEN[star.mutagen]) result.push(`ziwei.mutagen.${MUTAGEN[star.mutagen]}.palace-${palace.index}`)
    })
    auspiciousDensity.push(palaceAuspicious)
    challengingDensity.push(palaceChallenging)
  })
  brightness.forEach((count, name) => result.push(`ziwei.brightness.${name}.${count}`))
  result.push(`ziwei.auspicious_palaces.${auspiciousDensity.filter(Boolean).length}`)
  result.push(`ziwei.auspicious_max_density.${Math.max(...auspiciousDensity)}`)
  result.push(`ziwei.challenging_palaces.${challengingDensity.filter(Boolean).length}`)
  result.push(`ziwei.challenging_max_density.${Math.max(...challengingDensity)}`)
  return [...new Set(result)]
}
