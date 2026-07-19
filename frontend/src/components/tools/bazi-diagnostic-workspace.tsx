"use client"

import { useEffect, useMemo, useState } from "react"
import { BookOpen, Check, ChevronRight, CircleDot, Sparkles } from "lucide-react"

import { fetchPatternLibrary, fetchPatternRuleSummary } from "@/lib/api"
import { cn } from "@/lib/utils"
import type {
  ConsumerClaim,
  MetaphysicsChart,
  PatternCandidate,
  PatternLibrary,
  PatternRuleSummary,
  ThemeComparison,
  ThemeProfile,
} from "@/types/api"

type Locale = "en" | "zh"

const THEME_KEYS = [
  ["事业", "career"],
  ["财富", "wealth"],
  ["感情", "relationship"],
  ["五行与承压结构", "rhythm"],
] as const

const THEME_COPY = {
  career: { zh: "事业主场", en: "Career lane" },
  wealth: { zh: "财富路径", en: "Wealth path" },
  relationship: { zh: "关系磁场", en: "Relationship style" },
  rhythm: { zh: "身心节奏", en: "Mind-body rhythm" },
} as const

const THEME_ACCENTS = {
  career: "text-violet-700 bg-violet-500",
  wealth: "text-amber-700 bg-amber-500",
  relationship: "text-rose-700 bg-rose-500",
  rhythm: "text-cyan-700 bg-cyan-600",
} as const

function statusText(value: string | undefined, locale: Locale) {
  const map: Record<string, { zh: string; en: string }> = {
    formed: { zh: "成格", en: "Formed" },
    effective: { zh: "得用", en: "Effective" },
    constrained: { zh: "受制", en: "Constrained" },
    rescued: { zh: "救成", en: "Rescued" },
    mixed: { zh: "混杂", en: "Mixed" },
    transformed: { zh: "转化", en: "Transformed" },
    none: { zh: "未见明确救应", en: "No explicit rescue" },
  }
  return map[value ?? ""]?.[locale] ?? value ?? (locale === "zh" ? "待判断" : "Pending")
}

function compactMetricLabel(item: ThemeComparison, locale: Locale) {
  if (locale === "zh") return item.display_label ?? item.semantic_pole ?? item.display_percentage
  if (item.status === "unsupported") return "No reference"
  if (item.comparison_mode === "incidence") return `${(item.hit_percentage ?? 0).toFixed(1)}% incidence`
  if (item.display_direction === "high") return "More pronounced"
  if (item.display_direction === "low") return "More restrained"
  return "Common range"
}

function metricPosition(item: ThemeComparison) {
  if (item.status === "unsupported") return 10
  if (item.comparison_mode === "incidence") return Math.max(5, Math.min(100, item.hit_percentage ?? 0))
  const lower = item.lower_percentage ?? 0
  const same = item.same_percentage ?? 0
  return Math.max(4, Math.min(100, lower + same / 2))
}

function matchingThemeClaim(claims: ConsumerClaim[], key: string) {
  return claims.find((claim) => claim.slot === "theme" && claim.theme === key)
}

function lifecycleClaims(claims: ConsumerClaim[]) {
  return {
    formation: claims.find((claim) => claim.classicalRole === "formation_path"),
    damage: claims.find((claim) => claim.classicalRole === "damage"),
    rescue: claims.find((claim) => claim.classicalRole === "rescue"),
    verdict: claims.find((claim) => claim.slot === "hero"),
  }
}

