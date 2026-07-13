import type { Locale } from "@/i18n/config"

export function sourceDisplayLabel(source: string | undefined, locale: Locale) {
  const normalized = source?.toLowerCase() ?? ""
  if (normalized === "takashima") return "高岛易断"
  if (normalized === "english_commentary") return "English Commentary"
  if (normalized === "symbolic") return locale === "zh" ? "卦象" : "Symbolic structure"
  if (normalized === "guaci") return locale === "zh" ? "卦辞库" : "Classical text"
  return locale === "zh" ? "来源待核" : "Source unverified"
}
