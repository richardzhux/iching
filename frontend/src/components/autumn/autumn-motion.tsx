"use client"

import { createContext, useContext, useState, type ReactNode } from "react"
import { useReducedMotion } from "framer-motion"
import { Pause, Play } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"

const MotionContext = createContext({ paused: false, reduced: false, toggle: () => {} })

export function AutumnMotionProvider({ children }: { children: ReactNode }) {
  const reduced = Boolean(useReducedMotion())
  const [paused, setPaused] = useState(false)
  return (
    <MotionContext.Provider value={{ paused: paused || reduced, reduced, toggle: () => setPaused((value) => !value) }}>
      {children}
    </MotionContext.Provider>
  )
}

export const useAutumnMotion = () => useContext(MotionContext)

export function MotionToggle() {
  const { locale } = useI18n()
  const { paused, reduced, toggle } = useAutumnMotion()
  return (
    <button type="button" className="autumn-motion-toggle" onClick={toggle} disabled={reduced} aria-pressed={paused}>
      {paused ? <Play size={13} aria-hidden="true" /> : <Pause size={13} aria-hidden="true" />}
      {reduced ? (locale === "zh" ? "已减少动态效果" : "Reduced motion") : paused ? (locale === "zh" ? "让秋风继续" : "Resume motion") : (locale === "zh" ? "让秋风暂停" : "Pause motion")}
    </button>
  )
}
