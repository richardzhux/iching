"use client"

import { useId } from "react"
import { cn } from "@/lib/utils"
import { formatFrequency, frequencyBadge, frequencyLabel } from "@/lib/frequency-display"

export type AchievementLocale = "en" | "zh"
export type AchievementTier = "SSR" | "SR" | "R"
export type AchievementState = "条件齐备" | "命中" | "待核" | "受制"

export interface MetaphysicsAchievement {
  id: string
  title: string
  tier: AchievementTier | string
  state: AchievementState | string
  rarity_percentage: number | null
  position: string
  summary: string
  member_ids: string[]
  member_positions?: Record<string, string[]>
  universe_rule_ids?: string[]
  absent_rule_ids?: string[]
}

export interface MetaphysicsAchievementsProps {
  achievements: MetaphysicsAchievement[]
  locale?: AchievementLocale
  title?: string
  description?: string
  emptyMessage?: string
  className?: string
}

const markerNames: Record<string, string> = { wenchang: "文昌", xuetang: "学堂", ciguan: "词馆", huagai: "华盖", dexiu: "德秀", taohua: "桃花", hongyan: "红艳", hongluan: "红鸾", tianxi: "天喜", tianyi: "天乙", tiande: "天德", yuede: "月德", fuxing: "福星", guoyin: "国印", lushen: "禄神", yima: "驿马", jiangxing: "将星", yangren: "羊刃" }

function tierClass(tier: string) {
  if (tier === "SSR") return "border-[hsl(var(--imperial-metal)/0.55)] bg-[hsl(var(--imperial-metal)/0.12)] text-[hsl(var(--imperial-metal))]"
  if (tier === "SR") return "border-primary/45 bg-primary/10 text-primary"
  return "border-border bg-muted/[0.65] text-foreground"
}

function stateClass(state: string) {
  if (state === "条件齐备") return "bg-primary text-primary-foreground"
  if (state === "命中") return "bg-primary/[0.14] text-primary"
  if (state === "受制") return "bg-[hsl(var(--imperial-metal)/0.12)] text-[hsl(var(--imperial-metal))]"
  return "bg-muted text-foreground"
}

const englishState: Record<AchievementState, string> = {
  条件齐备: "Conditions met",
  命中: "Present",
  待核: "Unresolved",
  受制: "Constrained",
}

function stateLabel(state: string, locale: AchievementLocale) {
  if (locale === "zh") return state
  return englishState[state as AchievementState] ?? state
}

