"use client"

import { useState } from "react"
import { SimulationReference } from "@/components/tools/chart-exploration"
import type { MetaphysicsChart, ThemeComparison } from "@/types/api"

const themes = { 事业: "Career", 财富: "Wealth", 感情: "Relationship", 五行与承压结构: "Elements & pressure" }

export function BaziSimulationExplorer({ chart, locale }: { chart: MetaphysicsChart; locale: "zh" | "en" }) {
  const profiles = chart.theme_profiles ?? chart.structure.theme_profiles
  const [theme, setTheme] = useState<string>(profiles[0]?.theme ?? "事业")
  const [metricId, setMetricId] = useState("")
  const profile = profiles.find((item) => item.theme === theme) ?? profiles[0]
  const comparisons = profile?.comparisons ?? []
  const selected = comparisons.find((item) => item.metric_id === metricId) ?? comparisons[0]
  return <section className="space-y-6" aria-label={locale === "zh" ? "八字历法模拟对照" : "BaZi calendar simulation"}>
    <SimulationReference statistics={chart.statistics} locale={locale} count={profiles.reduce((total, item) => total + (item.comparisons?.length ?? 0), 0)} />
    <div className="autumn-simulation-themes" role="group" aria-label={locale === "zh" ? "对照主题" : "Comparison theme"}>{profiles.map((item) => <button key={item.theme} type="button" aria-pressed={profile?.theme === item.theme} onClick={() => { setTheme(item.theme); setMetricId("") }}><strong>{locale === "zh" ? item.theme : themes[item.theme]}</strong><span>{item.comparisons?.length ?? 0} {locale === "zh" ? "项" : "metrics"}</span></button>)}</div>
    <div className="autumn-distribution-workspace">
      <div className="autumn-metric-list" aria-label={locale === "zh" ? "全部结构指标" : "All structural metrics"}>{comparisons.map((item) => <button key={item.metric_id} type="button" aria-pressed={selected?.metric_id === item.metric_id} onClick={() => setMetricId(item.metric_id)}><span>{item.label}</span><strong>{item.comparison_mode === "incidence" ? (item.value ? (locale === "zh" ? "命中" : "Present") : (locale === "zh" ? "未命中" : "Absent")) : item.value}</strong><small>{locale === "zh" ? item.display_label : item.semantic_pole || item.display_percentage}</small></button>)}</div>
      {selected ? <div className="autumn-distribution-detail"><DistributionDetail item={selected} locale={locale} /><div className="mt-7 border-t border-border/60 pt-5"><p className="kicker">{locale === "zh" ? "主题结构依据" : "THEME EVIDENCE"}</p><div className="mt-4 space-y-4">{profile.evidence.map((evidence) => <article key={evidence.id}><h4 className="text-sm font-semibold">{evidence.title}</h4><p className="mt-1 text-sm leading-6 text-muted-foreground">{evidence.detail}</p><p className="mt-1 text-xs text-muted-foreground">{evidence.source}</p></article>)}</div></div></div> : <p>{locale === "zh" ? "当前命盘没有可用的结构分布。" : "No structural distributions are available for this chart."}</p>}
    </div>
  </section>
}

function DistributionDetail({ item, locale }: { item: ThemeComparison; locale: "zh" | "en" }) {
  const incidence = item.comparison_mode === "incidence"
  const histogram = incidence ? [
    { value: 0, percentage: 100 - (item.hit_percentage ?? 0) },
    { value: 1, percentage: item.hit_percentage ?? 0 },
  ] : item.histogram ?? []
  const maximum = Math.max(1, ...histogram.map((bin) => bin.percentage))
  const percent = (value: number) => `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}%`
  return <>
    <p className="kicker">{locale === "zh" ? "当前选中结构" : "SELECTED STRUCTURE"}</p><div className="mt-2 flex items-end justify-between gap-6"><h3 className="text-2xl">{item.label}</h3><strong className="text-3xl font-normal text-primary">{incidence ? (item.value ? (locale === "zh" ? "命中" : "Present") : (locale === "zh" ? "未命中" : "Absent")) : item.value}</strong></div>
    <p className="mt-3 text-sm leading-6 text-muted-foreground">{locale === "zh" ? item.display_label : item.semantic_pole || item.display_percentage}</p>
    {item.status === "unsupported" ? <p className="mt-5">{locale === "zh" ? "本项暂无可比基线。" : "No comparable baseline for this metric."}</p> : <>
      <div className="autumn-histogram" role="img" aria-label={`${item.label} · ${locale === "zh" ? "完整历法分布，朱红标记本盘" : "Full calendar distribution; vermilion marks this chart"}`}>{histogram.map((bin) => <div key={String(bin.value)} className={String(bin.value) === String(item.value) ? "is-current" : ""}><span>{percent(bin.percentage)}</span><i style={{ height: `${bin.percentage > 0 ? Math.max(2, bin.percentage / maximum * 160) : 0}px` }} /><small>{incidence ? (bin.value ? (locale === "zh" ? "命中" : "Present") : (locale === "zh" ? "未命中" : "Absent")) : bin.value}</small></div>)}</div>
      <p className="mt-3 text-xs text-muted-foreground"><span className="mr-2 inline-block size-2 bg-primary" />{locale === "zh" ? "朱红柱为本盘取值；柱高为加权样本占比。" : "Vermilion marks this chart’s value; bar height is its weighted sample share."}</p>
      {!incidence ? <dl className="autumn-distribution-split">{[[locale === "zh" ? "低于本盘" : "Below this chart", item.lower_percentage], [locale === "zh" ? "与本盘相同" : "Same value", item.same_percentage], [locale === "zh" ? "高于本盘" : "Above this chart", item.higher_percentage]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{typeof value === "number" ? percent(value) : "—"}</dd></div>)}</dl> : null}
    </>}
  </>
}
