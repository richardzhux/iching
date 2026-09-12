"use client"

import { useSyncExternalStore } from "react"
import { X } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useWorkspaceStore } from "@/lib/store"
import type { SessionPayload } from "@/types/api"
import { ChatPanel } from "./chat-panel"

const desktopQuery = "(min-width: 1200px)"
const subscribe = (callback: () => void) => {
  const media = window.matchMedia(desktopQuery)
  media.addEventListener("change", callback)
  return () => media.removeEventListener("change", callback)
}

export function ReadingFollowup({ session, prompts, desktopOpen, onDesktopOpenChange, mobileOpen, onMobileOpenChange }: {
  session: SessionPayload
  prompts: string[]
  desktopOpen: boolean
  onDesktopOpenChange: (open: boolean) => void
  mobileOpen: boolean
  onMobileOpenChange: (open: boolean) => void
}) {
  const { locale } = useI18n()
  const desktop = useSyncExternalStore(subscribe, () => window.matchMedia(desktopQuery).matches, () => false)
  const setPendingChatPrompt = useWorkspaceStore((state) => state.setPendingChatPrompt)
  const title = locale === "zh" ? "继续追问" : "Ask about this reading"
  const content = <>
    {prompts.length ? <details className="reading-chat-suggestions"><summary>{locale === "zh" ? "试着这样问" : "Suggested questions"}</summary><div>{prompts.map((prompt) => <button key={prompt} type="button" onClick={() => setPendingChatPrompt(prompt)}>{prompt}</button>)}</div></details> : null}
    <ChatPanel session={session} embedded />
  </>
  if (!desktop) return <Sheet open={mobileOpen} onOpenChange={onMobileOpenChange}><SheetContent className="reading-chat-sheet w-full sm:max-w-lg" aria-describedby={undefined}><SheetHeader><SheetTitle>{title}</SheetTitle></SheetHeader>{content}</SheetContent></Sheet>
  return <aside id="ai-followup" className="reading-chat-sidebar" hidden={!desktopOpen} aria-label={title}>
    <header><h2>{title}</h2><Button type="button" variant="ghost" size="icon-sm" aria-label={locale === "zh" ? "收起追问" : "Close follow-up"} onClick={() => onDesktopOpenChange(false)}><X size={16} /></Button></header>
    {content}
  </aside>
}
