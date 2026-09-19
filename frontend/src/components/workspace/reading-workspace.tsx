"use client"

import Link from "next/link"
import { useSearchParams } from "next/navigation"
import { useEffect, useSyncExternalStore } from "react"
import { Loader2 } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { HistoryDrawer } from "@/components/workspace/history-drawer"
import { ResultsPanel } from "@/components/workspace/results-panel"
import { useSupabaseAuth } from "@/hooks/use-supabase-auth"
import { useSessionQuery } from "@/lib/queries"
import { useWorkspaceStore } from "@/lib/store"

const subscribe = (callback: () => void) => useWorkspaceStore.persist.onFinishHydration(callback)
const snapshot = () => useWorkspaceStore.persist.hasHydrated()
const serverSnapshot = () => false

export function ReadingWorkspace() {
  const { locale, toLocalePath } = useI18n()
  const hydrated = useSyncExternalStore(subscribe, snapshot, serverSnapshot)
  const result = useWorkspaceStore((state) => state.result)
  const setResult = useWorkspaceStore((state) => state.setResult)
  const searchParams = useSearchParams()
  const auth = useSupabaseAuth()
  const requestedSession = searchParams.get("session")

  // A reading is addressable by id, so a link survives a reset or a different
  // device. Only fetch when the store does not already hold that reading.
  const wantsSession = Boolean(
    hydrated && requestedSession && result?.session_id !== requestedSession,
  )
  const sessionQuery = useSessionQuery(requestedSession, auth.accessToken, wantsSession)
  const signInRequired = wantsSession && !auth.loading && !auth.accessToken

  useEffect(() => {
    if (sessionQuery.data) setResult(sessionQuery.data)
  }, [sessionQuery.data, setResult])

  const failureMessage = signInRequired
    ? locale === "zh"
      ? "登录后才能打开这条卦例链接。"
      : "Sign in to open this reading link."
    : sessionQuery.error
      ? (sessionQuery.error as Error).message ||
        (locale === "zh" ? "无法打开这条卦例。" : "This reading could not be opened.")
      : null

  if (!hydrated || (wantsSession && sessionQuery.isFetching)) {
    return (
      <div className="flex min-h-[45vh] items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        {locale === "zh" ? "正在恢复上一卦…" : "Restoring your reading…"}
      </div>
    )
  }

  if (!result) {
    return (
      <section className="autumn-study autumn-empty mx-auto max-w-2xl border-y border-border bg-surface p-7 text-center sm:p-10">
        <h1 className="autumn-page-title">
          {failureMessage
            ? locale === "zh"
              ? "打不开这条卦例"
              : "This reading could not be opened"
            : locale === "zh"
              ? "还没有可继续的卦例"
              : "No active reading yet"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {failureMessage
            ? failureMessage
            : locale === "zh"
              ? "完成起卦后会自动来到这里；已登录用户也可从“我的”恢复云端卦例。"
              : "After casting, the full reading opens here automatically. Signed-in users can also restore a saved case from My."}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Button asChild>
            <Link href={toLocalePath("/app")}>{locale === "zh" ? "现在起卦" : "Cast now"}</Link>
          </Button>
          <Button asChild variant="outline">
            <Link href={toLocalePath("/profile")}>
              {locale === "zh" ? "查看我的卦例" : "Open my readings"}
            </Link>
          </Button>
        </div>
      </section>
    )
  }

  return (
    <div>
      <ResultsPanel />
      <div className="mx-auto max-w-5xl px-6 pb-12">
        <HistoryDrawer />
      </div>
    </div>
  )
}
