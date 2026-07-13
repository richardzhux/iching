import { cn } from "@/lib/utils"

export type HexagramGlyphLine = "0" | "1" | "yin" | "yang"

type Props = {
  lines: readonly HexagramGlyphLine[]
  className?: string
  lineClassName?: string
}

export function HexagramGlyph({ lines, className, lineClassName }: Props) {
  return (
    <div className={cn("grid w-16 gap-2 text-foreground", className)} aria-hidden="true">
      {lines.map((line, index) => {
        const isYang = line === "1" || line === "yang"
        return (
          <span key={`${line}-${index}`} className={cn("flex h-2 w-full items-center", lineClassName)}>
            {isYang ? (
              <span className="h-full w-full rounded-full bg-current" />
            ) : (
              <span className="flex h-full w-full items-center gap-[18%]">
                <span className="h-full flex-1 rounded-full bg-current" />
                <span className="h-full flex-1 rounded-full bg-current" />
              </span>
            )}
          </span>
        )
      })}
    </div>
  )
}