export function MetaphysicsAchievements({
  achievements,
  locale = "zh",
  title,
  description,
  emptyMessage,
  className,
}: MetaphysicsAchievementsProps) {
  const headingId = `${useId()}-metaphysics-achievements-title`
  const visibleAchievements = achievements
  const heading = title ?? (locale === "zh" ? "主题组合画像" : "Topic configurations")
  const supportingCopy = description ?? (locale === "zh" ? "按预先固定的主题指标共同统计，保留各项落位；出现率对应组内完全相同的有无配置，条件档次不表示吉凶。" : "These combinations group structures that occur together in the same chart. State describes their current operating conditions, while incidence is their same-value frequency in calendar samples.")

  return (
    <section className={cn("min-w-0", className)} aria-labelledby={headingId}>
      <header className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="kicker">{locale === "zh" ? "结构组合" : "STRUCTURE COMBINATIONS"}</p>
          <h2 id={headingId} className="mt-2 text-2xl font-semibold">{heading}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{supportingCopy}</p>
        </div>
        <p className="text-xs tabular-nums text-muted-foreground">{locale === "zh" ? `${visibleAchievements.length} 项` : `${visibleAchievements.length} found`}</p>
      </header>

      {visibleAchievements.length ? (
        <ul className="mt-5 grid min-w-0 gap-3 md:grid-cols-2">
          {visibleAchievements.map((achievement) => (
            <li key={achievement.id} className="min-w-0 overflow-hidden rounded-2xl border border-border/60 bg-surface px-4 py-5 shadow-[var(--surface-shadow-soft)] sm:px-5">
              <article className="min-w-0">
                <div className="flex items-center justify-between gap-3">
                  {frequencyBadge(achievement.rarity_percentage) ? <span
                    className={cn("inline-flex min-h-9 min-w-14 items-center justify-center rounded-xl border px-2.5 py-1.5 text-sm font-black tracking-[0.08em]", tierClass(frequencyBadge(achievement.rarity_percentage)!))}
                    aria-label={locale === "zh" ? `结构频率层级 ${frequencyBadge(achievement.rarity_percentage)}` : `Frequency tier ${frequencyBadge(achievement.rarity_percentage)}`}
                  >
                    {frequencyBadge(achievement.rarity_percentage)}
                  </span> : <span className="text-xs font-semibold text-muted-foreground">{frequencyLabel(achievement.rarity_percentage, locale)}</span>}
                  <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold", stateClass(achievement.state))}>{stateLabel(achievement.state, locale)}</span>
                </div>
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-5 gap-y-2">
                  <h3 className="mt-4 text-xl font-semibold leading-7">{achievement.title}</h3>
                  {achievement.rarity_percentage != null ? <p className="mt-4 shrink-0 rounded-full bg-primary/[0.08] px-2.5 py-1 text-xs font-semibold text-primary">{locale === "zh" ? `出现率 ${formatFrequency(achievement.rarity_percentage, locale)}%` : `${formatFrequency(achievement.rarity_percentage, locale)}% incidence`}</p> : null}
                </div>
                <p className="mt-3 text-sm leading-7 text-muted-foreground">{achievement.summary}</p>
                {achievement.universe_rule_ids?.length ? <details className="mt-3 text-xs leading-6 text-muted-foreground"><summary className="cursor-pointer font-semibold text-foreground">{locale === "zh" ? "组合范围与落位" : "Configuration and positions"}</summary><p className="mt-2">{locale === "zh" ? "固定指标：" : "Fixed indicators: "}{achievement.universe_rule_ids.map((id) => markerNames[id] ?? id).join("、")}</p><p>{locale === "zh" ? "未命中：" : "Absent: "}{achievement.absent_rule_ids?.length ? achievement.absent_rule_ids.map((id) => markerNames[id] ?? id).join("、") : "—"}</p>{Object.entries(achievement.member_positions ?? {}).map(([id, positions]) => <p key={id}>{markerNames[id] ?? id} · {positions.join("、")}</p>)}<p>{locale === "zh" ? "百分比只匹配组内有无配置，落位与条件档次另外展示，不计入这个联合事件。" : "Incidence matches presence and absence only; positions and condition states are shown separately."}</p></details> : null}
                <dl className="mt-4 flex min-w-0 flex-wrap items-center gap-x-5 gap-y-2 border-t border-border/55 pt-3 text-xs">
                  <div className="min-w-0">
                    <dt className="inline font-semibold text-foreground">{locale === "zh" ? "落位：" : "Position: "}</dt>
                    <dd className="inline break-words text-muted-foreground">{achievement.position}</dd>
                  </div>
                  {achievement.member_ids.length > 1 ? <div className="ml-auto"><dt className="sr-only">{locale === "zh" ? "组合数量" : "Combination size"}</dt><dd className="font-semibold text-primary">{locale === "zh" ? `${achievement.member_ids.length} 项结构共同出现` : `${achievement.member_ids.length} structures occur together`}</dd></div> : null}
                </dl>
              </article>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-5 rounded-2xl border border-border/60 bg-muted/30 px-5 py-6 text-sm leading-6 text-muted-foreground">{emptyMessage ?? (locale === "zh" ? "当前没有固定主题中两项以上共同命中的配置；单项结构仍保留在完整命盘中。" : "No rare multi-structure combination is present in this chart; individual structures remain available in the full chart.")}</p>
      )}
    </section>
  )
}
