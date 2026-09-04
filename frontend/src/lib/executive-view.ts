export type ThemeKey = "overall" | "career" | "wealth" | "relationship" | "rhythm"

export const THEME_KEYS: readonly ThemeKey[] = ["overall", "career", "wealth", "relationship", "rhythm"]

export function normalizeThemeKey(value: string): ThemeKey {
  if (value === "health") return "rhythm"
  return THEME_KEYS.includes(value as ThemeKey) ? value as ThemeKey : "overall"
}

export function themeLabel(theme: ThemeKey, locale: "en" | "zh") {
  const labels: Record<ThemeKey, { zh: string; en: string }> = {
    overall: { zh: "总览", en: "Overall" },
    career: { zh: "事业", en: "Career" },
    wealth: { zh: "财富", en: "Wealth" },
    relationship: { zh: "关系", en: "Relationships" },
    rhythm: { zh: "身心节奏", en: "Rhythm" },
  }
  return labels[theme][locale]
}
