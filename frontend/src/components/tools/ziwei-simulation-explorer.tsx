"use client"

import { useState } from "react"
import { SimulationReference } from "@/components/tools/chart-exploration"
import { formatFrequency, frequencyLabel } from "@/lib/frequency-display"
import type { ZiweiConsumerProfile, ZiweiConsumerBaseline } from "@/lib/ziwei-consumer"
import type { MetaphysicsStatistics, RarityMetric } from "@/types/api"

export function ZiweiSimulationExplorer({ statistics, metrics, consumer, locale }: { statistics: MetaphysicsStatistics; metrics: Array<RarityMetric & { label: string }>; consumer: ZiweiConsumerProfile; locale: "zh" | "en" }) {
  const [selectedId, setSelectedId] = useState("")
  const ordered = [...metrics].sort((a, b) => (a.status === "unsupported" ? Infinity : a.percentage) - (b.status === "unsupported" ? Infinity : b.percentage))
  const selected = ordered.find((item) => item.feature_id === selectedId) ?? ordered[0]
  const baseline = statistics.consumer_baseline as Partial<ZiweiConsumerBaseline> | undefined
  const family = baseline?.structural_families?.find((item) => item.id === consumer.twin.family_id)
  const familyShare = family?.share_percentage ?? (family?.weight != null && family.total_weight ? family.weight / family.total_weight * 100 : null)
  const format = (value: number) => `${formatFrequency(value, locale)}%`
  return <section className="space-y-6" aria-label={locale === "zh" ? "紫微历法模拟对照" : "Zi Wei calendar simulation"}>
    <SimulationReference statistics={statistics} locale={locale} count={metrics.length} />
    <div className="autumn-distribution-workspace">
      <div className="autumn-metric-list" aria-label={locale === "zh" ? "全部结构出现率" : "All structural frequencies"}>{ordered.map((item) => <button key={item.feature_id} type="button" aria-pressed={selected?.feature_id === item.feature_id} onClick={() => setSelectedId(item.feature_id)}><span>{item.label}</span><strong>{item.status === "unsupported" ? "—" : format(item.percentage)}</strong><small>{item.status === "unsupported" ? (locale === "zh" ? "未收录" : "Not catalogued") : frequencyLabel(item.percentage, locale)}</small></button>)}</div>
      {selected ? <article className="autumn-distribution-detail">
        <p className="kicker">{locale === "zh" ? "当前选中结构" : "SELECTED STRUCTURE"}</p><h3 className="mt-2 text-2xl">{selected.label}</h3>
        {selected.status === "unsupported" ? <p className="mt-6 text-sm">{locale === "zh" ? "本项在当前基线中没有可用统计。" : "This feature has no statistics in the current baseline."}</p> : <>
          <div className="autumn-frequency-number">{format(selected.percentage)}<span>{frequencyLabel(selected.percentage, locale)}</span></div>
          <p className="text-sm leading-6 text-muted-foreground">{locale === "zh" ? `在历法对照范围内，${format(selected.percentage)} 的加权时间具有相同特征。` : `${format(selected.percentage)} of the weighted calendar reference shares this feature.`}</p>
          <div className="autumn-frequency-bar" role="img" aria-label={`${selected.label} ${format(selected.percentage)}`}><span style={{ width: `${selected.percentage}%` }} /></div>
          <div className="mt-2 flex justify-between text-xs text-muted-foreground"><span>{locale === "zh" ? "相同特征" : "Same feature"} {format(selected.percentage)}</span><span>{locale === "zh" ? "其余样本" : "Other states"} {format(100 - selected.percentage)}</span></div>
          <dl className="autumn-distribution-split"><div><dt>{locale === "zh" ? "命中特征的小时权重" : "Matching hour weight"}</dt><dd>{selected.hit_weight.toLocaleString()}</dd></div><div><dt>{locale === "zh" ? "完整参考小时权重" : "Total hour weight"}</dt><dd>{selected.total_weight.toLocaleString()}</dd></div></dl>
        </>}
        {family && familyShare != null ? <section className="mt-8 border-t border-border/60 pt-6"><p className="kicker">{locale === "zh" ? "本盘的同类结构" : "THIS CHART’S STRUCTURAL FAMILY"}</p><h4 className="mt-3 text-xl">{locale === "zh" ? family.title : family.title_en ?? family.title}</h4><p className="mt-2 text-sm leading-6 text-muted-foreground">{locale === "zh" ? family.summary : family.summary_en ?? family.summary}</p><p className="mt-3 text-sm text-primary">{locale === "zh" ? "历法样本占比" : "Calendar sample share"} · {format(familyShare)}</p><p className="mt-2 text-xs text-muted-foreground">{consumer.identity.cohort_label}</p></section> : null}
      </article> : null}
    </div>
  </section>
}
