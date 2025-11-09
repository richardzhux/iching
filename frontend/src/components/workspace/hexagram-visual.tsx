"use client"

import { ArrowRight } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { HexOverview } from "@/types/api"

import type { NajiaTable } from "@/types/api"

type HexagramHeaderProps = {
  overview?: HexOverview
  najiaMeta?: NajiaTable["meta"]
}

export function HexagramHeader({ overview, najiaMeta }: HexagramHeaderProps) {
  if (!overview) {
    return null
  }

  return (
    <Card className="border-border/50 bg-white/70 shadow-glass dark:border-white/10 dark:bg-white/5">
      <CardContent className="p-5">
        <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">卦象总览</p>
        <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-center">
          <HexagramCard
            label="本卦"
            name={overview.main_hexagram?.name}
            explanation={overview.main_hexagram?.explanation}
            tag={najiaMeta?.main?.type}
          />
          {overview.changed_hexagram && (
            <div className="flex items-center gap-3">
              <ArrowRight className="h-5 w-5 text-amber-500" />
              <HexagramCard
                label="变卦"
                name={overview.changed_hexagram.name}
                explanation={overview.changed_hexagram.explanation}
                tag={najiaMeta?.changed?.type}
                accent
              />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

type HexagramCardProps = {
  label: string
  name?: string
  explanation?: string
  tag?: string | null
  accent?: boolean
}

function HexagramCard({ label, name, explanation, tag, accent = false }: HexagramCardProps) {
  return (
    <div
      className={cn(
        "flex-1 rounded-2xl border p-4",
        accent
          ? "border-amber-400/60 bg-amber-200/20 dark:border-amber-200/40 dark:bg-amber-200/10"
          : "border-border/30 bg-foreground/[0.03] dark:border-white/10 dark:bg-white/5"
      )}
    >
      <p className="text-[0.65rem] uppercase tracking-[0.4rem] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground dark:text-white">{name || "—"}</p>
      {tag && (
        <span className="mt-1 inline-flex rounded-full border border-amber-400/60 px-3 py-0.5 text-xs font-semibold text-amber-600 dark:border-amber-200/50 dark:text-amber-200">
          {tag}
        </span>
      )}
      {explanation && <p className="mt-1 text-sm text-muted-foreground">{explanation}</p>}
    </div>
  )
}
