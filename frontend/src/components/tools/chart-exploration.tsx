"use client"

import { ArrowUpRight } from "lucide-react"
import { ComparisonUniverseBar } from "@/components/tools/comparison-universe-bar"
import type { MetaphysicsStatistics } from "@/types/api"

export type AnalysisDestination<K extends string> = { key: K; label: string; description: string; count?: string }

export function AnalysisNavigation<K extends string>({ items, value, onChange, label }: { items: AnalysisDestination<K>[]; value: K; onChange: (key: K) => void; label: string }) {
  return <nav data-export-exclude aria-label={label} className="autumn-result-nav autumn-analysis-nav">
    {items.map((item, index) => <button key={item.key} type="button" aria-pressed={value === item.key} onClick={() => onChange(item.key)}>
      <span className="autumn-analysis-number">0{index + 1}</span><span><strong>{item.label}</strong><small>{item.description}</small></span>
    </button>)}
  </nav>
}

export function AnalysisMap<K extends string>({ items, onChange, locale, statistics }: { items: AnalysisDestination<K>[]; onChange: (key: K) => void; locale: "zh" | "en"; statistics?: MetaphysicsStatistics | null }) {
  return <aside className="autumn-analysis-map" aria-label={locale === "zh" ? "命盘分析地图" : "Chart analysis map"}>
    <p className="kicker">{locale === "zh" ? "继续探索这张盘" : "EXPLORE THIS CHART"}</p>
    <h2>{locale === "zh" ? "从结论，走进依据。" : "Follow the evidence."}</h2>
    <div>{items.map((item) => <button type="button" key={item.key} onClick={() => onChange(item.key)}><span><strong>{item.label}</strong><small>{item.description}</small>{item.count ? <em>{item.count}</em> : null}</span><ArrowUpRight aria-hidden="true" className="size-4 shrink-0" /></button>)}</div>
    {statistics && (!statistics.status || statistics.status === "available") ? <p className="autumn-analysis-footnote"><strong>{statistics.baseline.unique_state_count?.toLocaleString()}</strong> {locale === "zh" ? "个历法状态作为结构对照" : "calendar states in the structural reference"}<br />{statistics.baseline.start.slice(0, 4)}–{statistics.baseline.end.slice(0, 4)}</p> : null}
  </aside>
}

export function SimulationReference({ statistics, locale, count }: { statistics: MetaphysicsStatistics; locale: "zh" | "en"; count: number }) {
  const { baseline } = statistics
  const unit = baseline.sample_unit === "minute" ? (locale === "zh" ? "分钟" : "minutes") : (locale === "zh" ? "民用小时" : "civil hours")
  return <header className="autumn-simulation-reference">
    <div><p className="kicker">{locale === "zh" ? "历法模拟 · 结构对照" : "CALENDAR SIMULATION · STRUCTURAL COMPARISON"}</p><h2>{locale === "zh" ? "这张盘，在样本中是什么样？" : "Where does this chart sit in the reference?"}</h2><p>{locale === "zh" ? "每一项都对应当前命盘的具体结构，按其在历法时间中的持续时长加权。出现频率描述结构的常见程度。" : "Each comparison describes a specific chart structure, weighted by its duration in calendar time. Frequency measures how common that structure is."}</p></div>
    <dl><div><dt>{locale === "zh" ? "参考区间" : "Reference period"}</dt><dd>{baseline.start.slice(0, 4)}–{baseline.end.slice(0, 4)}</dd></div><div><dt>{locale === "zh" ? "唯一历法状态" : "Distinct calendar states"}</dt><dd>{baseline.unique_state_count?.toLocaleString() ?? "—"}</dd></div><div><dt>{locale === "zh" ? "本盘对照项目" : "Chart comparisons"}</dt><dd>{count}</dd></div></dl>
    <p className="text-xs text-muted-foreground">{locale === "zh" ? "加权范围" : "Weighted coverage"} · {baseline.sample_weight.toLocaleString(undefined, { maximumFractionDigits: 0 })} {unit} · {baseline.timezone}</p>
    <ComparisonUniverseBar statistics={statistics} locale={locale} />
  </header>
}
