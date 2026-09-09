"use client"

import dynamic from "next/dynamic"
import Image from "next/image"
import type { CSSProperties, ReactNode } from "react"
import { useI18n } from "@/components/providers/i18n-provider"
import { MotionToggle, useAutumnMotion } from "./autumn-motion"
import type { AutumnStageProps } from "./autumn-stage"

const AutumnStage = dynamic(() => import("./autumn-stage"), { ssr: false })

type Props = AutumnStageProps & {
  children: ReactNode
  className?: string
  caption?: ReactNode
  sceneOverlay?: ReactNode
}

export function AutumnFrame({ children, className = "", caption, sceneOverlay, ...stage }: Props) {
  const { locale } = useI18n()
  const { paused } = useAutumnMotion()
  return (
    <section className={`autumn-frame ${className}`} data-motion={paused ? "paused" : "playing"}>
      <div className="autumn-scene-panel" id={className === "autumn-casting" ? "casting-scene" : undefined}>
        <Image className="autumn-courtyard" src="/autumn/courtyard.webp" alt="" fill priority sizes="100vw" />
        <AutumnStage {...stage} />
        {sceneOverlay}
        <div className="autumn-leaves" aria-hidden="true">
          {Array.from({ length: 12 }, (_, index) => (
            <span key={index} className="autumn-leaf-path" style={{
              "--leaf-x": `${34 + (index * 17) % 66}%`,
              "--leaf-delay": `${-index * 2.31}s`,
              "--leaf-duration": `${13 + index % 5 * 2.3}s`,
              "--leaf-drift": `${(index % 2 ? -1 : 1) * (50 + index * 13)}px`,
              "--leaf-size": `${index > 9 ? 104 + (index - 10) * 34 : 22 + index % 4 * 12}px`,
              "--leaf-turn": `${index * 31}deg`,
            } as CSSProperties}>
              <Image src="/autumn/ginkgo-leaf.webp" alt="" width={70} height={70} className="autumn-leaf" />
            </span>
          ))}
        </div>
        {caption ? <div className="autumn-scene-caption">{caption}</div> : null}
        <div className="autumn-season-note" aria-hidden="true">{locale === "zh" ? "朱墙 · 银杏 · 秋日" : "VERMILION · GINKGO · AUTUMN"}</div>
        <MotionToggle />
      </div>
      <div className="autumn-question-panel">{children}</div>
    </section>
  )
}
