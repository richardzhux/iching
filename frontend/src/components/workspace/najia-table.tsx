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
          <div className="hidden border-b border-border/35 px-3 py-2 text-[0.68rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground md:grid md:grid-cols-[7rem_minmax(0,1fr)_2.5rem_minmax(0,1fr)]">
            <span>{messages.workspace.results.sixGodLabel}</span>
            <span>{messages.workspace.results.mainHexLabel}</span>
            <span className="text-center">{locale === "zh" ? "动" : "Move"}</span>
            <span>{messages.workspace.results.changedHexLabel}</span>
          </div>
          {table.rows.map((row) => {
            const rowMarker = row.marker
            return (
              <div
                key={row.position}
                className="grid gap-2 border-b border-border/25 px-3 py-2 text-sm last:border-b-0 md:grid-cols-[7rem_minmax(0,1fr)_2.5rem_minmax(0,1fr)] md:items-center"
              >
                <div className="flex min-h-11 items-center justify-between gap-2 md:block">
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
                  highlight={row.is_moving}
                />
                <div className="hidden text-center text-sm font-semibold md:block">
                  {row.movement_tag ? (
                    <span className="imperial-text">{row.movement_tag}</span>
                  ) : (
                    <span className="text-muted-foreground/40">·</span>
                  )}
                </div>
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
  highlight?: boolean
  muted?: boolean
}

function NajiaLineColumn({
  label,
  relation,
  marker,
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
        "flex min-h-11 items-center rounded-md border px-2.5 py-1.5",
        muted
          ? "border-border/30 bg-transparent dark:border-primary/10"
          : "border-border/50 bg-surface/80 shadow-inner dark:border-primary/15 dark:bg-primary/5"
      )}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[0.68rem] uppercase tracking-[0.1rem] text-muted-foreground">
          <span>{label}</span>
          {marker && <span className="text-primary">{marker}</span>}
        </div>
        <p className={relationClasses}>{relation || "—"}</p>
      </div>
    </div>
  )
}
