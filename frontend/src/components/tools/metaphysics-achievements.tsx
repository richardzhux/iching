"use client"

import { useId } from "react"
import { cn } from "@/lib/utils"

export type AchievementLocale = "en" | "zh"
export type AchievementTier = "SSR" | "SR" | "R"
export type AchievementState = "发力" | "有力" | "可见" | "受制"

export interface MetaphysicsAchievement {
  id: string
  title: string
  tier: AchievementTier | string
  state: AchievementState | string
  rarity_percentage: number
  position: string
  summary: string
  member_ids: string[]
}

export interface MetaphysicsAchievementsProps {
  achievements: MetaphysicsAchievement[]
  locale?: AchievementLocale
  title?: string
  description?: string
  emptyMessage?: string
  className?: string
}

function tierClass(tier: string) {
  if (tier === "SSR") return "border-[hsl(var(--imperial-metal)/0.55)] bg-[hsl(var(--imperial-metal)/0.12)] text-[hsl(var(--imperial-metal))]"
  if (tier === "SR") return "border-primary/45 bg-primary/10 text-primary"
  return "border-border bg-muted/[0.65] text-foreground"
}

function stateClass(state: string) {
  if (state === "发力") return "bg-primary text-primary-foreground"
  if (state === "有力") return "bg-primary/[0.14] text-primary"
  if (state === "受制") return "bg-destructive/10 text-destructive"
  return "bg-muted text-foreground"
}

const englishState: Record<AchievementState, string> = {
  发力: "Activated",
  有力: "Effective",
  可见: "Visible",
  受制: "Constrained",
}

function stateLabel(state: string, locale: AchievementLocale) {
  if (locale === "zh") return state
  return englishState[state as AchievementState] ?? state
}

function formatPercentage(value: number, locale: AchievementLocale) {
  return new Intl.NumberFormat(locale === "zh" ? "zh-CN" : "en-US", { maximumFractionDigits: 2 }).format(value)
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
  const heading = title ?? (locale === "zh" ? "已解锁的命盘成就" : "Unlocked chart achievements")
  const supportingCopy = description ?? (locale === "zh" ? "越稀有，越难在普通命盘里遇见；发力状态代表这项特征正得到原局呼应。" : "The rarer the achievement, the less often it appears; an activated state means the chart strongly reinforces it.")

  return (
    <section className={cn("min-w-0", className)} aria-labelledby={headingId}>
      <header className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="kicker">{locale === "zh" ? "稀有成就" : "RARE ACHIEVEMENTS"}</p>
          <h2 id={headingId} className="mt-2 text-2xl font-semibold">{heading}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{supportingCopy}</p>
        </div>
        <p className="text-xs tabular-nums text-muted-foreground">{locale === "zh" ? `${achievements.length} 项` : `${achievements.length} found`}</p>
      </header>

      {achievements.length ? (
        <ul className="mt-5 grid min-w-0 gap-3 md:grid-cols-2">
          {achievements.map((achievement) => (
            <li key={achievement.id} className="min-w-0 overflow-hidden rounded-2xl border border-border/60 bg-surface px-4 py-5 shadow-[var(--surface-shadow-soft)] sm:px-5">
              <article className="min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <span className={cn("inline-flex min-h-9 min-w-14 items-center justify-center rounded-xl border px-2.5 py-1.5 text-sm font-black tracking-[0.08em]", tierClass(achievement.tier))}>{achievement.tier}</span>
                  <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold", stateClass(achievement.state))}>{stateLabel(achievement.state, locale)}</span>
                </div>
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-5 gap-y-2">
                  <h3 className="mt-4 text-xl font-semibold leading-7">{achievement.title}</h3>
                  <p className="mt-4 shrink-0 rounded-full bg-primary/[0.08] px-2.5 py-1 text-xs font-semibold text-primary">{locale === "zh" ? `出现率 ${formatPercentage(achievement.rarity_percentage, locale)}%` : `${formatPercentage(achievement.rarity_percentage, locale)}% incidence`}</p>
                </div>
                <p className="mt-3 text-sm leading-7 text-muted-foreground">{achievement.summary}</p>
                <dl className="mt-4 flex min-w-0 flex-wrap items-center gap-x-5 gap-y-2 border-t border-border/55 pt-3 text-xs">
                  <div className="min-w-0">
                    <dt className="inline font-semibold text-foreground">{locale === "zh" ? "落位：" : "Position: "}</dt>
                    <dd className="inline break-words text-muted-foreground">{achievement.position}</dd>
                  </div>
                  {achievement.member_ids.length > 1 ? <div className="ml-auto"><dt className="sr-only">{locale === "zh" ? "组合数量" : "Combination size"}</dt><dd className="font-semibold text-primary">{locale === "zh" ? `${achievement.member_ids.length} 项结构共振` : `${achievement.member_ids.length}-part resonance`}</dd></div> : null}
                </dl>
              </article>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-5 rounded-2xl border border-border/60 bg-muted/30 px-5 py-6 text-sm leading-6 text-muted-foreground">{emptyMessage ?? (locale === "zh" ? "暂未解锁稀有成就；你的主导格局与主题亮点仍可在完整命盘中查看。" : "No rare achievement is unlocked yet; your main chart pattern and standout themes remain available in the full chart.")}</p>
      )}
    </section>
  )
}
