"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import type { Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { trackProductEvent } from "@/lib/analytics"
import { HEXAGRAM_THEME_FILTERS, matchesThemeFilter } from "@/lib/hexagram-copy"

export type LibrarySearchDocument = {
  slug: string
  number: number
  nameZh: string
  shortNameZh: string
  pinyin: string
  title: string
  meaning: string
  themes: readonly string[]
  localizedThemes: string[]
  sourceSnippet: string
}

type Props = {
  locale: Locale
  documents: LibrarySearchDocument[]
}

function normalize(value: string) {
  return value.toLowerCase().normalize("NFKD").replace(/\p{Diacritic}/gu, "")
}

export function LibrarySearch({ locale, documents }: Props) {
  const [query, setQuery] = useState("")
  const [activeTheme, setActiveTheme] = useState("")
  const themeFilters = HEXAGRAM_THEME_FILTERS
  const labels =
    locale === "zh"
      ? {
          title: "查卦名与卦意",
          placeholder: "乾、qian、屯、利贞、时机、感情...",
          empty: "没有找到匹配的卦，试试卦名、处境或主题。",
          open: "打开卦页",
          allThemes: "全部",
          showing: (displayed: number, matched: number) => `显示 ${displayed} / ${matched} 个结果`,
        }
      : {
          title: "Search the Yi",
          placeholder: "qian, difficulty, waiting, relationships...",
          empty: "No matching hexagram. Try a name, situation, or theme.",
          open: "Open hexagram",
          allThemes: "All",
          showing: (displayed: number, matched: number) =>
            `Showing ${displayed} of ${matched} ${matched === 1 ? "result" : "results"}`,
        }

  const matchedResults = useMemo(() => {
    const needle = normalize(query.trim())
    const filteredByTheme = activeTheme
      ? documents.filter((document) => matchesThemeFilter(document.themes, activeTheme))
      : documents
    if (!needle) return filteredByTheme
    return filteredByTheme
      .map((document) => {
        const titleHaystack = normalize(
          [
            document.number.toString(),
            document.nameZh,
            document.shortNameZh,
            document.pinyin,
            document.title,
            document.meaning,
            document.themes.join(" "),
          ].join(" "),
        )
        const sourceHaystack = normalize(document.sourceSnippet)
        const score =
          titleHaystack.includes(needle)
            ? 3
            : sourceHaystack.includes(needle)
              ? 1
              : 0
        return { document, score }
      })
      .filter((entry) => entry.score > 0)
      .sort((a, b) => b.score - a.score || a.document.number - b.document.number)
      .map((entry) => entry.document)
  }, [activeTheme, documents, query])

  const displayedResults = matchedResults.slice(0, query.trim() || activeTheme ? 12 : 8)

  return (
    <section className="border-b border-border/60 pb-7">
      <label htmlFor="library-search" className="text-sm font-semibold text-foreground">
        {labels.title}
      </label>
      <input
        id="library-search"
        value={query}
        onChange={(event) => {
          const next = event.target.value
          setQuery(next)
          if (next.trim().length >= 2) {
            trackProductEvent("library_search_used", { locale, query_length: next.trim().length })
          }
        }}
        placeholder={labels.placeholder}
        className="mt-3 h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      />
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1" aria-label={locale === "zh" ? "按主题筛选" : "Filter by theme"}>
        <button
          type="button"
          onClick={() => setActiveTheme("")}
          aria-pressed={!activeTheme}
          className="min-h-11 shrink-0 rounded-md px-3 text-sm font-medium outline-none transition hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring"
        >
          {labels.allThemes}
        </button>
        {themeFilters.map((filter) => (
          <button
            type="button"
            key={filter.id}
            onClick={() => setActiveTheme(filter.id)}
            aria-pressed={activeTheme === filter.id}
            className="min-h-11 shrink-0 rounded-md px-3 text-sm font-medium outline-none transition hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring aria-pressed:bg-primary/10 aria-pressed:text-primary"
          >
            {filter[locale]}
          </button>
        ))}
      </div>
      <p className="mt-3 text-sm text-muted-foreground" role="status" aria-live="polite">
        {labels.showing(displayedResults.length, matchedResults.length)}
      </p>
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {displayedResults.map((result) => (
          <Link
            key={result.slug}
            href={withLocale(locale, `/hexagram/${result.slug}`)}
            className="rounded-md border border-border/60 bg-surface-elevated p-3 outline-none transition hover:border-primary/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs text-muted-foreground">#{result.number.toString().padStart(2, "0")}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {result.nameZh} · {result.pinyin}
                </p>
                {locale === "en" && <p className="mt-1 text-xs text-muted-foreground">{result.title}</p>}
              </div>
              <span className="text-xs font-semibold text-primary">{labels.open}</span>
            </div>
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">
              {result.sourceSnippet || result.meaning}
            </p>
            <p className="mt-2 text-[11px] text-muted-foreground">{result.localizedThemes.join(" · ")}</p>
          </Link>
        ))}
      </div>
      {!matchedResults.length && <p className="mt-4 text-sm text-muted-foreground">{labels.empty}</p>}
    </section>
  )
}