function buildLifecycle(primary: PatternCandidate | null, claims: ConsumerClaim[], locale: Locale) {
  const bound = lifecycleClaims(claims)
  return [
    {
      id: "candidate",
      label: locale === "zh" ? "月令候选" : "Month-command candidate",
      title: primary?.name ?? (locale === "zh" ? "主导结构" : "Dominant structure"),
      detail: primary?.selection === "month_main_qi"
        ? (locale === "zh" ? "月令本气取格" : "Selected from the month-command main qi")
        : (primary?.summary ?? (locale === "zh" ? "由月令与透干确定候选" : "Candidate derived from month command and exposed stems")),
      state: "active",
      claim: bound.verdict,
    },
    {
      id: "formation",
      label: locale === "zh" ? "成格路径" : "Formation",
      title: bound.formation?.title ?? primary?.formation_path?.title ?? statusText(primary?.formation, locale),
      detail: bound.formation?.summary
        ?? primary?.formation_path?.details?.join("；")
        ?? (locale === "zh" ? "当前命盘中形成主结构的关键连接" : "The key connection forming the primary structure"),
      state: primary?.formation === "formed" || bound.formation ? "active" : "quiet",
      claim: bound.formation ?? bound.verdict,
    },
    {
      id: "damage",
      label: locale === "zh" ? "破格与牵制" : "Damage and constraints",
      title: bound.damage?.title
        ?? (primary?.integrity === "minor_damage" ? (locale === "zh" ? "存在局部牵制" : "Local constraint present") : statusText(primary?.integrity, locale)),
      detail: bound.damage?.summary
        ?? primary?.tensions?.join("；")
        ?? (locale === "zh" ? "未见改变主路径的明显破坏" : "No clear damage overturns the main path"),
      state: bound.damage || primary?.integrity === "minor_damage" ? "warning" : "quiet",
      claim: bound.damage ?? bound.verdict,
    },
    {
      id: "rescue",
      label: locale === "zh" ? "救应与转化" : "Rescue and transformation",
      title: bound.rescue?.title ?? statusText(primary?.rescue, locale),
      detail: bound.rescue?.summary
        ?? primary?.rescues?.join("；")
        ?? (locale === "zh" ? "当前裁决不依赖额外救应" : "The verdict does not rely on an additional rescue"),
      state: bound.rescue ? "active" : "quiet",
      claim: bound.rescue ?? bound.verdict,
    },
    {
      id: "verdict",
      label: locale === "zh" ? "最终裁决" : "Verdict",
      title: bound.verdict?.title ?? primary?.title ?? (locale === "zh" ? "主导结构" : "Dominant structure"),
      detail: bound.verdict?.summary ?? primary?.summary ?? "",
      state: "verdict",
      claim: bound.verdict,
    },
  ]
}

