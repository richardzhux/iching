import type { Locale } from "@/i18n/config"
import type { HexagramLibraryEntry } from "@/lib/hexagram-library"

type ThemeRule = {
  en: string
  zh: string
  pattern: RegExp
}

const THEME_RULES: ThemeRule[] = [
  { en: "Beginnings", zh: "开端", pattern: /beginning|initiative|arrival|approach|first commitment|threshold/ },
  { en: "Change", zh: "变化", pattern: /change|transformation|renewal|return|cycle|adaptation|movement|progress|advance|increase|decrease/ },
  { en: "Relationships", zh: "关系", pattern: /relationship|marriage|attraction|alliance|belonging|fellowship|gathering|family|household|roles|communication|trust/ },
  { en: "Work", zh: "事业", pattern: /leadership|organization|command|responsibility|public cause|recognition|culture|training|discipline|achievement/ },
  { en: "Timing", zh: "时机", pattern: /timing|patience|waiting|readiness|sequence|duration|constancy|gradual|temporary/ },
  { en: "Choices", zh: "选择", pattern: /decision|selection|difference|trade|conduct|protocol|measure|calibration|clarity/ },
  { en: "Risk", zh: "风险", pattern: /risk|danger|conflict|dispute|obstruction|blockage|injury|decline|erosion|constraint|overload|exhaustion/ },
  { en: "Restraint", zh: "节制", pattern: /restraint|limit|boundary|withholding|retreat|preservation|stillness|care|caution|concealment/ },
  { en: "Growth", zh: "成长", pattern: /growth|learning|instruction|nourishment|feeding|resource|support|benefit|prosperity|abundance/ },
  { en: "Action", zh: "行动", pattern: /power|strength|creative|action|breakthrough|enforcement|mobilization|inspiration|visibility/ },
]

export const HEXAGRAM_THEME_FILTERS = [
  { id: "change", en: "Change", zh: "变化", pattern: /change|transformation|renewal|return|progress|movement/ },
  { id: "relationships", en: "Relationships", zh: "关系", pattern: /relationship|marriage|attraction|alliance|belonging|family|communication/ },
  { id: "work", en: "Work", zh: "事业", pattern: /leadership|organization|responsibility|recognition|command|growth|achievement/ },
  { id: "timing", en: "Timing", zh: "时机", pattern: /timing|patience|waiting|readiness|sequence|duration|gradual/ },
  { id: "challenge", en: "Challenges", zh: "困难", pattern: /danger|risk|conflict|obstruction|blockage|constraint|difficulty|exhaustion/ },
] as const

export function localizedHexagramThemes(themes: readonly string[], locale: Locale) {
  if (locale === "en") return themes.slice(0, 3)
  const labels: string[] = []
  for (const theme of themes) {
    const rule = THEME_RULES.find((candidate) => candidate.pattern.test(theme))
    const label = rule?.zh ?? "局势"
    if (!labels.includes(label)) labels.push(label)
    if (labels.length === 3) break
  }
  return labels.length ? labels : ["局势"]
}

export function localizedHexagramMeaning(entry: HexagramLibraryEntry, locale: Locale) {
  if (locale === "en") return entry.meaningEn
  const themes = localizedHexagramThemes(entry.themes, locale)
  return `${entry.shortNameZh}卦常用于观察${themes.join("、")}中的局势与变化。`
}

export function localizedTrigram(value: string, locale: Locale) {
  if (locale === "en") return value
  return {
    Heaven: "乾 · 天",
    Earth: "坤 · 地",
    Thunder: "震 · 雷",
    Wind: "巽 · 风",
    Water: "坎 · 水",
    Fire: "离 · 火",
    Mountain: "艮 · 山",
    Lake: "兑 · 泽",
  }[value] ?? value
}

export function matchesThemeFilter(themes: readonly string[], filterId: string) {
  const filter = HEXAGRAM_THEME_FILTERS.find((candidate) => candidate.id === filterId)
  return !filter || themes.some((theme) => filter.pattern.test(theme))
}
