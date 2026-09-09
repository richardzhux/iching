"use client"

import { THEME_KEYS, themeLabel, type ThemeKey } from "@/lib/executive-view"
import { cn } from "@/lib/utils"
import { personalActivityPoints, type LifeKlineSeries } from "@/components/tools/life-kline-chart"

export function ThemeSelector({ value, locale, onChange, className }: { value: ThemeKey; locale: "en" | "zh"; onChange: (theme: ThemeKey) => void; className?: string }) {
  return (
    <div className={cn("autumn-theme-selector max-w-full overflow-x-auto border-b border-border/60", className)}>
      <div role="group" aria-label={locale === "zh" ? "选择解读主题" : "Choose interpretation theme"} className={cn("grid grid-cols-5 gap-2", locale === "zh" ? "min-w-0" : "min-w-[28rem]")}>
        {THEME_KEYS.map((theme) => (
          <button
            key={theme}
            type="button"
            aria-pressed={value === theme}
            onClick={() => onChange(theme)}
            className={cn("min-h-12 border-b-2 px-3 py-3 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary", value === theme ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}
          >
            {themeLabel(theme, locale)}
          </button>
        ))}
      </div>
    </div>
  )
}

export function OverallThemeTimeline({ lifeKline, locale, currentYear, onSelectTheme }: { lifeKline: LifeKlineSeries; locale: "en" | "zh"; currentYear: number; onSelectTheme?: (theme: ThemeKey) => void }) {
  const rows = (["career", "wealth", "relationship", "rhythm"] as const).flatMap((theme) => {
    const series = lifeKline.series.find((item) => item.key === theme || (theme === "rhythm" && item.key === "health"))
    if (!series) return []
    const points = personalActivityPoints(lifeKline, series)
    const point = points.find((item) => item.year >= currentYear) ?? points[0]
    if (!point) return []
    const delta = point.close - 100
    return [{ theme, label: series.label, point, delta }]
  })
  return (
    <section className="overflow-hidden rounded-3xl border border-border/65 bg-surface shadow-[var(--surface-shadow-soft)]">
      <header className="border-b border-border/60 px-5 py-6"><p className="kicker">{locale === "zh" ? "当前变化" : "CURRENT CHANGE"}</p><h2 className="mt-2 text-2xl font-semibold">{locale === "zh" ? "四条主线的当前节奏" : "Current activity across four themes"}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{locale === "zh" ? "以各主题的个人常态 100 为参照，点选主线查看年度趋势与月份触发。" : "Each theme is indexed to its personal baseline of 100. Select a theme to explore yearly trends and monthly drivers."}</p></header>
      <ol className="divide-y divide-border/55">
        {rows.map(({ theme, label, point, delta }) => <li key={theme}><button type="button" onClick={() => onSelectTheme?.(theme)} disabled={!onSelectTheme} className="grid w-full gap-2 px-5 py-4 text-left transition hover:bg-primary/[0.035] disabled:cursor-default sm:grid-cols-[8rem_1fr_auto] sm:items-center"><span className="font-semibold">{themeLabel(theme, locale)}</span><span className="text-sm text-muted-foreground">{point.year} · {locale === "zh" ? (Math.abs(delta) <= 3 ? "接近常态" : delta > 0 ? "结构活跃增强" : "结构活跃减弱") : (Math.abs(delta) <= 3 ? "Near baseline" : delta > 0 ? "Activity increases" : "Activity decreases")}</span><span className="text-right text-sm font-semibold tabular-nums text-primary">{Math.round(point.close)} <span className="text-xs text-muted-foreground">{label}</span>{onSelectTheme ? <span aria-hidden="true" className="ml-4">↗</span> : null}</span></button></li>)}
      </ol>
    </section>
  )
}
