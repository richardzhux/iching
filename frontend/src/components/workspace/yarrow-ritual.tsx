"use client"

import type { Locale } from "@/i18n/config"
import type { YarrowChange } from "@/types/api"
import { HexagramGlyph } from "@/components/hexagram/hexagram-glyph"

function StalkPile({ count, label, grouped = false, remainder = 0 }: { count: number; label: string; grouped?: boolean; remainder?: number }) {
  return <div className="yarrow-pile"><strong>{label} <span>{count}</span></strong><svg viewBox={`0 0 250 ${count > 48 ? 145 : 100}`} role="img" aria-label={`${label}: ${count}`}>
    {Array.from({ length: count }, (_, i) => <line key={i} data-remainder={remainder > 0 && i >= count - remainder} x1={8 + (i % 24) * (grouped ? 7.5 : 9.5) + (grouped ? Math.floor((i % 24) / 4) * 8 : 0)} x2={10 + (i % 24) * (grouped ? 7.5 : 9.5) + (grouped ? Math.floor((i % 24) / 4) * 8 : 0)} y1={8 + Math.floor(i / 24) * 47} y2={47 + Math.floor(i / 24) * 47} />)}
  </svg></div>
}

export function YarrowRitual({ locale, change, phase, changeNumber, values, remaining }: { locale: Locale; change: YarrowChange | null; phase: number; changeNumber: number; values: number[]; remaining: number }) {
  const zh = locale === "zh"
  const names = zh ? ["分二", "挂一", "揲四", "归奇"] : ["Divide", "Set one aside", "Count by fours", "Gather remainders"]
  const gathered = phase === 3 && change
  const left = change ? change.left - (gathered ? change.left_remainder : 0) : 49
  const right = change ? change.right - (phase >= 1 ? 1 : 0) - (gathered ? change.right_remainder : 0) : 0
  const held = change ? 49 - change.before + (phase >= 1 ? 1 : 0) + (gathered ? change.left_remainder + change.right_remainder : 0) : 0
  return <section className="yarrow-ritual" aria-label={zh ? "蓍草三变成爻" : "Three changes form one line"}>
    <header><div><span>{zh ? "大衍之数五十，其用四十有九" : "Fifty stalks; forty-nine in use"}</span><h2>{zh ? (changeNumber ? `第 ${changeNumber} 变 · ${names[phase]}` : "虚一 · 四十九策待分") : (changeNumber ? `Change ${changeNumber} · ${names[phase]}` : "One reserved · 49 ready")}</h2></div><div className="yarrow-reserved"><i />{zh ? "虚置一策" : "One reserved"}</div></header>
    <ol className="yarrow-operations">{names.map((name, i) => <li key={name} aria-current={change && phase === i ? "step" : undefined}>{i + 1} · {name}</li>)}</ol>
    <div className="yarrow-piles"><StalkPile count={left} label={zh ? "左策" : "Left"} grouped={phase >= 2} remainder={phase === 2 ? change?.left_remainder : 0} /><StalkPile count={right} label={zh ? "右策" : "Right"} grouped={phase >= 2} remainder={phase === 2 ? change?.right_remainder : 0} /></div>
    <div className="yarrow-accounting" aria-live="polite">{change ? <>
      <p>{zh ? `本变起数 ${change.before} = 左 ${change.left} + 右 ${change.right}` : `${change.before} = left ${change.left} + right ${change.right}`}</p>
      {phase >= 1 && <p>{zh ? `右取一策挂指间，右余 ${change.right - 1}。` : `Set one from the right aside; ${change.right - 1} remain on the right.`}</p>}
      {phase >= 2 && <p>{zh ? `四策一数：左 ${Math.floor((change.left - change.left_remainder) / 4)} 组、余 ${change.left_remainder}；右 ${Math.floor((change.right - 1 - change.right_remainder) / 4)} 组、余 ${change.right_remainder}。` : `Groups of four: left ${Math.floor((change.left - change.left_remainder) / 4)}, remainder ${change.left_remainder}; right ${Math.floor((change.right - 1 - change.right_remainder) / 4)}, remainder ${change.right_remainder}.`}</p>}
      {gathered && <strong>{change.before} − (1 + {change.left_remainder} + {change.right_remainder}) = {change.after} {zh ? "策" : "stalks"}{changeNumber === 3 ? ` ÷ 4 = ${change.after / 4}` : ""}</strong>}
    </> : <p>{zh ? "分为两堆，右取一策；各以四数，合其余策。每爻三变，变后用余策再分。" : "Divide into two piles and set one from the right aside. Count each pile by fours and remove the remainders. Repeat with the remaining stalks three times."}</p>}</div>
    <div className="yarrow-held"><StalkPile count={held} label={zh ? "本爻已置策" : "Set aside this line"} /></div>
    <footer><span>{zh ? `现用 ${remaining} 策 · 已成 ${values.length} / 6 爻` : `${remaining} active · ${values.length} / 6 lines`}</span>{values.length > 0 && <HexagramGlyph lines={[...values].reverse().map((value) => value % 2 ? "1" : "0")} className="w-20 gap-1" lineClassName="h-1" />}</footer>
  </section>
}
