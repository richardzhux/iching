"use client"

import { THEME_KEYS, themeLabel, type ThemeKey } from "@/lib/executive-view"
import { cn } from "@/lib/utils"
import type { LifeKlineSeries } from "@/components/tools/life-kline-chart"

export function ThemeSelector({ value, locale, onChange, className }: { value: ThemeKey; locale: "en" | "zh"; onChange: (theme: ThemeKey) => void; className?: string }) {
  return (
    <div className={cn("max-w-full overflow-x-auto rounded-2xl border border-border/60 bg-surface p-1.5", className)}>
      <div role="tablist" aria-label={locale === "zh" ? "选择解读主题" : "Choose interpretation theme"} className="grid min-w-[32rem] grid-cols-5 gap-1">
        {THEME_KEYS.map((theme) => (
          <button
            key={theme}
            type="button"
            role="tab"
            aria-selected={value === theme}
            onClick={() => onChange(theme)}
            className={cn("min-h-11 rounded-xl px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", value === theme ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:bg-primary/[0.07] hover:text-foreground")}
          >
            {themeLabel(theme, locale)}
          </button>
        ))}
      </div>
    </div>
  )
}

export function OverallThemeTimeline({ lifeKline, locale, currentYear }: { lifeKline: LifeKlineSeries; locale: "en" | "zh"; currentYear: number }) {
  const rows = (["career", "wealth", "relationship", "rhythm"] as const).flatMap((theme) => {
    const series = lifeKline.series.find((item) => item.key === theme || (theme === "rhythm" && item.key === "health"))
    if (!series) return []
    const point = series.points.find((item) => item.year >= currentYear) ?? series.points[0]
    if (!point) return []
    const delta = point.close - 100
    return [{ theme, label: series.label, point, delta }]
  })
  return (
    <section className="overflow-hidden rounded-3xl border border-border/65 bg-surface shadow-[var(--surface-shadow-soft)]">
      <header className="border-b border-border/60 px-5 py-6"><p className="kicker">{locale === "zh" ? "当前变化" : "CURRENT CHANGE"}</p><h2 className="mt-2 text-2xl font-semibold">{locale === "zh" ? "四条主线的下一次变化" : "The next change in each theme"}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{locale === "zh" ? "总览不合成一个吉凶分数；这里只列每条主线最近的结构变化。" : "Overall does not combine themes into a fortune score. It shows the nearest structural change in each theme."}</p></header>
      <ol className="divide-y divide-border/55">
        {rows.map(({ theme, label, point, delta }) => <li key={theme} className="grid gap-2 px-5 py-4 sm:grid-cols-[8rem_1fr_auto] sm:items-center"><p className="font-semibold">{themeLabel(theme, locale)}</p><p className="text-sm text-muted-foreground">{point.year} · {locale === "zh" ? (Math.abs(delta) <= 3 ? "接近常态" : delta > 0 ? "结构活跃增强" : "结构活跃减弱") : (Math.abs(delta) <= 3 ? "Near baseline" : delta > 0 ? "Activity increases" : "Activity decreases")}</p><p className="text-right text-sm font-semibold tabular-nums text-primary">{Math.round(point.close)} <span className="text-xs text-muted-foreground">{label}</span></p></li>)}
      </ol>
    </section>
  )
}
