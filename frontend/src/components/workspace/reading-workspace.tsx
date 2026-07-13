"use client"

import Link from "next/link"
import { useSyncExternalStore } from "react"
import { BookOpen, Loader2 } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { HistoryDrawer } from "@/components/workspace/history-drawer"
import { ResultsPanel } from "@/components/workspace/results-panel"
import { useWorkspaceStore } from "@/lib/store"

const subscribe = (callback: () => void) => useWorkspaceStore.persist.onFinishHydration(callback)
const snapshot = () => useWorkspaceStore.persist.hasHydrated()
const serverSnapshot = () => false

export function ReadingWorkspace() {
  const { locale, toLocalePath } = useI18n()
  const hydrated = useSyncExternalStore(subscribe, snapshot, serverSnapshot)
  const result = useWorkspaceStore((state) => state.result)

  if (!hydrated) {
    return <div className="flex min-h-[45vh] items-center justify-center gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />{locale === "zh" ? "正在恢复上一卦…" : "Restoring your reading…"}</div>
  }

  if (!result) {
    return (
      <section className="surface-card mx-auto max-w-2xl rounded-xl p-7 text-center sm:p-10">
        <BookOpen className="mx-auto size-8 text-primary" />
        <h1 className="mt-4 text-2xl font-semibold">{locale === "zh" ? "还没有可继续的卦例" : "No active reading yet"}</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{locale === "zh" ? "完成起卦后会自动来到这里；已登录用户也可从“我的”恢复云端卦例。" : "After casting, the full reading opens here automatically. Signed-in users can also restore a saved case from My."}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3"><Button asChild><Link href={toLocalePath("/app")}>{locale === "zh" ? "现在起卦" : "Cast now"}</Link></Button><Button asChild variant="outline"><Link href={toLocalePath("/profile")}>{locale === "zh" ? "查看我的卦例" : "Open my readings"}</Link></Button></div>
      </section>
    )
  }

  return <div className="space-y-5"><ResultsPanel /><HistoryDrawer /></div>
}
