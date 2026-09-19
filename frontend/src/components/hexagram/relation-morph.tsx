"use client"

import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { useId, useState } from "react"

import type { Locale } from "@/i18n/config"
import { hexagramLines } from "@/lib/hexagram-library"
import type { RelationKind } from "@/lib/hexagram-relations"

/**
 * Show a related hexagram by performing the operation that produces it.
 *
 * 综卦 is the primary turned upside down, so the figure rotates 180°. 错卦
 * inverts every line's polarity, so each line morphs in place. 互卦 is built
 * from lines 2-3-4 and 3-4-5, so those lines light up and slide together. The
 * motion is the explanation — a reader who watches it once knows the rule,
 * which a paragraph of prose does not achieve as quickly.
 *
 * Every animation is skipped under `prefers-reduced-motion`, and the figure is
 * decorative: the accessible description lives in the caller's text.
 */

const LINE_POSITION_LABELS_ZH = ["初", "二", "三", "四", "五", "上"]

type Props = {
  /** Primary hexagram lines, bottom to top, as "0" | "1". */
  primary: readonly string[]
  /** Target hexagram lines, bottom to top. */
  target: readonly string[]
  kind: RelationKind
  locale: Locale
  /** Line positions (1-based, bottom up) that moved in the cast. */
  movingPositions?: readonly number[]
}

function describeKind(kind: RelationKind, locale: Locale) {
  const zh: Partial<Record<RelationKind, string>> = {
    reverse: "整卦上下颠倒",
    inverse: "六爻阴阳互换",
    mutual: "取二三四、三四五爻重组",
    changed: "动爻变其阴阳",
    main: "本卦六爻",
  }
  const en: Partial<Record<RelationKind, string>> = {
    reverse: "the whole figure turns over",
    inverse: "every line flips polarity",
    mutual: "lines 2-3-4 and 3-4-5 recombine",
    changed: "the moving lines change",
    main: "the six cast lines",
  }
  return (locale === "zh" ? zh : en)[kind] ?? ""
}

export function RelationMorph({ primary, target, kind, locale, movingPositions = [] }: Props) {
  const reduceMotion = useReducedMotion()
  const titleId = useId()
  const [replayCount, setReplayCount] = useState(0)
  const [hovered, setHovered] = useState<number | null>(null)
  // Remounting on the kind replays the animation without an effect, so the
  // motion always matches the relation currently selected.
  const replayKey = `${kind}-${replayCount}`

  const lines = (target.length ? target : primary).map((value) => value === "1" || value === "yang")
  // 互卦 draws lines 2-5 of the primary; highlight where they came from.
  const sourceHighlight = kind === "mutual" ? [2, 3, 4, 5] : []
  const rotation = kind === "reverse" ? 180 : 0

  return (
    <figure className="relation-morph" aria-labelledby={titleId}>
      <motion.div
        key={replayKey}
        className="relation-morph-stack"
        initial={reduceMotion ? false : { rotate: 0 }}
        animate={{ rotate: rotation }}
        transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 55, damping: 13 }}
        aria-hidden="true"
      >
        {/* Rendered top line first so index 5 is the top of the figure. */}
        {[...lines].reverse().map((isYang, renderIndex) => {
          const position = 6 - renderIndex
          const moved = movingPositions.includes(position)
          const fromMutual = sourceHighlight.includes(position)
          const isHovered = hovered === position
          return (
            <motion.button
              type="button"
              key={position}
              className="relation-morph-line"
              data-moving={moved || undefined}
              data-source={fromMutual || undefined}
              data-active={isHovered || undefined}
              onMouseEnter={() => setHovered(position)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(position)}
              onBlur={() => setHovered(null)}
              // Counter-rotate so labels stay upright while the figure turns.
              style={{ rotate: -rotation }}
              initial={reduceMotion ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reduceMotion ? { duration: 0 } : { delay: 0.05 * renderIndex, duration: 0.3 }}
              aria-label={`${locale === "zh" ? "第" : "Line "}${position}${locale === "zh" ? "爻" : ""}: ${isYang ? (locale === "zh" ? "阳" : "yang") : (locale === "zh" ? "阴" : "yin")}`}
            >
              <span className="relation-morph-index">
                {locale === "zh" ? LINE_POSITION_LABELS_ZH[position - 1] : position}
              </span>
              <span className="relation-morph-bars">
                <AnimatePresence initial={false} mode="wait">
                  {isYang ? (
                    <motion.span
                      key="yang"
                      className="relation-morph-bar"
                      initial={reduceMotion ? false : { scaleX: 0.2, opacity: 0 }}
                      animate={{ scaleX: 1, opacity: 1 }}
                      exit={reduceMotion ? undefined : { scaleX: 0.2, opacity: 0 }}
                      transition={reduceMotion ? { duration: 0 } : { duration: 0.28 }}
                    />
                  ) : (
                    <motion.span
                      key="yin"
                      className="relation-morph-split"
                      initial={reduceMotion ? false : { opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={reduceMotion ? undefined : { opacity: 0 }}
                      transition={reduceMotion ? { duration: 0 } : { duration: 0.28 }}
                    >
                      <span className="relation-morph-bar" />
                      <span className="relation-morph-bar" />
                    </motion.span>
                  )}
                </AnimatePresence>
              </span>
            </motion.button>
          )
        })}
      </motion.div>
      <figcaption id={titleId} className="relation-morph-caption">
        {describeKind(kind, locale)}
        {hovered ? (
          <span className="relation-morph-annotation">
            {locale === "zh"
              ? `　第${hovered}爻${lines[hovered - 1] ? "阳" : "阴"}${movingPositions.includes(hovered) ? " · 动爻" : ""}`
              : `　line ${hovered} ${lines[hovered - 1] ? "yang" : "yin"}${movingPositions.includes(hovered) ? " · moving" : ""}`}
          </span>
        ) : null}
      </figcaption>
      {!reduceMotion ? (
        <button type="button" className="relation-morph-replay" onClick={() => setReplayCount((value) => value + 1)}>
          {locale === "zh" ? "再看一次变化" : "Replay the change"}
        </button>
      ) : null}
    </figure>
  )
}

export function relationLines(binary: string | null | undefined) {
  return binary ? (hexagramLines(binary) as readonly string[]) : []
}
