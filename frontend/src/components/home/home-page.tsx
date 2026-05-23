"use client"

import Link from "next/link"
import { motion, useReducedMotion } from "framer-motion"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"

export function HomePage() {
  const { locale, toLocalePath } = useI18n()
  const reduceMotion = useReducedMotion()
  const copy =
    locale === "zh"
      ? {
          badge: "双语易经阅读桌",
          title: "为起卦、研读与复盘而建的易经阅读桌。",
          subtitle: "I Ching Studio is a bilingual reading desk for casting, studying, and keeping a serious record of change.",
          primaryCta: "开始阅读",
          secondaryCta: "浏览经典档案",
          institution: "The most traceable, source-grounded reading environment for the Yi.",
          packetTitle: "一份完整阅读包",
          packetBody: "先看问题、起卦、卦象与动爻，再看经典文本、来源证据、解释与复盘。",
          evidenceTitle: "来源先于解释",
          evidenceBody: "每条解释都尽量回到卦辞、动爻、高岛、英文注释或卦象结构；无法直接归源的内容会作为现代综合。",
          journalTitle: "长期复盘",
          journalBody: "把阅读保存为可回看的记录：状态、重访日期、实际结果和后续追问都留在同一条线索里。",
          safety: "阅读用于反思与判断整理，不作为医疗、法律、金融或命定式建议。",
          sampleLabel: "示例阅读",
          questionLabel: "问题",
          castLabel: "起卦",
          passageLabel: "关键原文",
          interpretationLabel: "来源绑定解释",
          viewFull: "查看完整阅读流程",
        }
      : {
          badge: "Bilingual Yi reading desk",
          title: "A serious reading desk for casting, study, and return.",
          subtitle: "I Ching Studio is a bilingual reading desk for casting, studying, and keeping a serious record of change.",
          primaryCta: "Start a Reading",
          secondaryCta: "Browse Source Library",
          institution: "The most traceable, source-grounded reading environment for the Yi.",
          packetTitle: "A complete reading packet",
          packetBody: "Question, cast, hexagrams, moving lines, received text, source evidence, interpretation, and journal follow-up stay together.",
          evidenceTitle: "Sources before synthesis",
          evidenceBody: "Interpretation points back to judgment text, moving lines, Takashima, English commentary, or symbolic structure before AI synthesis enters.",
          journalTitle: "Return later",
          journalBody: "Save status, revisit date, outcome notes, and follow-up questions so a reading becomes a durable record instead of a one-off answer.",
          safety: "Reflective interpretation, not medical, legal, financial, or fate-certain advice.",
          sampleLabel: "Sample reading",
          questionLabel: "Question",
          castLabel: "Cast",
          passageLabel: "Received text",
          interpretationLabel: "Source-linked interpretation",
          viewFull: "View the full reading flow",
        }

  const sampleReading = {
    question:
      locale === "zh"
        ? "我应该怎样理解一个困难项目的开端？"
        : "What should I understand about beginning a difficult project?",
    cast:
      locale === "zh"
        ? "第 3 卦 屯，初爻动 → 第 8 卦 比"
        : "Hexagram 3, Difficulty at the Beginning, line 1 → Hexagram 8, Holding Together",
    passage:
      locale === "zh"
        ? "磐桓，利居贞，利建侯。"
        : "Difficulty at the beginning asks for steadiness before alliance.",
    interpretation:
      locale === "zh"
        ? "主证据不是整卦散读，而是初爻：先稳定位置、建立负责人，再进入比卦的协作关系。"
        : "The decisive evidence is the first moving line: stabilize the starting position before seeking the alliance shown by Hexagram 8.",
  }

  const pillars = [
    { title: copy.packetTitle, body: copy.packetBody },
    { title: copy.evidenceTitle, body: copy.evidenceBody },
    { title: copy.journalTitle, body: copy.journalBody },
  ]

  return (
    <main className="space-y-10">
      <section className="grid min-h-[calc(100vh-11rem)] gap-8 lg:grid-cols-[1fr_0.92fr] lg:items-center">
	        <motion.div
	          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
	          animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
	          transition={{ duration: reduceMotion ? 0 : 0.35 }}
          className="space-y-7"
        >
          <div className="inline-flex items-center gap-2 rounded-md border border-border/70 bg-surface px-3 py-1 text-xs font-semibold text-muted-foreground">
            <span className="size-2 rounded-full bg-primary" />
            {copy.badge}
          </div>
          <div className="space-y-4">
            <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-foreground sm:text-5xl lg:text-6xl">
              {copy.title}
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-muted-foreground">{copy.subtitle}</p>
            <p className="max-w-2xl text-base leading-7 text-foreground">{copy.institution}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" className="rounded-md px-6 text-sm font-semibold">
              <Link href={toLocalePath("/app")}>{copy.primaryCta}</Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="rounded-md px-6 text-sm font-semibold">
              <Link href={toLocalePath("/library")}>{copy.secondaryCta}</Link>
            </Button>
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
            <span className="rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-xs font-semibold text-primary">
              #03 → #08
            </span>
          </div>
          <dl className="mt-5 space-y-5">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{copy.questionLabel}</dt>
              <dd className="mt-2 text-lg font-semibold leading-7 text-foreground">{sampleReading.question}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{copy.castLabel}</dt>
              <dd className="mt-2 text-sm leading-6 text-foreground">{sampleReading.cast}</dd>
            </div>
            <div className="grid gap-3 rounded-md border border-border/60 bg-surface-elevated p-4 sm:grid-cols-[7rem_1fr]">
              <HexMini lines={["yin", "yang", "yin", "yin", "yin", "yang"]} />
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{copy.passageLabel}</p>
                <p className="mt-2 text-base leading-7 text-foreground">{sampleReading.passage}</p>
              </div>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{copy.interpretationLabel}</dt>
              <dd className="mt-2 text-sm leading-6 text-foreground">{sampleReading.interpretation}</dd>
            </div>
          </dl>
          <Button asChild variant="outline" className="mt-5 w-full rounded-md">
            <Link href={toLocalePath("/app")}>{copy.viewFull}</Link>
          </Button>
        </motion.article>
      </section>

      <section className="grid gap-3 md:grid-cols-3">
        {pillars.map((pillar) => (
          <article key={pillar.title} className="rounded-lg border border-border/60 bg-surface p-5">
            <h2 className="text-base font-semibold text-foreground">{pillar.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{pillar.body}</p>
          </article>
        ))}
      </section>
    </main>
  )
}

function HexMini({ lines }: { lines: Array<"yang" | "yin"> }) {
  return (
    <div className="grid gap-2 py-1" aria-hidden="true">
      {lines.map((line, index) => (
        <span
          key={`${line}-${index}`}
          className={
            line === "yang"
              ? "h-2 rounded bg-foreground"
              : "h-2 rounded bg-gradient-to-r from-foreground from-40% via-transparent via-40% to-foreground to-60%"
          }
        />
      ))}
    </div>
  )
}