function EvidenceSourcePanel({
  claim,
  bundleId,
  patternId,
  locale,
}: {
  claim: ConsumerClaim | undefined
  bundleId: string
  patternId: string
  locale: Locale
}) {
  const [sources, setSources] = useState<PatternRuleSummary[]>([])
  const [library, setLibrary] = useState<PatternLibrary | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let active = true
    const ids = claim?.ruleIds ?? []
    if (!ids.length) {
      setSources([])
      return () => { active = false }
    }
    setLoading(true)
    void Promise.allSettled(ids.map((ruleId) => fetchPatternRuleSummary(bundleId, ruleId)))
      .then((results) => {
        if (!active) return
        setSources(results.flatMap((result) => result.status === "fulfilled" ? [result.value] : []))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [bundleId, claim?.id, claim?.ruleIds])

  useEffect(() => {
    let active = true
    if (!patternId) {
      setLibrary(null)
      return () => { active = false }
    }
    void fetchPatternLibrary(patternId)
      .then((result) => {
        if (active) setLibrary(result)
      })
      .catch(() => {
        if (active) setLibrary(null)
      })
    return () => { active = false }
  }, [patternId])

  if (!claim) return null
  return (
    <aside className="min-w-0 border-l border-border/55 pl-5 lg:pl-7">
      <div className="flex items-center gap-2 text-primary">
        <BookOpen aria-hidden="true" className="size-4" />
        <h3 className="text-sm font-semibold">{locale === "zh" ? "为什么这样判断" : "Why this conclusion"}</h3>
      </div>
      <h4 className="mt-4 text-xl font-semibold leading-8">{claim.title}</h4>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{claim.summary}</p>

      {claim.evidenceHighlights?.length ? (
        <div className="mt-5 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{locale === "zh" ? "命盘事实" : "Chart facts"}</p>
          {claim.evidenceHighlights.map((item) => (
            <p key={item} className="flex gap-2 text-sm leading-6">
              <Check aria-hidden="true" className="mt-1 size-4 shrink-0 text-primary" />
              <span>{item}</span>
            </p>
          ))}
        </div>
      ) : null}

      {loading ? <p className="mt-5 text-sm text-muted-foreground">{locale === "zh" ? "正在读取古籍依据…" : "Loading classical evidence…"}</p> : null}
      {sources.length ? (
        <div className="mt-6 space-y-5">
          {sources.map((source) => {
            const locators = source.sources.flatMap((item) => item.locators).filter((item) => item.quote)
            return (
              <section key={source.rule_id} className="border-t border-border/50 pt-4">
                <p className="text-sm font-semibold text-primary">{source.title}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{source.summary}</p>
                {locators.slice(0, 2).map((locator) => (
                  <blockquote key={locator.id} className="mt-3 border-l-2 border-amber-400/70 pl-3 text-sm leading-6 text-foreground/85">
                    {locator.quote}
                    <footer className="mt-1 text-xs text-muted-foreground">
                      {locator.printed_page ? `${locale === "zh" ? "页" : "p."}${locator.printed_page}` : ""}
                    </footer>
                  </blockquote>
                ))}
              </section>
            )
          })}
        </div>
      ) : (
        <p className="mt-5 text-xs leading-5 text-muted-foreground">
          {claim.sourceIds.length
            ? (locale === "zh" ? "当前依据已绑定到研究资料，影印引文将在可用时显示。" : "This claim is linked to research evidence; scan quotations appear when available.")
            : (locale === "zh" ? "这一判断来自命盘结构事实，不依赖单项古籍格名。" : "This conclusion comes from chart structure rather than a single named classical rule.")}
        </p>
      )}
      {library?.examples.length ? (
        <section className="mt-7 border-t border-border/50 pt-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{locale === "zh" ? "相近古籍例命" : "Related classical examples"}</p>
          <div className="mt-3 divide-y divide-border/45">
            {library.examples.slice(0, 3).map((example) => (
              <article key={example.id} className="py-3 first:pt-0">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h5 className="text-sm font-semibold">{example.name}</h5>
                  <span className="text-xs tracking-wide text-primary">{example.pillars.join("　")}</span>
                </div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{example.author_claim}</p>
              </article>
            ))}
          </div>
          {library.examples.length > 3 ? <p className="mt-2 text-xs font-semibold text-primary">{locale === "zh" ? `本格局共收录 ${library.examples.length} 个例命` : `${library.examples.length} examples indexed`}</p> : null}
        </section>
      ) : null}
    </aside>
  )
}

function ThemeMap({
  profile,
  claim,
  locale,
}: {
  profile: ThemeProfile | undefined
  claim: ConsumerClaim | undefined
  locale: Locale
}) {
  const key = THEME_KEYS.find(([label]) => label === profile?.theme)?.[1] ?? "career"
  const accent = THEME_ACCENTS[key]
  const [textClass, barClass] = accent.split(" ")
  const comparisons = profile?.comparisons ?? []
  return (
    <section className="min-w-0 border-t border-border/55 pt-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className={cn("text-sm font-semibold", textClass)}>{THEME_COPY[key][locale]}</p>
          <h3 className="mt-1 text-lg font-semibold">{claim?.title ?? profile?.theme ?? "—"}</h3>
          <p className="mt-1 max-w-[34rem] text-sm leading-6 text-muted-foreground">{claim?.summary}</p>
        </div>
        <span className="shrink-0 text-xs font-semibold text-muted-foreground">
          {locale === "zh" ? `${comparisons.length} 项结构对照` : `${comparisons.length} comparisons`}
        </span>
      </div>
      <div className="mt-5 grid gap-x-5 gap-y-4 sm:grid-cols-2">
        {comparisons.map((item) => {
          const position = metricPosition(item)
          return (
            <div key={item.metric_id} className="min-w-0">
              <div className="flex items-end justify-between gap-3">
                <span className="truncate text-xs font-medium">{item.label}</span>
                <span className="shrink-0 text-[0.68rem] text-muted-foreground">{compactMetricLabel(item, locale)}</span>
              </div>
              <div className="relative mt-2 h-1.5 rounded-full bg-muted">
                <span className={cn("absolute inset-y-0 left-0 rounded-full opacity-70", barClass)} style={{ width: `${position}%` }} />
                <span className={cn("absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-background", barClass)} style={{ left: `${position}%` }} />
              </div>
              <div className="mt-1 flex justify-between text-[0.62rem] text-muted-foreground">
                <span>{locale === "zh" ? "较少" : "Less"}</span>
                <strong className="text-foreground">{item.value}{item.unit && item.unit !== "count" ? ` ${item.unit}` : ""}</strong>
                <span>{locale === "zh" ? "较多" : "More"}</span>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export function BaziDiagnosticWorkspace({ chart, locale }: { chart: MetaphysicsChart; locale: Locale }) {
  const claims = chart.consumer?.claims ?? []
  const hero = claims.find((claim) => claim.slot === "hero")
  const primary = chart.structure?.patterns?.primary ?? null
  const lifecycle = useMemo(() => buildLifecycle(primary, claims, locale), [claims, locale, primary])
  const initialClaim = lifecycle.find((item) => item.claim)?.claim
  const [selectedClaimId, setSelectedClaimId] = useState(initialClaim?.id ?? "")
  const selectedClaim = claims.find((claim) => claim.id === selectedClaimId) ?? initialClaim
  const bundleId = chart.rule_versions?.pattern_bundle ?? ""

  useEffect(() => {
    setSelectedClaimId(initialClaim?.id ?? "")
  }, [chart.input_timestamp, initialClaim?.id])

  return (
    <div className="overflow-hidden border-y border-border/60 bg-surface">
      <section className="grid min-w-0 gap-8 px-5 py-8 sm:px-7 lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.42fr)] lg:px-9 lg:py-10">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles aria-hidden="true" className="size-4" />
            <p className="text-sm font-semibold">{locale === "zh" ? "命格诊断" : "Pattern diagnosis"}</p>
          </div>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">{hero?.title ?? primary?.title ?? "—"}</h2>
          <p className="mt-3 max-w-3xl text-base leading-7 text-muted-foreground">{hero?.summary ?? primary?.summary}</p>

          <ol className="mt-8 grid gap-0 border-y border-border/55 md:grid-cols-5">
            {lifecycle.map((step, index) => (
              <li key={step.id} className="relative min-w-0 border-b border-border/45 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
                <button
                  type="button"
                  onClick={() => step.claim && setSelectedClaimId(step.claim.id)}
                  aria-pressed={selectedClaim?.id === step.claim?.id}
                  className={cn(
                    "group flex h-full w-full min-w-0 items-start gap-3 px-3 py-4 text-left transition sm:px-4",
                    selectedClaim?.id === step.claim?.id ? "bg-primary/[0.06]" : "hover:bg-muted/35",
                  )}
                >
                  <span className={cn(
                    "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                    step.state === "verdict" || step.state === "active"
                      ? "border-primary bg-primary text-primary-foreground"
                      : step.state === "warning"
                        ? "border-amber-400 bg-amber-50 text-amber-800"
                        : "border-border bg-background text-muted-foreground",
                  )}>
                    {step.state === "verdict" ? <Check aria-hidden="true" className="size-4" /> : index + 1}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-muted-foreground">{step.label}</span>
                    <strong className="mt-1 block text-sm leading-5">{step.title}</strong>
                    <span className="mt-1.5 line-clamp-3 block text-xs leading-5 text-muted-foreground">{step.detail}</span>
                  </span>
                </button>
                {index < lifecycle.length - 1 ? <ChevronRight aria-hidden="true" className="absolute -right-2 top-1/2 z-10 hidden size-4 -translate-y-1/2 rounded-full bg-surface text-muted-foreground md:block" /> : null}
              </li>
            ))}
          </ol>

          <div className="mt-8 grid gap-x-8 lg:grid-cols-2">
            {THEME_KEYS.map(([label, key]) => (
              <ThemeMap
                key={label}
                profile={chart.theme_profiles.find((profile) => profile.theme === label)}
                claim={matchingThemeClaim(claims, key === "rhythm" ? "rhythm" : key)}
                locale={locale}
              />
            ))}
          </div>
        </div>

        <EvidenceSourcePanel claim={selectedClaim} bundleId={bundleId} patternId={String(primary?.id ?? "").replace("bazi.pattern.ordinary.", "").replace("bazi.pattern.special.", "")} locale={locale} />
      </section>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-border/55 bg-muted/20 px-5 py-3 text-xs text-muted-foreground sm:px-7 lg:px-9">
        <span className="inline-flex items-center gap-2">
          <CircleDot aria-hidden="true" className="size-3.5 text-primary" />
          {locale === "zh" ? "点击诊断轨道可切换对应命盘事实与古籍依据" : "Select a lifecycle step to inspect facts and classical evidence"}
        </span>
        <span>{locale === "zh" ? `已展开 ${chart.theme_profiles.reduce((sum, profile) => sum + (profile.comparisons?.length ?? 0), 0)} 项结构分布` : `${chart.theme_profiles.reduce((sum, profile) => sum + (profile.comparisons?.length ?? 0), 0)} distributions surfaced`}</span>
      </footer>
    </div>
  )
}
