"use client"

import { Coins, Flower2, PencilLine, Sprout } from "lucide-react"
import { cn } from "@/lib/utils"

const METHODS = [
  { key: "c", zh: "三枚铜钱", en: "Three coins", hintZh: "一掷一爻", hintEn: "Toss, then reflect", icon: Coins },
  { key: "s", zh: "五十蓍草", en: "Yarrow stalks", hintZh: "三变成一爻", hintEn: "Three changes per line", icon: Sprout },
  { key: "m", zh: "梅花易数", en: "Plum blossom", hintZh: "以时取象", hintEn: "A moment becomes a sign", icon: Flower2 },
  { key: "x", zh: "自定义", en: "Your own cast", hintZh: "亲手录入六爻", hintEn: "Set the six lines", icon: PencilLine },
] as const

export function CastingMethodPicker({ locale, value, available, onChange }: {
  locale: "zh" | "en"
  value: string
  available: string[]
  onChange: (value: string) => void
}) {
  return <div className="autumn-method-picker" role="group" aria-label={locale === "zh" ? "起卦方法" : "Casting method"}>
    {METHODS.filter((method) => available.includes(method.key)).map((method) => <button key={method.key} type="button" aria-pressed={value === method.key} onClick={() => onChange(method.key)}>
      <method.icon size={20} strokeWidth={1.5} aria-hidden="true" />
      <span><strong>{locale === "zh" ? method.zh : method.en}</strong><small>{locale === "zh" ? method.hintZh : method.hintEn}</small></span>
    </button>)}
  </div>
}

const LINE_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

export function ManualLineEditor({ locale, values, raw, onLineChange, onRawChange }: {
  locale: "zh" | "en"
  values: number[]
  raw: string
  onLineChange: (index: number, value: number) => void
  onRawChange: (value: string) => void
}) {
  return <div className="autumn-line-editor">
    <p>{locale === "zh" ? "点卦爻切换阴阳，点圆圈标记动爻。" : "Tap a line to change yin and yang; use the circle to mark change."}</p>
    <div className="autumn-line-editor-rows">
      {[5, 4, 3, 2, 1, 0].map((index) => {
        const value = values[index]
        const moving = value === 6 || value === 9
        const yang = value === 7 || value === 9
        const name = locale === "zh" ? LINE_NAMES[index] : `Line ${index + 1}`
        const state = !value ? (locale === "zh" ? "未设定" : "unset") : locale === "zh" ? `${yang ? "阳" : "阴"}${moving ? "，动爻" : ""}` : `${yang ? "yang" : "yin"}${moving ? ", changing" : ""}`
        return <div className="autumn-line-editor-row" key={index}>
          <span>{name}</span>
          <button type="button" className={cn("autumn-line-ink", !value && "is-empty")} data-moving={moving} aria-label={`${name}：${state}，${locale === "zh" ? "切换阴阳" : "toggle yin and yang"}`} onClick={() => onLineChange(index, !value ? 7 : yang ? (moving ? 6 : 8) : (moving ? 9 : 7))}>
            {!value || yang ? <i /> : <><i /><i /></>}
          </button>
          <button type="button" className="autumn-moving-mark" disabled={!value} aria-pressed={moving} aria-label={`${name}：${locale === "zh" ? "标记动爻" : "mark as changing"}`} onClick={() => onLineChange(index, moving ? (yang ? 7 : 8) : (yang ? 9 : 6))}><span aria-hidden="true">{moving ? "●" : "○"}</span></button>
          <small>{value || "—"}</small>
        </div>
      })}
    </div>
    <div className="autumn-line-input"><label htmlFor="manual-lines-quick">{locale === "zh" ? "或输入六位数字" : "Or enter six digits"}</label><input id="manual-lines-quick" inputMode="numeric" maxLength={6} autoComplete="off" placeholder="678789" value={raw.includes("0") ? "" : raw} onChange={(event) => onRawChange(event.target.value.replace(/[^6-9]/g, "").slice(0, 6))} /><span>{locale === "zh" ? "6 老阴 · 7 少阳 · 8 少阴 · 9 老阳，自下而上" : "6 old yin · 7 yang · 8 yin · 9 old yang, bottom to top"}</span></div>
  </div>
}

const TRIGRAM_NAMES = ["", "乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
const TRIGRAM_EN = ["", "Heaven", "Lake", "Fire", "Thunder", "Wind", "Water", "Mountain", "Earth"]
export function MeihuaSteps({ locale, step, upper, lower, moving }: {
  locale: "zh" | "en"; step: number; upper?: number | null; lower?: number | null; moving?: number | null
}) {
  const names = locale === "zh" ? ["上卦", "下卦", "动爻"] : ["Upper", "Lower", "Changing"]
  const values = [upper ? (locale === "zh" ? TRIGRAM_NAMES[upper] : TRIGRAM_EN[upper]) : "—", lower ? (locale === "zh" ? TRIGRAM_NAMES[lower] : TRIGRAM_EN[lower]) : "—", moving ? (locale === "zh" ? `第 ${moving} 爻` : `Line ${moving}`) : "—"]
  return <ol className="autumn-meihua-steps" aria-label={locale === "zh" ? "梅花成卦步骤" : "Plum blossom casting steps"}>
    {names.map((name, index) => <li key={name} data-complete={step > index}><small>{String(index + 1).padStart(2, "0")} · {name}</small><strong>{step > index ? values[index] : "—"}</strong></li>)}
  </ol>
}
