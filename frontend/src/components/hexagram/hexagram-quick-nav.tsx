import Link from "next/link"
import type { Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { HEXAGRAM_LIBRARY } from "@/lib/hexagram-library"
import { cn } from "@/lib/utils"

type Props = {
  locale: Locale
  mode: "anchors" | "routes"
  activeSlug?: string
}

function HexagramLinks({ locale, mode, activeSlug, compact }: Props & { compact: boolean }) {
  return HEXAGRAM_LIBRARY.map((entry) => {
    const active = entry.slug === activeSlug
    const href = mode === "anchors" ? `#hexagram-${entry.number}` : withLocale(locale, `/hexagram/${entry.slug}`)
    return (
      <Link
        key={entry.slug}
        href={href}
        aria-current={active ? "page" : undefined}
        className={cn(
          "autumn-hexagram-index shrink-0 text-sm outline-none transition focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          compact ? "flex min-h-11 items-center gap-2 px-3 py-2" : "flex min-h-11 items-center gap-2 px-2.5 py-2",
          active ? "bg-primary/10 font-semibold text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground",
        )}
      >
        <span className="tabular-nums text-xs opacity-70">{entry.number.toString().padStart(2, "0")}</span>
        <span>{entry.shortNameZh}</span>
      </Link>
    )
  })
}

export function HexagramQuickNav({ locale, mode, activeSlug }: Props) {
  const label = locale === "zh" ? "六十四卦快速导航" : "Browse 64 hexagrams"
  const title = locale === "zh" ? "六十四卦" : "64 hexagrams"
  return (
    <>
      <nav aria-label={label} className="autumn-library-index sticky top-24 hidden max-h-[calc(100vh-7rem)] overflow-y-auto pr-3 lg:block">
        <p className="sticky top-0 z-10 bg-background pb-3 text-sm font-semibold text-foreground">{title}</p>
        <div className="grid grid-cols-2 gap-1.5">
          <HexagramLinks locale={locale} mode={mode} activeSlug={activeSlug} compact={false} />
        </div>
      </nav>
      <nav aria-label={label} className="autumn-library-index py-2 lg:hidden">
        <div className="flex gap-1.5 overflow-x-auto pb-2">
          <HexagramLinks locale={locale} mode={mode} activeSlug={activeSlug} compact />
        </div>
      </nav>
    </>
  )
}
