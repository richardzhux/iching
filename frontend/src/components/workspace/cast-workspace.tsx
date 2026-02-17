"use client"

import { Button } from "@/components/ui/button"
import { useI18n } from "@/components/providers/i18n-provider"
import { CastForm } from "@/components/workspace/cast-form"
import { HistoryDrawer } from "@/components/workspace/history-drawer"
import { ResultsPanel } from "@/components/workspace/results-panel"
import { useConfigQuery } from "@/lib/queries"
import { cn } from "@/lib/utils"
import { useWorkspaceStore } from "@/lib/store"
import { Loader2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

export function CastWorkspace() {
  const { messages } = useI18n()
  const view = useWorkspaceStore((state) => state.view)
  const reopenResults = useWorkspaceStore((state) => state.reopenResults)
  const hasResult = useWorkspaceStore((state) => Boolean(state.result))
  const { data, isLoading, error } = useConfigQuery()

  if (isLoading) {
    return (
      <div className="surface-card flex min-h-[50vh] items-center justify-center rounded-3xl p-8">
        <div className="inline-flex items-center gap-3 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          {messages.workspace.loadingConfig}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="surface-card flex min-h-[50vh] items-center justify-center rounded-3xl p-8">
        <div className="max-w-xl text-center text-destructive">
          <p className="font-medium">{messages.workspace.configErrorTitle}</p>
          <p className="mt-1 text-sm text-muted-foreground">{messages.workspace.configErrorHint}</p>
          <p className="mt-2 text-xs">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className={cn("space-y-6", "xl:space-y-8")}>
      <header className="surface-card rounded-3xl p-6 sm:p-7">
        <p className="kicker">{messages.workspace.headerKicker}</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          {messages.workspace.headerTitle}
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          {messages.workspace.headerDescription}
        </p>
      </header>
      <AnimatePresence mode="wait">
        {view === "form" ? (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="space-y-4">
              <CastForm config={data} />
              {hasResult && (
                <Button
                  variant="outline"
                  onClick={() => reopenResults()}
                  className="w-full rounded-2xl"
                >
                  {messages.workspace.viewLastResult}
                </Button>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <ResultsPanel />
          </motion.div>
        )}
      </AnimatePresence>
      {view === "results" && <HistoryDrawer />}
    </div>
  )
}
