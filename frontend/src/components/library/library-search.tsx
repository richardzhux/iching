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
  titleEn: string
  meaningEn: string
  themes: readonly string[]
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
          title: "检索经典档案",
          placeholder: "乾、qian、屯、difficulty、利贞、takashima...",
          empty: "没有匹配的卦页或来源片段。",
          open: "打开卦页",
        }
      : {
          title: "Search the Yi",
          placeholder: "qian, 屯, difficulty, 利贞, takashima...",
          empty: "No matching hexagram or source snippet.",
          open: "Open hexagram",
        }

  const results = useMemo(() => {
    const needle = normalize(query.trim())
    if (!needle) return documents.slice(0, 8)
    return documents
      .map((document) => {
        const titleHaystack = normalize(
          [
            document.number.toString(),
            document.nameZh,
            document.shortNameZh,
            document.pinyin,
            document.titleEn,
            document.meaningEn,
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
      .slice(0, 12)
      .map((entry) => entry.document)
  }, [documents, query])

  return (
    <section className="rounded-lg border border-border/60 bg-surface p-5">
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
        className="mt-3 h-11 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
      <div className="mt-4 grid gap-2 md:grid-cols-2">
        {results.map((result) => (
          <Link
            key={result.slug}
            href={withLocale(locale, `/hexagram/${result.slug}`)}
            className="rounded-md border border-border/60 bg-surface-elevated p-3 transition hover:border-primary/50"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs text-muted-foreground">#{result.number.toString().padStart(2, "0")}</p>
                <p className="mt-1 text-sm font-semibold text-foreground">
                  {result.nameZh} · {result.pinyin}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{result.titleEn}</p>
              </div>
              <span className="text-xs font-semibold text-primary">{labels.open}</span>
            </div>
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">
              {result.sourceSnippet || result.meaningEn}
            </p>
          </Link>
        ))}
      </div>
      {!results.length && <p className="mt-4 text-sm text-muted-foreground">{labels.empty}</p>}
    </section>
  )
}
