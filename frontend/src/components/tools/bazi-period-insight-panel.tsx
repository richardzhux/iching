"use client"

import { ArrowRight, CalendarRange, CircleDot, Layers3 } from "lucide-react"

import { cn } from "@/lib/utils"
import type {
  DayunCycle,
  PeriodMonth,
  PeriodThemeActivation,
  PeriodYear,
} from "@/types/api"

type Locale = "en" | "zh"

const THEMES = [
  ["事业", "career", "事业"],
  ["财富", "wealth", "财富"],
  ["感情", "relationship", "感情"],
  ["五行与承压结构", "rhythm", "身心节奏"],
] as const

const ROLE_STYLE: Record<string, string> = {
  formation: "bg-violet-100 text-violet-800",
  rescue: "bg-emerald-100 text-emerald-800",
  support: "bg-sky-100 text-sky-800",
  damage: "bg-amber-100 text-amber-900",
  conflict: "bg-rose-100 text-rose-800",
  activity: "bg-primary/10 text-primary",
  neutral: "bg-muted text-muted-foreground",
}

function dedupe(items: PeriodThemeActivation[]) {
  const seen = new Set<string>()
  return items.filter((item) => {
    const key = `${item.label}:${item.detail}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

export function BaziPeriodInsightPanel({
  cycle,
  year,
  month,
  selectedTheme,
  locale,
}: {
  cycle: DayunCycle | undefined
  year: PeriodYear | undefined
  month: PeriodMonth | undefined
  selectedTheme?: string
  locale: Locale
}) {
  if (!cycle) return null
  const layers = [
    { key: "dayun", label: locale === "zh" ? "大运" : "Da Yun", title: `${cycle.ganzhi} · ${cycle.start_year}–${cycle.end_year}`, data: cycle.theme_activations },
    ...(year ? [{ key: "liunian", label: locale === "zh" ? "流年" : "Year", title: `${year.year} · ${year.ganzhi}`, data: year.theme_activations }] : []),
    ...(month ? [{ key: "liuyue", label: locale === "zh" ? "流月" : "Month", title: `${month.label} · ${month.ganzhi}`, data: month.theme_activations }] : []),
  ]
  const selectedCanonical = selectedTheme === "health" ? "rhythm" : selectedTheme
  const orderedThemes = selectedCanonical
    ? [...THEMES].sort((left, right) => Number(right[1] === selectedCanonical) - Number(left[1] === selectedCanonical))
    : THEMES

  return (
    <section className="border-y border-border/60 bg-surface">
      <header className="flex flex-wrap items-end justify-between gap-4 px-5 py-5 sm:px-7">
        <div>
          <div className="flex items-center gap-2 text-primary">
            <CalendarRange aria-hidden="true" className="size-4" />
            <p className="text-sm font-semibold">{locale === "zh" ? "当前阶段正在激活什么" : "What this period activates"}</p>
          </div>
          <h3 className="mt-2 text-2xl font-semibold">{layers.map((layer) => layer.title).join("　/　")}</h3>
        </div>
        <p className="max-w-xl text-sm leading-6 text-muted-foreground">
          {locale === "zh"
            ? "按大运、流年、流月逐层展示新增结构。这里描述主题信号怎样被激活，不把冲合直接解释成好坏。"
            : "Da Yun, year, and month are layered to show newly activated structures without turning every interaction into a good-or-bad grade."}
        </p>
      </header>

      <div className="grid min-w-0 border-t border-border/55 lg:grid-cols-4">
        {orderedThemes.map(([theme, key, label]) => {
          const items = dedupe(layers.flatMap((layer) =>
            (layer.data?.[theme] ?? []).map((item) => ({ ...item, layer: item.layer || layer.key })),
          ))
          const active = key === selectedCanonical
          return (
            <article key={theme} className={cn("min-w-0 border-b border-border/45 px-5 py-5 last:border-b-0 lg:border-b-0 lg:border-r lg:last:border-r-0", active && "bg-primary/[0.045]")}>
              <div className="flex items-center justify-between gap-3">
                <h4 className="font-semibold">{label}</h4>
                <span className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? `${items.length} 项触发` : `${items.length} signals`}</span>
              </div>
              {items.length ? (
                <div className="mt-4 space-y-4">
                  {items.slice(0, 5).map((item) => (
                    <div key={`${item.layer}-${item.id}-${item.label}`} className="min-w-0">
                      <div className="flex items-start gap-2">
                        <CircleDot aria-hidden="true" className="mt-1 size-3.5 shrink-0 text-primary" />
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-semibold leading-5">{item.label}</p>
                            <span className={cn("rounded-full px-2 py-0.5 text-[0.65rem] font-semibold", ROLE_STYLE[item.role] ?? ROLE_STYLE.neutral)}>
                              {item.layer === "dayun" ? (locale === "zh" ? "大运" : "cycle") : item.layer === "liunian" ? (locale === "zh" ? "流年" : "year") : (locale === "zh" ? "流月" : "month")}
                            </span>
                          </div>
                          <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-5 flex items-center gap-2 text-sm text-muted-foreground">
                  <Layers3 aria-hidden="true" className="size-4" />
                  {locale === "zh" ? "这一层没有新增的直接结构信号" : "No new direct signal in this layer"}
                </div>
              )}
            </article>
          )
        })}
      </div>
      <footer className="flex items-center gap-2 border-t border-border/55 bg-muted/20 px-5 py-3 text-xs text-muted-foreground sm:px-7">
        <span>{locale === "zh" ? "大运提供背景" : "Da Yun sets the background"}</span>
        <ArrowRight aria-hidden="true" className="size-3.5" />
        <span>{locale === "zh" ? "流年聚焦阶段" : "the year focuses it"}</span>
        <ArrowRight aria-hidden="true" className="size-3.5" />
        <span>{locale === "zh" ? "流月显示具体触发" : "the month shows the immediate trigger"}</span>
      </footer>
    </section>
  )
}
