"use client"

import { useI18n } from "@/components/providers/i18n-provider"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { NajiaTable } from "@/types/api"

type NajiaTableProps = {
  table?: NajiaTable
}

export function NajiaTableView({ table }: NajiaTableProps) {
  const { messages, locale } = useI18n()
  if (!table || !table.rows?.length) {
    return null
  }

  return (
    <Card className="surface-card border-border/40">
      <CardContent className="p-2 sm:p-3">
        <div className="overflow-hidden rounded-lg border border-border/40 bg-foreground/[0.025] dark:border-primary/15 dark:bg-primary/5">
          <div className="grid grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1fr)] border-b border-border/35 px-2 py-2 text-[0.65rem] font-semibold uppercase tracking-[0.12rem] text-muted-foreground sm:grid-cols-[6rem_minmax(0,1fr)_minmax(0,1fr)] sm:px-3">
            <span>{messages.workspace.results.sixGodLabel}</span>
            <span>{messages.workspace.results.mainHexLabel}</span>
            <span>{messages.workspace.results.changedHexLabel}</span>
          </div>
          {table.rows.map((row) => {
            const rowMarker = row.marker
            return (
              <div
                key={row.position}
                className="grid grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1fr)] items-center gap-1 border-b border-border/25 px-2 py-1.5 text-sm last:border-b-0 sm:grid-cols-[6rem_minmax(0,1fr)_minmax(0,1fr)] sm:gap-2 sm:px-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold leading-5">{row.god || "—"}</p>
                  {row.hidden && (
                    <p className="truncate text-[0.72rem] leading-4 text-muted-foreground">
                      {locale === "zh" ? "伏神" : "Hidden"}: {row.hidden}
                    </p>
                  )}
                </div>
                <NajiaLineColumn
                  label={locale === "zh" ? `第${row.position}爻` : `Line ${row.position}`}
                  relation={row.main_relation}
                  marker={rowMarker}
                  movementTag={row.movement_tag}
                  highlight={row.is_moving}
                />
                <NajiaLineColumn
                  label={messages.workspace.results.changedHexLabel}
                  relation={row.changed_relation}
                  marker=""
                  highlight={row.is_moving}
                  muted
                />
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

type NajiaLineColumnProps = {
  label: string
  relation: string
  marker: string
  movementTag?: string
  highlight?: boolean
  muted?: boolean
}

function NajiaLineColumn({
  label,
  relation,
  marker,
  movementTag,
  highlight = false,
  muted = false,
}: NajiaLineColumnProps) {
  const relationClasses = cn(
    "truncate text-sm font-semibold leading-5",
    highlight ? "imperial-text" : "text-foreground"
  )

  return (
    <div
      className={cn(
        "flex min-h-9 items-center rounded-md border px-2 py-1",
        muted
          ? "border-border/30 bg-transparent dark:border-primary/10"
          : "border-border/50 bg-surface/80 shadow-inner dark:border-primary/15 dark:bg-primary/5"
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-[0.62rem] uppercase tracking-[0.06rem] text-muted-foreground">
          <span className="sr-only">{label}</span>
          {marker && <span className="text-primary">{marker}</span>}
          {movementTag && <span className="imperial-text">{movementTag}</span>}
        </div>
        <p className={relationClasses}>{relation || "—"}</p>
      </div>
    </div>
  )
}
