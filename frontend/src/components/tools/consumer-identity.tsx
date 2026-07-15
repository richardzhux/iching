"use client"

import { useId } from "react"
import { cn } from "@/lib/utils"

export type ConsumerLocale = "en" | "zh"

export interface ConsumerIdentitySummary {
  system_title: string
  archetype_title: string
  archetype_subtitle: string
  fusion_title?: string | null
  main_score?: number
  global_percentile?: number
  global_top_percentage?: number
  cohort_percentile?: number
  cohort_top_percentage?: number
  cohort_label?: string
}

export interface ConsumerSubjectScore {
  key: string
  label: string
  score?: number
  global_percentile?: number
  global_top_percentage?: number
  cohort_percentile?: number
  cohort_top_percentage?: number
  headline: string
  path_label?: string
  path_summary?: string
}

export interface ConsumerFingerprint {
  id: string
  title: string
  detail: string
  rarity_label: string
  top_percentage: number
  incidence_percentage?: number
}

export interface ConsumerStructuralTwin {
  family_id: string
  title: string
  share_percentage: number
  summary: string
  representatives: string[]
}

export interface ConsumerIdentityProfile {
  identity: ConsumerIdentitySummary
  subjects: ConsumerSubjectScore[]
  fingerprints: ConsumerFingerprint[]
  twin: ConsumerStructuralTwin | null
}

interface ConsumerComparisonActionBase {
  label: string
  ariaLabel?: string
}

export type ConsumerComparisonAction =
  | (ConsumerComparisonActionBase & { href: string; onClick?: never })
  | (ConsumerComparisonActionBase & { href?: never; onClick: () => void })

export interface ConsumerIdentityProps {
  profile: ConsumerIdentityProfile
  locale?: ConsumerLocale
  comparisonAction?: ConsumerComparisonAction
  className?: string
}

function formatNumber(value: number, locale: ConsumerLocale, maximumFractionDigits = 1) {
  return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", {
    maximumFractionDigits,
  }).format(value)
}

function incidenceLabel(value: number, locale: ConsumerLocale) {
  const formatted = formatNumber(value, locale)
  return locale === "zh" ? `同值约 ${formatted}%` : `${formatted}% same-value incidence`
}

export interface ConsumerSubjectPath {
  label: string
  title: string
  description: string
}

function includesAny(value: string, terms: string[]) {
  return terms.some((term) => value.toLowerCase().includes(term.toLowerCase()))
}

/**
 * Turn current and legacy score-era payloads into a descriptive consumer path.
 * Numeric fields on old snapshots never shape the label or copy shown here.
 */
