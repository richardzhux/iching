export type FrequencyLocale = "en" | "zh"

export function frequencyBadge(percentage: number | null | undefined) {
  if (percentage == null || !Number.isFinite(percentage) || percentage <= 0) return null
  if (percentage <= 2) return "SSR"
  if (percentage <= 5) return "SR"
  if (percentage <= 10) return "R"
  return null
}

export function frequencyLabel(percentage: number | null | undefined, locale: FrequencyLocale) {
  if (percentage == null || !Number.isFinite(percentage)) return ""
  if (percentage === 0) return locale === "zh" ? "本参考样本未出现" : "Not observed in this reference"
  const badge = frequencyBadge(percentage)
  if (badge) return badge
  if (percentage <= 20) return locale === "zh" ? "较少见" : "Less common"
  return locale === "zh" ? "常见" : "Common"
}

export function formatFrequency(percentage: number, locale: FrequencyLocale) {
  return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", { maximumFractionDigits: 2 }).format(percentage)
}
