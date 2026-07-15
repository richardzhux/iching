"use client"

import { useId } from "react"
import { cn } from "@/lib/utils"

export type ConsumerLocale = "en" | "zh"

export interface ConsumerIdentitySummary {
  system_title: string
  archetype_title: string
  archetype_subtitle: string
  fusion_title?: string | null
  main_score: number
  global_percentile: number
  global_top_percentage: number
  cohort_percentile: number
  cohort_top_percentage: number
  cohort_label: string
}

export interface ConsumerSubjectScore {
  key: string
  label: string
  score: number
  global_percentile: number
  global_top_percentage: number
  cohort_percentile: number
  cohort_top_percentage: number
  headline: string
}

export interface ConsumerFingerprint {
  id: string
  title: string
  detail: string
  rarity_label: string
  top_percentage: number
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

function boundedPercentage(value: number) {
  return Math.min(100, Math.max(0, Number.isFinite(value) ? value : 0))
}

function topPercentageLabel(value: number, locale: ConsumerLocale) {
  const formatted = formatNumber(value, locale)
  return locale === "zh" ? `前 ${formatted}%` : `Top ${formatted}%`
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
  const { identity, subjects, fingerprints, twin } = profile
  const title = identity.fusion_title || identity.archetype_title
  const score = boundedPercentage(identity.main_score)

  return (
    <section
      data-consumer-share-card
      aria-labelledby={headingId}
      className={cn("min-w-0 overflow-hidden rounded-3xl border border-primary/25 bg-surface/95 shadow-[var(--surface-shadow)]", className)}
    >
      <header className="imperial-highlight-panel grid min-w-0 gap-7 border-0 border-b border-primary/20 px-5 py-7 shadow-none sm:px-7 lg:grid-cols-[minmax(0,1fr)_10rem] lg:items-center lg:px-9 lg:py-9">
        <div className="min-w-0">
          <p className="kicker">{identity.system_title}</p>
          <h2 id={headingId} className="mt-3 text-balance text-3xl font-semibold leading-tight sm:text-4xl">{title}</h2>
          {identity.fusion_title ? <p className="mt-2 text-sm font-semibold text-primary">{identity.archetype_title}</p> : null}
          <p className="mt-4 max-w-3xl text-pretty text-base font-semibold leading-7 sm:text-lg sm:leading-8">{identity.archetype_subtitle}</p>
          <dl className="mt-6 flex min-w-0 flex-wrap gap-x-7 gap-y-3 text-sm">
            <div>
              <dt className="text-xs text-muted-foreground">{locale === "zh" ? "全部样本" : "All samples"}</dt>
              <dd className="mt-1 font-semibold text-primary">{topPercentageLabel(identity.global_top_percentage, locale)}</dd>
            </div>
            <div className="min-w-0">
              <dt className="truncate text-xs text-muted-foreground">{identity.cohort_label}</dt>
              <dd className="mt-1 font-semibold text-primary">{topPercentageLabel(identity.cohort_top_percentage, locale)}</dd>
            </div>
          </dl>
        </div>
        <div className="flex items-end justify-between gap-5 border-t border-primary/20 pt-5 lg:block lg:border-l lg:border-t-0 lg:py-3 lg:pl-8 lg:text-right">
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground">{locale === "zh" ? "命盘总指数" : "CHART INDEX"}</p>
            <p className="mt-1 text-6xl font-semibold leading-none tabular-nums text-primary">{formatNumber(identity.main_score, locale)}</p>
          </div>
          <div className="min-w-24 flex-1 lg:mt-4">
            <div className="h-1.5 overflow-hidden rounded-full bg-primary/15" role="img" aria-label={`${locale === "zh" ? "命盘总指数" : "Chart index"} ${formatNumber(identity.main_score, locale)} / 100`}>
              <span className="block h-full rounded-full bg-primary" style={{ width: `${score}%` }} />
            </div>
            <p className="mt-2 text-xs font-medium text-muted-foreground">{locale === "zh" ? `超过 ${formatNumber(identity.global_percentile, locale)}% 的历法样本` : `Ahead of ${formatNumber(identity.global_percentile, locale)}% of calendar samples`}</p>
          </div>
        </div>
      </header>

      <div role="group" className="grid min-w-0 grid-cols-2 border-b border-border/60 lg:grid-cols-4" aria-label={locale === "zh" ? "四项主题分数" : "Four subject scores"}>
        {subjects.map((subject, index) => (
          <article key={subject.key} className={cn("min-w-0 px-4 py-5 sm:px-5", index % 2 === 1 && "border-l border-border/55", index >= 2 && "border-t border-border/55 lg:border-t-0", index > 0 && "lg:border-l lg:border-border/55")}>
            <div className="flex items-baseline justify-between gap-2">
              <h3 className="truncate text-sm font-semibold">{subject.label}</h3>
              <strong className="text-2xl font-semibold tabular-nums text-primary">{formatNumber(subject.score, locale)}</strong>
            </div>
            <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted" role="img" aria-label={`${subject.label} ${formatNumber(subject.score, locale)} / 100`}>
              <span className="block h-full rounded-full bg-primary/75" style={{ width: `${boundedPercentage(subject.score)}%` }} />
            </div>
            <p className="mt-3 text-sm font-medium leading-6">{subject.headline}</p>
            <p className="mt-2 text-xs font-medium leading-5 text-muted-foreground">{locale === "zh" ? `全部样本${topPercentageLabel(subject.global_top_percentage, locale)} · 同类${topPercentageLabel(subject.cohort_top_percentage, locale)}` : `${topPercentageLabel(subject.global_top_percentage, locale)} overall · ${topPercentageLabel(subject.cohort_top_percentage, locale)} among peers`}</p>
          </article>
        ))}
      </div>

      <div className={cn("grid min-w-0", twin && "lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.65fr)]")}>
        <section className="min-w-0 px-5 py-7 sm:px-7 lg:px-9" aria-labelledby={`${headingId}-fingerprints`}>
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="kicker">{locale === "zh" ? "我的亮点" : "MY SIGNATURE"}</p>
              <h3 id={`${headingId}-fingerprints`} className="mt-2 text-xl font-semibold">{locale === "zh" ? "最能代表你的五个特征" : "Five traits that stand out"}</h3>
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
                    <p className="text-xs font-semibold text-primary">{fingerprint.rarity_label} · {topPercentageLabel(fingerprint.top_percentage, locale)}</p>
                  </div>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{fingerprint.detail}</p>
                </div>
              </li>
            ))}
          </ol>
          {!twin && comparisonAction ? <div data-export-exclude className="mt-6"><ComparisonEntry action={comparisonAction} /></div> : null}
        </section>

        {twin ? <aside className="min-w-0 border-t border-border/60 bg-primary/[0.035] px-5 py-7 sm:px-7 lg:border-l lg:border-t-0 lg:px-8" aria-labelledby={`${headingId}-twin`}>
          <p className="kicker">{locale === "zh" ? "同类型命盘" : "YOUR CHART FAMILY"}</p>
          <h3 id={`${headingId}-twin`} className="mt-2 text-2xl font-semibold leading-tight">{twin.title}</h3>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">{twin.summary}</p>
          <p className="mt-5 border-y border-border/55 py-3 text-sm">
            <strong className="text-2xl tabular-nums text-primary">{formatNumber(twin.share_percentage, locale)}%</strong>
            <span className="ml-2 text-muted-foreground">{locale === "zh" ? "历法样本与你属于同一类型" : "of calendar samples share your chart family"}</span>
          </p>
          {twin.representatives.length ? (
            <div className="mt-5">
              <p className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "最接近你的结构样本" : "Closest chart patterns"}</p>
              <ul className="mt-2 space-y-2 text-sm leading-6">
                {twin.representatives.map((representative, index) => <li key={`${representative}-${index}`} className="flex gap-2"><span aria-hidden="true" className="text-primary">·</span><span>{representative}</span></li>)}
              </ul>
            </div>
          ) : null}
          {comparisonAction ? <div data-export-exclude className="mt-6"><ComparisonEntry action={comparisonAction} /></div> : null}
        </aside> : null}
      </div>
    </section>
  )
}