export function describeConsumerSubject(subject: ConsumerSubjectScore, locale: ConsumerLocale): ConsumerSubjectPath {
  const key = subject.key.toLowerCase()
  const headline = subject.headline || subject.label
  if (subject.path_label && subject.path_summary) {
    const labels: Record<string, { zh: string; en: string }> = {
      career: { zh: "事业主场", en: "Career lane" },
      wealth: { zh: "财富路径", en: "Wealth path" },
      relationship: { zh: "关系磁场", en: "Relationship style" },
      health: { zh: "身心节奏", en: "Mind-body rhythm" },
    }
    const localized = labels[key]
    return {
      label: localized ? localized[locale] : subject.label,
      title: subject.path_label,
      description: subject.path_summary,
    }
  }

  if (key === "career" || includesAny(subject.label, ["事业", "career"])) {
    if (includesAny(headline, ["食伤", "伤官", "食神", "output", "expression"])) {
      return locale === "zh"
        ? { label: "事业主场", title: "创造表达型", description: "更容易通过作品、表达与解决新问题建立自己的位置。" }
        : { label: "Career lane", title: "Creative expression", description: "You build momentum through ideas, expression, and solving new problems." }
    }
    if (includesAny(headline, ["印星", "正印", "偏印", "resource", "knowledge"])) {
      return locale === "zh"
        ? { label: "事业主场", title: "专业积累型", description: "专业能力、学习深度与长期可信度，是更稳定的事业支点。" }
        : { label: "Career lane", title: "Expertise builder", description: "Depth, learning, and long-term credibility are your steadier career anchors." }
    }
    if (includesAny(headline, ["官杀", "正官", "七杀", "authority", "officer"])) {
      return locale === "zh"
        ? { label: "事业主场", title: "责任推进型", description: "在有目标、有责任边界的环境里，更容易把事情持续向前推进。" }
        : { label: "Career lane", title: "Purposeful operator", description: "Clear goals and responsibility help you keep complex work moving." }
    }
    return locale === "zh"
      ? { label: "事业主场", title: "主动开拓型", description: "事业动力更适合落在主动选择、持续行动与阶段突破上。" }
      : { label: "Career lane", title: "Active builder", description: "Your career momentum grows through initiative, consistent action, and timely breakthroughs." }
  }

  if (key === "wealth" || includesAny(subject.label, ["财富", "wealth"])) {
    const hidden = includesAny(headline, ["藏干", "藏见", "深藏", "hidden"])
    const visible = includesAny(headline, ["明干", "明透", "透干", "visible"])
    if (hidden && !visible) {
      return locale === "zh"
        ? { label: "财富路径", title: "潜藏兑现型", description: "资源更常藏在能力、关系与长期积累里，等待合适阶段兑现；深藏不代表贫乏。" }
        : { label: "Wealth path", title: "Quiet compounding", description: "Resources tend to build through skill, relationships, and time before becoming visible; hidden does not mean lacking." }
    }
    if (includesAny(headline, ["比劫", "peer"])) {
      return locale === "zh"
        ? { label: "财富路径", title: "协作竞争型", description: "资源往往伴随合作与竞争流动，重点在边界、分配与把机会留在自己手里。" }
        : { label: "Wealth path", title: "Collaborative competition", description: "Resources move through both cooperation and competition, making boundaries and allocation especially important." }
    }
    if (visible) {
      return locale === "zh"
        ? { label: "财富路径", title: "外显经营型", description: "资源意识更容易被看见，适合通过明确目标、经营与现实结果持续积累。" }
        : { label: "Wealth path", title: "Visible builder", description: "Your resource orientation is easier to see and grows through clear goals, stewardship, and tangible results." }
    }
    return locale === "zh"
      ? { label: "财富路径", title: "长期积累型", description: "财富更适合被理解为积累方式与兑现节奏，而不是一张命盘里的高低成绩。" }
      : { label: "Wealth path", title: "Long-term compounding", description: "This describes how resources accumulate and surface, not a grade for wealth." }
  }

  if (key === "relationship" || key === "relationships" || includesAny(subject.label, ["感情", "关系", "relationship", "love"])) {
    if (includesAny(headline, ["桃花", "红鸾", "天喜", "红艳", "romance", "attraction"])) {
      return locale === "zh"
        ? { label: "关系磁场", title: "吸引表达型", description: "关系信号较容易显现，关键在把吸引力转化为真实、稳定的相处。" }
        : { label: "Relationship style", title: "Expressive attraction", description: "Connection signals surface readily; the key is turning attraction into a real, steady bond." }
    }
    if (includesAny(headline, ["夫妻宫", "配偶星", "互动", "spouse", "partner"])) {
      return locale === "zh"
        ? { label: "关系磁场", title: "深度互动型", description: "亲密关系容易牵动重要选择，也更需要在互动中建立清楚的理解与边界。" }
        : { label: "Relationship style", title: "Deep interaction", description: "Close relationships can shape major choices, making mutual understanding and boundaries especially important." }
    }
    return locale === "zh"
      ? { label: "关系磁场", title: "共同成长型", description: "关系主题更适合从相处方式、选择联动与共同成长来理解。" }
      : { label: "Relationship style", title: "Growing together", description: "Your relationship story is better understood through interaction, shared choices, and mutual growth." }
  }

  if (key === "health" || includesAny(subject.label, ["健康", "health", "身心"])) {
    if (includesAny(headline, ["集中", "承压", "冲", "刑", "害", "破", "pressure", "concentrat"])) {
      return locale === "zh"
        ? { label: "身心节奏", title: "张弛调节型", description: "结构里的集中与牵动较明显，适合重视节奏切换、恢复空间与稳定日常。" }
        : { label: "Mind-body rhythm", title: "Active regulation", description: "Concentrated and interacting signals make rhythm, recovery, and steady routines especially valuable." }
    }
    return locale === "zh"
      ? { label: "身心节奏", title: "稳定续航型", description: "这一栏描述传统五行中的节奏与恢复方式，不把命盘结构当作健康成绩。" }
      : { label: "Mind-body rhythm", title: "Steady endurance", description: "This describes rhythm and recovery in the chart rather than grading real-world health." }
  }

  return { label: subject.label, title: headline, description: locale === "zh" ? "这是一种命盘表达路径，不代表人生优劣。" : "This is a chart expression path, not a grade for a life." }
}

