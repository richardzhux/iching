"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { ArrowRight } from "lucide-react"
import { HomeHexagram } from "@/components/autumn/home-hexagram"
import { AutumnFrame } from "@/components/autumn/autumn-frame"
import { HexagramGlyph } from "@/components/hexagram/hexagram-glyph"
import { useI18n } from "@/components/providers/i18n-provider"
import { useWorkspaceStore } from "@/lib/store"

export function HomePage() {
  const { messages, locale, toLocalePath } = useI18n()
  const router = useRouter()
  const question = useWorkspaceStore((state) => state.form.userQuestion)
  const updateForm = useWorkspaceStore((state) => state.updateForm)
  const copy = messages.home
  const begin = () => router.push(toLocalePath("/app"))

  return (
    <div>
      <AutumnFrame sceneContent={<HomeHexagram locale={locale} />} caption={locale === "zh" ? "一问 · 六爻 · 万般变化" : "One question. Six lines. A different perspective."}>
        <h1 className="autumn-title" lang="zh">一念之间</h1>
          <p className="autumn-eyebrow">{locale === "zh" ? "以一念，观万象" : "A moment of change"}</p>

        <form onSubmit={(event) => { event.preventDefault(); begin() }}>
          <label htmlFor="home-question" className="autumn-question-label">{locale === "zh" ? "此刻，你想理解什么？" : "What would you like to understand?"}</label>
          <textarea id="home-question" className="autumn-textarea" value={question} onChange={(event) => updateForm("userQuestion", event.target.value)} maxLength={2000} rows={4} placeholder={locale === "zh" ? "我该如何理解眼前的变化……" : "What should I understand about this change…"} />
          <button type="submit" className="autumn-primary mt-5">{locale === "zh" ? "开始起卦" : "Begin a reading"}<ArrowRight size={15} aria-hidden="true" /></button>
        </form>
        <div className="autumn-actions-row"><span className="autumn-link">{locale === "zh" ? "三枚铜钱 · 自下而上" : "Three coins · six lines"}</span><Link className="autumn-link" href={toLocalePath("/library")}>{locale === "zh" ? "先读经典" : "Explore the texts"}</Link></div>
        <div className="autumn-method-row"><p className="autumn-footnote !mt-0">{locale === "zh" ? "循经典之意，照自己的处境。" : "Rooted in the classical texts. Open to your own reflection."}</p></div>
      </AutumnFrame>
      <div className="autumn-below">
        <section className="autumn-chapter">
          <div><p className="autumn-eyebrow">{locale === "zh" ? "从何问起" : "Where to begin"}</p><h2 className="mt-4">{locale === "zh" ? "问一件，真正\n放在心上的事。" : "Begin with what is on your mind."}</h2><p className="mt-5 text-sm leading-7 text-muted-foreground">{copy.promise}</p></div>
          <div>{copy.intents.map((intent) => <Link key={intent.label} href={toLocalePath(intent.href)} className="group flex items-center justify-between gap-5 border-b border-border/60 py-5"><span><span className="text-base font-medium">{intent.label}</span><span className="mt-1 block text-xs leading-6 text-muted-foreground">{intent.hint}</span></span><ArrowRight size={16} className="text-primary transition-transform group-hover:translate-x-1" aria-hidden="true" /></Link>)}</div>
        </section>
        <section className="autumn-chapter">
          <div><p className="autumn-eyebrow">{copy.sampleLabel}</p><h2 className="mt-4">{locale === "zh" ? "一卦，如何读。" : "A reading, unfolded."}</h2><p className="mt-5 text-sm leading-7 text-muted-foreground">{copy.proofBody}</p><Link href={toLocalePath("/library")} className="autumn-link mt-6 inline-block">{copy.secondaryCta} →</Link></div>
          <article><p className="autumn-eyebrow">#03 → #08</p><dl className="divide-y divide-border/60"><SampleRow label={copy.questionLabel} value={copy.sampleQuestion} prominent /><SampleRow label={copy.castLabel} value={copy.sampleCast} /><div className="grid grid-cols-[70px_1fr] items-start gap-7 py-5"><HexagramGlyph lines={["yin", "yang", "yin", "yin", "yin", "yang"]} className="w-full gap-2 py-1" lineClassName="h-2" /><div><dt className="autumn-eyebrow">{copy.passageLabel}</dt><dd className="mt-2 text-sm leading-7">{copy.samplePassage}</dd></div></div><SampleRow label={copy.interpretationLabel} value={copy.sampleInterpretation} /></dl></article>
        </section>
        <p className="max-w-3xl text-xs leading-6 text-muted-foreground">{copy.safety}</p>
      </div>
    </div>
  )
}

function SampleRow({ label, value, prominent = false }: { label: string; value: string; prominent?: boolean }) {
  return <div className="py-5"><dt className="autumn-eyebrow">{label}</dt><dd className={prominent ? "mt-2 text-lg leading-8" : "mt-2 text-sm leading-7"}>{value}</dd></div>
}
