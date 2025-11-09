"use client"

import { CastForm } from "@/components/workspace/cast-form"
import { HistoryDrawer } from "@/components/workspace/history-drawer"
import { ResultsPanel } from "@/components/workspace/results-panel"
import { useConfigQuery } from "@/lib/queries"
import { cn } from "@/lib/utils"
import { Loader2 } from "lucide-react"

export function CastWorkspace() {
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
    <div
      className={cn(
        "grid gap-8",
        "lg:grid-cols-[minmax(320px,380px),1fr]",
        "xl:grid-cols-[360px,1fr]",
      )}
    >
      <div className="space-y-6">
        <CastForm config={data} />
      </div>
      <div className="space-y-6">
        <ResultsPanel />
        <HistoryDrawer />
      </div>
    </div>
  )
}
