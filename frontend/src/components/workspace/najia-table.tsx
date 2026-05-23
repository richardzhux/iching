"use client"

import { useI18n } from "@/components/providers/i18n-provider"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { NajiaTable } from "@/types/api"

import { LineGlyph } from "./line-glyph"

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
      <CardContent className="p-3 sm:p-4">
        <div className="space-y-2">
          {table.rows.map((row) => {
            const changedType: "yang" | "yin" = row.changed_line_type || row.line_type
            return (
              <div
                key={row.position}
                className="grid gap-2 rounded-md border border-border/40 bg-foreground/[0.025] p-2.5 text-sm dark:border-primary/15 dark:bg-primary/5 md:grid-cols-[8.25rem_minmax(0,1fr)_minmax(0,1fr)] md:items-stretch"
              >
                <div className="flex min-h-16 flex-col justify-center gap-0.5 px-1">
                  <p className="text-[0.62rem] uppercase tracking-[0.28rem] text-muted-foreground">{messages.workspace.results.sixGodLabel}</p>
                  <p className="text-sm font-semibold leading-5">{row.god || "—"}</p>
                  {row.hidden && (
                    <p className="text-[0.72rem] leading-4 text-muted-foreground">
                      {locale === "zh" ? "伏神" : "Hidden"}: {row.hidden}
                    </p>
                  )}
                </div>
                <NajiaLineColumn
                  label={locale === "zh" ? `第${row.position}爻` : `Line ${row.position}`}
                  relation={row.main_relation}
                  marker={row.marker}
                  lineType={row.line_type}
                  highlight={row.is_moving}
                />
                <NajiaLineColumn
                  label={messages.workspace.results.changedHexLabel}
                  relation={row.changed_relation}
                  marker=""
                  lineType={changedType}
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
  lineType: "yang" | "yin"
  highlight?: boolean
  muted?: boolean
}

function NajiaLineColumn({
  label,
  relation,
  marker,
  lineType,
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
        "flex min-h-16 flex-col justify-center gap-1.5 rounded-md border px-3 py-2",
        muted
          ? "border-border/30 bg-transparent dark:border-primary/10"
          : "border-border/50 bg-surface/80 shadow-inner dark:border-primary/15 dark:bg-primary/5"
      )}
    >
      <div className="flex items-center justify-between gap-2 text-[0.7rem] uppercase tracking-[0.12rem] text-muted-foreground">
        <span>{label}</span>
        {marker && <span className="text-primary">{marker}</span>}
      </div>
      <p className={relationClasses}>{relation || "—"}</p>
      <div className="flex items-center">
        <LineGlyph variant={lineType} highlight={highlight} className="h-2.5 w-12" />
      </div>
    </div>
  )
}
