"use client"

import { motion, useReducedMotion } from "framer-motion"
import { useState } from "react"

import type { Locale } from "@/i18n/config"
import type { ZiHourNotice } from "@/types/api"

/**
 * 晚子时: show both schools and let the reader decide.
 *
 * 子时 runs 23:00-01:00 and straddles midnight. Both schools place 00:00-01:00
 * on the new day; they disagree only about whether 23:00-24:00 does too. That
 * disagreement is live and unresolved, so a birth landing there gets both
 * charts rather than whichever one the code happened to compute first.
 *
 * The test is run against the calculation clock, so a civil 23:50 that
 * true-solar correction carries back to 22:59 never raises the question.
 */
export function ZiHourChoice({
  notice,
  locale,
  selected,
  onSelect,
}: {
  notice: ZiHourNotice
  locale: Locale
  selected?: string
  onSelect?: (boundary: "current" | "forward") => void
}) {
  const reduceMotion = useReducedMotion()
  const [localChoice, setLocalChoice] = useState<string | undefined>(selected)
  const active = selected ?? localChoice

  // 00:00-01:00: both schools agree, so say so instead of asking.
  if (!notice.schools_disagree) {
    return (
      <aside className="rounded-2xl border border-border/55 bg-surface px-5 py-4">
        <p className="text-xs font-semibold text-primary">
          {locale === "zh" ? "子时说明" : "Zi hour"}
        </p>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">
          {locale === "zh"
            ? notice.note
            : "This birth falls in the early half of the Zi hour (00:00-01:00). Both schools agree here, so the day-boundary dispute does not affect this chart."}
        </p>
      </aside>
    )
  }

  return (
    <aside className="rounded-2xl border border-primary/35 bg-primary/[0.045] px-5 py-5">
      <p className="text-xs font-semibold text-primary">
        {locale === "zh" ? "晚子时 · 两派分歧" : "Late Zi hour · the schools differ"}
      </p>
      <h3 className="mt-2 text-lg font-semibold leading-7">
        {locale === "zh" ? "这张盘有两种排法" : "This chart has two valid readings"}
      </h3>
      <p className="mt-2 text-sm leading-7 text-muted-foreground">
        {locale === "zh"
          ? notice.note
          : "This birth falls between 23:00 and 24:00. The two schools disagree on whether the day pillar advances. Both are shown; the choice is yours."}
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2" role="group"
        aria-label={locale === "zh" ? "选择换日流派" : "Choose a day-boundary school"}>
        {notice.options.map((option, index) => {
          const isActive = active === option.day_boundary
          return (
            <motion.button
              type="button"
              key={option.day_boundary}
              aria-pressed={isActive}
              onClick={() => {
                setLocalChoice(option.day_boundary)
                onSelect?.(option.day_boundary)
              }}
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reduceMotion ? { duration: 0 } : { delay: 0.06 * index, duration: 0.28 }}
              className={`rounded-xl border px-4 py-3 text-left transition-colors ${
                isActive
                  ? "border-primary bg-primary/10"
                  : "border-border/55 bg-surface hover:border-primary/45"
              }`}
            >
              <span className="block text-xs font-semibold text-primary">
                {locale === "zh"
                  ? option.label
                  : option.day_boundary === "forward"
                    ? "Day advances (school 1)"
                    : "Day does not advance (school 2)"}
              </span>
              <span className="mt-2 block font-mono text-base tracking-wide">{option.bazi}</span>
              <span className="mt-1 block text-xs text-muted-foreground">
                {locale === "zh"
                  ? `日柱 ${option.day_pillar} · 日主 ${option.day_stem}`
                  : `Day pillar ${option.day_pillar} · day master ${option.day_stem}`}
              </span>
            </motion.button>
          )
        })}
      </div>

      <p className="mt-3 text-xs leading-5 text-muted-foreground">
        {locale === "zh"
          ? "两派都有传承依据，本产品不代为判定。改用另一排法请在专业设置中切换「晚子时换日」后重新排盘。"
          : "Both schools have standing. This product does not decide for you; switch “Advance day at late Zi hour” in the professional settings and recalculate to use the other."}
      </p>
    </aside>
  )
}