function ComparisonEntry({ action }: { action: ConsumerComparisonAction }) {
  const className = "inline-flex min-h-11 items-center justify-center rounded-xl border border-primary/35 bg-primary/[0.06] px-4 py-2.5 text-sm font-semibold text-primary transition hover:border-primary/60 hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"

  if (action.href) {
    return <a href={action.href} aria-label={action.ariaLabel} className={className}>{action.label}<span aria-hidden="true" className="ml-2">→</span></a>
  }

  return <button type="button" aria-label={action.ariaLabel} onClick={action.onClick} className={className}>{action.label}<span aria-hidden="true" className="ml-2">→</span></button>
}

export function ConsumerIdentity({ profile, locale = "zh", comparisonAction, className }: ConsumerIdentityProps) {
  const headingId = `${useId()}-consumer-identity-title`
  const { identity, subjects, fingerprints } = profile
  const title = identity.fusion_title || identity.archetype_title

  return (
    <section
      data-consumer-share-card
      aria-labelledby={headingId}
      className={cn("min-w-0 overflow-hidden rounded-3xl border border-primary/25 bg-surface/95 shadow-[var(--surface-shadow)]", className)}
    >
      <header className="imperial-highlight-panel min-w-0 border-0 border-b border-primary/20 px-5 py-7 shadow-none sm:px-7 lg:px-9 lg:py-9">
        <div className="min-w-0">
          <p className="kicker">{identity.system_title}</p>
          <h2 id={headingId} className="mt-3 text-balance text-3xl font-semibold leading-tight sm:text-4xl">{title}</h2>
          {identity.fusion_title ? <p className="mt-2 text-sm font-semibold text-primary">{identity.archetype_title}</p> : null}
          <p className="mt-4 max-w-3xl text-pretty text-base font-semibold leading-7 sm:text-lg sm:leading-8">{identity.archetype_subtitle}</p>
        </div>
      </header>

      <div role="group" className="grid min-w-0 gap-px border-b border-border/60 bg-border/55 sm:grid-cols-2 lg:grid-cols-4" aria-label={locale === "zh" ? "四条人生路径" : "Four life paths"}>
        {subjects.map((subject, index) => (
          <SubjectPathCard key={subject.key} subject={subject} locale={locale} index={index} />
        ))}
      </div>

      <div className="grid min-w-0">
        <section className="min-w-0 px-5 py-7 sm:px-7 lg:px-9" aria-labelledby={`${headingId}-fingerprints`}>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="kicker">{locale === "zh" ? "特别结构" : "DISTINCTIVE STRUCTURES"}</p>
              <h3 id={`${headingId}-fingerprints`} className="mt-2 text-xl font-semibold">{locale === "zh" ? "命盘中较有辨识度的特征" : "Distinctive patterns in your chart"}</h3>
            </div>
            <span className="text-xs tabular-nums text-muted-foreground">{fingerprints.length}</span>
          </div>
          <ol className="mt-5 divide-y divide-border/55 border-y border-border/55">
            {fingerprints.map((fingerprint, index) => (
              <li key={fingerprint.id} className="grid min-w-0 grid-cols-[2rem_minmax(0,1fr)] gap-3 py-4">
                <span aria-hidden="true" className="pt-0.5 text-sm font-semibold tabular-nums text-primary/70">{String(index + 1).padStart(2, "0")}</span>
                <div className="min-w-0">
                  <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                    <h4 className="font-semibold leading-6">{fingerprint.title}</h4>
                    <p className="text-xs font-semibold text-primary">{fingerprint.rarity_label} · {incidenceLabel(fingerprint.incidence_percentage ?? fingerprint.top_percentage, locale)}</p>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{fingerprint.detail}</p>
                </div>
              </li>
            ))}
          </ol>
          <p className="mt-4 text-xs leading-5 text-muted-foreground">{locale === "zh" ? "少见程度只说明结构辨识度，不代表吉凶或人生高低。" : "Rarity describes distinctiveness, not fortune or the quality of a life."}</p>
          {comparisonAction ? <div data-export-exclude className="mt-6"><ComparisonEntry action={comparisonAction} /></div> : null}
        </section>
      </div>
    </section>
  )
}

function SubjectPathCard({ subject, locale, index }: { subject: ConsumerSubjectScore; locale: ConsumerLocale; index: number }) {
  const path = describeConsumerSubject(subject, locale)
  return (
    <article className="min-w-0 bg-surface px-4 py-5 sm:px-5">
      <div className="flex items-center gap-2">
        <span aria-hidden="true" className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{index + 1}</span>
        <p className="text-xs font-semibold tracking-[0.12em] text-muted-foreground">{path.label}</p>
      </div>
      <h3 className="mt-3 text-xl font-semibold leading-tight text-primary">{path.title}</h3>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{path.description}</p>
      <p className="mt-4 border-t border-border/50 pt-3 text-xs leading-5 text-foreground/75">{subject.headline}</p>
    </article>
  )
}
