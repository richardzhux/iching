"use client"

import { cn } from "@/lib/utils"

type LineGlyphProps = {
  variant: "yang" | "yin"
  highlight?: boolean
  className?: string
}

export function LineGlyph({ variant, highlight = false, className }: LineGlyphProps) {
  return (
    <div className={cn("relative flex h-3 w-16 items-center justify-center", className)}>
      {variant === "yang" ? (
        <span
          className={cn(
            "h-[3px] w-full rounded-full bg-foreground/90 dark:bg-white",
            highlight && "bg-amber-500 dark:bg-amber-400"
          )}
        />
      ) : (
        <span className="flex w-full items-center justify-between">
          <span
            className={cn(
              "h-[3px] w-[38%] rounded-full bg-foreground/90 dark:bg-white",
              highlight && "bg-amber-500 dark:bg-amber-400"
            )}
          />
          <span
            className={cn(
              "h-[3px] w-[38%] rounded-full bg-foreground/90 dark:bg-white",
              highlight && "bg-amber-500 dark:bg-amber-400"
            )}
          />
        </span>
      )}
    </div>
  )
}
