"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { useI18n } from "@/components/providers/i18n-provider"
import { CastForm } from "@/components/workspace/cast-form"
import { HistoryDrawer } from "@/components/workspace/history-drawer"
import { ResultsPanel } from "@/components/workspace/results-panel"
import { useConfigQuery } from "@/lib/queries"
import { cn } from "@/lib/utils"
import { useWorkspaceStore } from "@/lib/store"
import { BookOpen, Loader2, RotateCw } from "lucide-react"
import { motion, AnimatePresence, useReducedMotion } from "framer-motion"

export function CastWorkspace() {
  const { messages, toLocalePath } = useI18n()
  const reduceMotion = useReducedMotion()
  const view = useWorkspaceStore((state) => state.view)
  const reopenResults = useWorkspaceStore((state) => state.reopenResults)
  const hasResult = useWorkspaceStore((state) => Boolean(state.result))
  const { data, isLoading, isFetching, error, refetch } = useConfigQuery()
  const errorDetail = error instanceof Error ? error.message : messages.common.unknownError

  if (isLoading) {
    return (
      <div className="surface-card min-h-[50vh] rounded-lg p-6">
        <div className="mx-auto flex max-w-3xl flex-col items-center justify-center py-12 text-center">
          <div className="inline-flex items-center gap-3 rounded-md border border-border/60 bg-surface-elevated px-4 py-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            {messages.workspace.loadingConfig}
          </div>
          <h1 className="mt-6 text-2xl font-semibold text-foreground">{messages.workspace.loadingConfigTitle}</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">{messages.workspace.loadingConfigBody}</p>
          <div className="mt-6 grid w-full gap-3 sm:grid-cols-3">
            {[messages.workspace.results.mainHexLabel, messages.workspace.results.primarySectionTitle, messages.workspace.history.title].map((label) => (
              <div key={label} className="h-24 rounded-lg border border-border/50 bg-surface-elevated/70 p-4 text-left">
                <p className="h-3 w-24 rounded bg-muted" />
                <p className="mt-4 h-3 w-32 rounded bg-muted/70" />
                <p className="mt-3 h-3 w-20 rounded bg-muted/60" />
                <span className="sr-only">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="surface-card min-h-[50vh] rounded-lg p-6">
        <div className="mx-auto flex max-w-2xl flex-col items-center justify-center py-12 text-center">
          <p className="kicker">{messages.workspace.headerKicker}</p>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">{messages.workspace.configErrorTitle}</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">{messages.workspace.configErrorHint}</p>
          {process.env.NODE_ENV !== "production" && (
            <p className="mt-3 rounded-md border border-border/60 bg-surface-elevated px-3 py-2 text-xs text-muted-foreground">
              {errorDetail}
            </p>
          )}
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Button type="button" variant="default" className="rounded-md" disabled={isFetching} onClick={() => refetch()}>
              {isFetching ? <Loader2 className="mr-2 size-4 animate-spin" /> : <RotateCw className="mr-2 size-4" />}
              {messages.workspace.configRetryCta}
            </Button>
            <Button asChild type="button" variant="outline" className="rounded-md">
              <Link href={toLocalePath("/")}>{messages.workspace.sampleReadingCta}</Link>
            </Button>
            <Button asChild type="button" variant="outline" className="rounded-md">
              <Link href={toLocalePath("/library")}>
                <BookOpen className="mr-2 size-4" />
                {messages.workspace.libraryCta}
              </Link>
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className={cn("space-y-5", "xl:space-y-6")}>
      <header className="mx-auto max-w-5xl border-b border-border/60 pb-5">
        <p className="kicker">{messages.workspace.headerKicker}</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          {messages.workspace.headerTitle}
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
          {messages.workspace.headerDescription}
        </p>
      </header>
      <AnimatePresence mode="wait">
        {view === "form" ? (
	          <motion.div
	            key="form"
	            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
	            animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
	            exit={reduceMotion ? undefined : { opacity: 0, y: -10 }}
	            transition={{ duration: reduceMotion ? 0 : 0.2 }}
          >
            <div className="space-y-4">
              <CastForm config={data} />
              {hasResult && (
                <Button
                  variant="outline"
                  onClick={() => reopenResults()}
                  className="w-full rounded-lg"
                >
                  {messages.workspace.viewLastResult}
                </Button>
              )}
            </div>
          </motion.div>
        ) : (
	          <motion.div
	            key="results"
	            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
	            animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
	            exit={reduceMotion ? undefined : { opacity: 0, y: -10 }}
	            transition={{ duration: reduceMotion ? 0 : 0.2 }}
          >
            <ResultsPanel />
          </motion.div>
        )}
      </AnimatePresence>
      {view === "results" && <HistoryDrawer />}
    </div>
  )
}
