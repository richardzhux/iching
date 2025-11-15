"use client"

import { Button } from "@/components/ui/button"
import { CastForm } from "@/components/workspace/cast-form"
import { HistoryDrawer } from "@/components/workspace/history-drawer"
import { ResultsPanel } from "@/components/workspace/results-panel"
import { useConfigQuery } from "@/lib/queries"
import { cn } from "@/lib/utils"
import { useWorkspaceStore } from "@/lib/store"
import { Loader2 } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

export function CastWorkspace() {
  const view = useWorkspaceStore((state) => state.view)
  const reopenResults = useWorkspaceStore((state) => state.reopenResults)
  const hasResult = useWorkspaceStore((state) => Boolean(state.result))
  const { data, isLoading, error } = useConfigQuery()

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="glass-panel inline-flex items-center gap-3 rounded-2xl px-6 py-4 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          正在加载配置…
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="glass-panel rounded-2xl px-6 py-4 text-center text-destructive">
          无法获取后端配置，请检查 FastAPI 服务是否运行。<br />
          {(error as Error).message}
        </div>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className={cn("space-y-8", "xl:space-y-10")}>
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
                  className="w-full"
                >
                  查看上一条占卜结果
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
