"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import type { Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { trackProductEvent } from "@/lib/analytics"

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
  const labels =
    locale === "zh"
      ? {
          title: "查卦名与卦意",
          placeholder: "乾、qian、第 3 卦、利贞...",
          empty: "没有找到匹配的卦，试试卦名、拼音、编号或原文。",
          open: "打开卦页",
          showing: (displayed: number, matched: number) => `显示 ${displayed} / ${matched} 个结果`,
        }
      : {
          title: "Search the Yi",
          placeholder: "qian, hexagram 3, difficulty, judgment...",
          empty: "No matching hexagram. Try a name, pinyin, number, or source phrase.",
          open: "Open hexagram",
          showing: (displayed: number, matched: number) =>
            `Showing ${displayed} of ${matched} ${matched === 1 ? "result" : "results"}`,
        }

  const matchedResults = useMemo(() => {
    const needle = normalize(query.trim())
    if (!needle) return documents
    return documents
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
  }, [documents, query])

  const displayedResults = matchedResults.slice(0, query.trim() ? 12 : 8)

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
