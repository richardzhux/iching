"use client"

import Link from "next/link"
import { useState } from "react"
import type { Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { hexagramLines } from "@/lib/hexagram-library"
import { relatedHexagramBinaries, type RelationKind } from "@/lib/hexagram-relations"
import { HexagramGlyph } from "./hexagram-glyph"

const LABELS: Record<RelationKind, { zh: string; en: string; ruleZh: string; ruleEn: string }> = {
  main: { zh: "本卦", en: "Primary", ruleZh: "本次起卦所得的六爻，由初爻向上排列。", ruleEn: "The six cast lines, ordered from the first line upward." },
  changed: { zh: "变卦 · 之卦", en: "Changed", ruleZh: "只变动爻：老阳九变阴，老阴六变阳；七、八保持原状。", ruleEn: "Only moving lines change: nine becomes yin and six becomes yang; seven and eight remain." },
  mutual: { zh: "互卦", en: "Nuclear", ruleZh: "取本卦二、三、四爻作下卦，三、四、五爻作上卦。这里显示本卦的互体。", ruleEn: "Primary lines 2–3–4 form the lower trigram; lines 3–4–5 form the upper. This is the primary hexagram’s nuclear form." },
  inverse: { zh: "错卦", en: "Complement", ruleZh: "本卦六爻阴阳全部相反，爻位不变。", ruleEn: "Reverse the polarity of all six primary lines without changing their positions." },
  reverse: { zh: "综卦", en: "Reversed", ruleZh: "将本卦上下颠倒：初与上、二与五、三与四交换位置。", ruleEn: "Turn the primary hexagram upside down: swap 1↔6, 2↔5 and 3↔4." },
}

export function HexagramRelations({ values, locale }: { values: number[]; locale: Locale }) {
  const [selected, setSelected] = useState<RelationKind>("main")
  const relations = relatedHexagramBinaries(values)
  if (!relations.length) return null
  const current = relations.find((item) => item.kind === selected) ?? relations[0]
  return <section className="hexagram-relations" aria-label={locale === "zh" ? "本变互错综" : "Related hexagrams"}>
    <header><p className="kicker">{locale === "zh" ? "六爻之间" : "Six lines, related forms"}</p><h2>{locale === "zh" ? "本、变、互、错、综" : "The primary and its related forms"}</h2></header>
    <div className="hexagram-relation-choices" role="group" aria-label={locale === "zh" ? "选择关联卦" : "Select a related form"}>
      {relations.map((item) => <button type="button" key={item.kind} aria-pressed={current.kind === item.kind} disabled={!item.entry} onClick={() => setSelected(item.kind)}>
        <span>{LABELS[item.kind][locale]}</span>
        {item.binary ? <HexagramGlyph lines={hexagramLines(item.binary)} className="w-20 gap-1.5" lineClassName="h-1.5" /> : <span className="hexagram-no-change">{locale === "zh" ? "无动爻" : "No moving lines"}</span>}
        <strong>{(locale === "zh" ? item.entry?.nameZh : item.entry?.titleEn) ?? (locale === "zh" ? "本卦不变" : "Primary remains")}</strong>
        {item.entry ? <small>{locale === "zh" ? `第 ${item.entry.number} 卦` : `${item.entry.number} · ${item.entry.titleEn}`}</small> : null}
      </button>)}
    </div>
    <div className="hexagram-relation-explanation" aria-live="polite">
      <p><strong>{LABELS[current.kind][locale]}</strong>{locale === "zh" ? LABELS[current.kind].ruleZh : LABELS[current.kind].ruleEn}</p>
      {current.entry ? <Link href={withLocale(locale, `/hexagram/${current.entry.slug}`)}>{locale === "zh" ? `读${current.entry.shortNameZh}卦经文` : "Read this hexagram"} →</Link> : null}
    </div>
  </section>
}
