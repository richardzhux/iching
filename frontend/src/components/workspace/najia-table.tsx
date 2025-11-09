"use client"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { NajiaTable } from "@/types/api"

import { LineGlyph } from "./line-glyph"

type NajiaTableProps = {
  table?: NajiaTable
}

export function NajiaTableView({ table }: NajiaTableProps) {
  if (!table || !table.rows?.length) {
    return null
  }

  return (
    <Card className="border-border/40 bg-white/70 shadow-glass dark:border-white/10 dark:bg-white/5">
      <CardContent className="p-5">
        <div className="space-y-3">
          {table.rows.map((row) => {
            const changedType: "yang" | "yin" = row.changed_line_type || row.line_type
            return (
              <div
                key={row.position}
                className="grid gap-4 rounded-2xl border border-border/40 bg-foreground/[0.03] p-4 text-sm dark:border-white/10 dark:bg-white/5 md:grid-cols-[110px,1fr,1fr]"
              >
                <div className="flex flex-col gap-1">
                  <p className="text-[0.65rem] uppercase tracking-[0.4rem] text-muted-foreground">六神</p>
                  <p className="text-base font-semibold">{row.god || "—"}</p>
                  {row.hidden && <p className="text-xs text-muted-foreground">伏神：{row.hidden}</p>}
                </div>
                <NajiaLineColumn
                  label={`第${row.position}爻`}
                  relation={row.main_relation}
                  marker={row.marker}
                  movement={row.movement_tag}
                  lineType={row.line_type}
                  highlight={row.is_moving}
                />
                <NajiaLineColumn
                  label="变卦"
                  relation={row.changed_relation}
                  marker=""
                  movement=""
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
  movement: string
  lineType: "yang" | "yin"
  highlight?: boolean
  muted?: boolean
}

function NajiaLineColumn({
  label,
  relation,
  marker,
  movement,
  lineType,
  highlight = false,
  muted = false,
}: NajiaLineColumnProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-2xl border px-3 py-2",
        muted
          ? "border-border/30 bg-transparent dark:border-white/5"
          : "border-white/50 bg-white/80 shadow-inner dark:border-white/10 dark:bg-white/5"
      )}
    >
      <div className="flex items-center justify-between text-xs uppercase tracking-widest text-muted-foreground">
        <span>{label}</span>
        {marker && <span className="text-sky-500">{marker}</span>}
      </div>
      <p className="text-sm font-semibold text-foreground dark:text-white">{relation || "—"}</p>
      <div className="flex items-center gap-2">
        <LineGlyph variant={lineType} highlight={highlight} />
        {movement && (
          <span className="text-[0.65rem] uppercase tracking-widest text-amber-500">{movement}</span>
        )}
      </div>
    </div>
  )
}
