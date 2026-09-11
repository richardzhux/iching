"use client"

import { useState } from "react"
import { lineName } from "@/lib/hexagram-relations"
import type { Locale } from "@/i18n/config"

export function HomeHexagram({ locale }: { locale: Locale }) {
  const [changed, setChanged] = useState(false)
  const values = changed ? [8, 8, 8, 8, 7, 8] : [9, 8, 8, 8, 7, 8]
  const zh = locale === "zh"
  return <section className="autumn-paper-hexagram" aria-label={zh ? "屯卦初九变比卦示意" : "Illustration: Difficulty at the Beginning changes to Holding Together"}>
    <div className="paper-hexagram-heading"><span>{zh ? "卦象示意" : "An example of change"}</span><div role="group" aria-label={zh ? "本卦与变卦" : "Primary and changed"}><button type="button" aria-pressed={!changed} onClick={() => setChanged(false)}>{zh ? "本卦 · 屯" : "Primary · 3"}</button><button type="button" aria-pressed={changed} onClick={() => setChanged(true)}>{zh ? "变卦 · 比" : "Changed · 8"}</button></div></div>
    <div className="paper-hexagram-body">
      <svg className="paper-trigram-scenery" viewBox="0 0 580 380" aria-hidden="true">
        {[0, 1, 2, 3].map((n) => <path key={n} d={`M20 ${65 + n * 14} Q90 ${40 + n * 14} 160 ${65 + n * 14} T300 ${65 + n * 14} T440 ${65 + n * 14} T580 ${65 + n * 14}`} />)}
        {changed ? [0, 1, 2].map((n) => <path key={n} d={`M20 ${265 + n * 20} Q150 ${235 + n * 20} 280 ${265 + n * 20} T580 ${265 + n * 20}`} />) : <path d="M450 212 L419 263 L454 255 L419 319" className="paper-thunder" />}
      </svg>
      <div className="paper-six-lines">{[...values].reverse().map((value, i) => <div key={i} className="paper-line" data-moving={!changed && i === 5}><span className="paper-line-name">{lineName(6 - i, value % 2 === 1)}</span><span className="paper-line-bars">{value % 2 ? <i /> : <><i /><i /></>}</span><span className="paper-line-motion">{i === 5 ? (!changed ? "○" : "←") : ""}</span></div>)}</div>
      <div className="paper-trigram-labels"><p><strong>坎 ☵</strong><span>{zh ? "上卦 · 水" : "Above · Water"}</span></p><p><strong>{changed ? "坤 ☷" : "震 ☳"}</strong><span>{zh ? (changed ? "下卦 · 地" : "下卦 · 雷") : (changed ? "Below · Earth" : "Below · Thunder")}</span></p></div>
    </div>
    <h2>{zh ? (changed ? "水地比" : "水雷屯") : (changed ? "Holding Together" : "Difficulty at the Beginning")}</h2>
    <p>{zh ? (changed ? "初九由阳变阴，下震成坤；上坎不变。" : "初九为动爻。水在雷上，动于险中。") : (changed ? "The first line becomes yin: Thunder becomes Earth; Water remains." : "The first line is moving. Water above, Thunder below.")}</p>
  </section>
}
