"use client"

import Link from "next/link"
import { motion, useReducedMotion } from "framer-motion"
import { HexagramGlyph } from "@/components/hexagram/hexagram-glyph"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"

export function HomePage() {
  const { messages, toLocalePath } = useI18n()
  const reduceMotion = useReducedMotion()
  const copy = messages.home

  const sampleReading = {
    question: copy.sampleQuestion,
    cast: copy.sampleCast,
    passage: copy.samplePassage,
    interpretation: copy.sampleInterpretation,
  }

  return (
    <main className="space-y-8 sm:space-y-10">
      <section className="grid gap-8 border-b border-border/60 pb-8 lg:grid-cols-[1fr_0.88fr] lg:items-start">
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.35 }}
          className="space-y-6"
        >
          <div className="space-y-4">
            <p className="kicker">{copy.badge}</p>
            <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-foreground sm:text-5xl lg:text-6xl">
              {copy.title}
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-muted-foreground">{copy.subtitle}</p>
            <p className="max-w-2xl border-l-2 border-primary/50 pl-4 text-base font-medium leading-7 text-foreground">
              {copy.promise}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" className="min-h-11 rounded-md px-6 text-sm font-semibold">
              <Link href={toLocalePath("/app")}>{copy.primaryCta}</Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="min-h-11 rounded-md px-6 text-sm font-semibold">
              <Link href={toLocalePath("/library")}>{copy.secondaryCta}</Link>
            </Button>
          </div>

          <div>
            <p className="text-sm font-semibold text-foreground">{copy.intentLabel}</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {copy.intents.map((intent) => (
                <Link
                  key={intent.label}
                  href={toLocalePath(intent.href)}
                  className="group min-h-11 rounded-md border-b border-border/70 px-1 py-3 outline-none transition hover:border-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                >
                  <span className="font-semibold text-foreground group-hover:text-primary">{intent.label}</span>
                  <span className="ml-2 text-sm text-muted-foreground">{intent.hint}</span>
                </Link>
              ))}
            </div>
          </div>

          <p className="max-w-2xl text-xs leading-5 text-muted-foreground">{copy.safety}</p>
        </motion.div>

        <motion.article
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
          transition={{ delay: reduceMotion ? 0 : 0.08, duration: reduceMotion ? 0 : 0.4 }}
          className="rounded-lg border border-border/70 bg-surface p-5 shadow-sm"
        >
          <div className="flex items-center justify-between gap-3 border-b border-border/60 pb-4">
            <p className="kicker">{copy.sampleLabel}</p>
            <span className="text-xs font-semibold text-primary">#03 → #08</span>
          </div>
          <dl className="mt-5 divide-y divide-border/60">
            <SampleRow label={copy.questionLabel} value={sampleReading.question} prominent />
            <SampleRow label={copy.castLabel} value={sampleReading.cast} />
            <div className="grid gap-4 py-4 sm:grid-cols-[6rem_1fr]">
              <HexagramGlyph lines={["yin", "yang", "yin", "yin", "yin", "yang"]} className="w-full gap-2 py-1" lineClassName="h-2" />
              <SampleText label={copy.passageLabel} value={sampleReading.passage} />
            </div>
            <SampleRow label={copy.interpretationLabel} value={sampleReading.interpretation} />
          </dl>
        </motion.article>
      </section>

      <section className="grid gap-5 border-b border-border/60 pb-8 md:grid-cols-[14rem_1fr]">
        <h2 className="text-lg font-semibold text-foreground">{copy.proofTitle}</h2>
        <p className="max-w-3xl text-sm leading-7 text-muted-foreground">{copy.proofBody}</p>
      </section>
    </main>
  )
}

function SampleRow({ label, value, prominent = false }: { label: string; value: string; prominent?: boolean }) {
  return (
    <div className="py-4">
      <dt className="text-xs font-semibold uppercase tracking-[0.16rem] text-muted-foreground">{label}</dt>
      <dd className={prominent ? "mt-2 text-lg font-semibold leading-7 text-foreground" : "mt-2 text-sm leading-6 text-foreground"}>
        {value}
      </dd>
    </div>
  )
}

function SampleText({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.16rem] text-muted-foreground">{label}</p>
      <p className="mt-2 text-base leading-7 text-foreground">{value}</p>
    </div>
  )
}
