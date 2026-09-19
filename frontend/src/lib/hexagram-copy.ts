import type { Locale } from "@/i18n/config"
import { HEXAGRAM_ESSENCE_BY_SLUG } from "@/lib/hexagram-essence"
import type { HexagramLibraryEntry } from "@/lib/hexagram-library"

/**
 * Chinese copy for a hexagram comes from that hexagram's own 大象 and 象傳,
 * generated into `hexagram-essence.ts` by tools/build_hexagram_essence.py.
 *
 * It used to be assembled by matching English theme words against ten regexes
 * and filling `${short}卦常用于观察${themes}中的局势与变化。`. Themes that
 * matched nothing fell back to the word 局势, so 贲 — whose themes are `form`,
 * `adornment`, `surface` — rendered as 「贲卦常用于观察局势中的局势与变化。」:
 * a sentence that says nothing, and says it twice. Anything generic enough to
 * fit all 64 hexagrams describes none of them.
 */

const THEME_RULES: { en: string; zh: string; pattern: RegExp }[] = [
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
  { en: "Form", zh: "形式", pattern: /form|adornment|surface|appearance|display|grace|ornament/ },
  { en: "Order", zh: "秩序", pattern: /order|repair|decay|ancestral|ritual|observation|example|correction/ },
  { en: "Depth", zh: "深度", pattern: /depth|repetition|truth|naturalness|unexpected|reflection|inner/ },
]

export function localizedHexagramThemes(themes: readonly string[], locale: Locale) {
  if (locale === "en") return themes.slice(0, 3)
  const labels: string[] = []
  for (const theme of themes) {
    const rule = THEME_RULES.find((candidate) => candidate.pattern.test(theme))
    if (rule && !labels.includes(rule.zh)) labels.push(rule.zh)
    if (labels.length === 3) break
  }
  return labels
}

/** What this hexagram is about, in its own words. */
export function localizedHexagramMeaning(entry: HexagramLibraryEntry, locale: Locale) {
  if (locale === "en") return entry.meaningEn
  const essence = HEXAGRAM_ESSENCE_BY_SLUG[entry.slug]
  if (essence?.imageZh) return essence.imageZh
  // No image in the corpus: name the trigram pair rather than invent a theme.
  return `${entry.shortNameZh}卦，${localizedTrigram(entry.lower, "zh")}下${localizedTrigram(entry.upper, "zh")}上。`
}

/** The 象傳 counsel clause, e.g. 君子以自强不息. Empty when the corpus has none. */
export function hexagramCounsel(slug: string) {
  return HEXAGRAM_ESSENCE_BY_SLUG[slug]?.counselZh ?? ""
}

/** 运势: how the situation tends to run. Empty when the corpus has none. */
export function hexagramTrend(slug: string) {
  return HEXAGRAM_ESSENCE_BY_SLUG[slug]?.trendZh ?? ""
}

export function hexagramImage(slug: string) {
  return HEXAGRAM_ESSENCE_BY_SLUG[slug]?.imageZh ?? ""
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

/** Bare trigram name without the element gloss, for inline prose. */
export function trigramShort(value: string, locale: Locale) {
  if (locale === "en") return value
  return {
    Heaven: "乾", Earth: "坤", Thunder: "震", Wind: "巽",
    Water: "坎", Fire: "离", Mountain: "艮", Lake: "兑",
  }[value] ?? value
}
