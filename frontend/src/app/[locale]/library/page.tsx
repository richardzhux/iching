import type { Metadata } from "next"
import Link from "next/link"
import { defaultLocale, isLocale, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { LibrarySearch, type LibrarySearchDocument } from "@/components/library/library-search"
import { PUBLIC_SITE_URL } from "@/lib/env"
import { getHexagramArchive } from "@/lib/hexagram-archive"
import { localizedHexagramMeaning, localizedHexagramThemes } from "@/lib/hexagram-copy"
import { HEXAGRAM_LIBRARY, getHexagramPinyin, hexagramLines } from "@/lib/hexagram-library"

type Props = {
  params: Promise<{ locale: string }>
}

async function buildSearchDocuments(locale: Locale): Promise<LibrarySearchDocument[]> {
  return Promise.all(
    HEXAGRAM_LIBRARY.map(async (entry) => {
      const archive = await getHexagramArchive(entry.slug)
      const sourceSnippet =
        archive?.entries
          .filter((sourceEntry) => sourceEntry.locale.startsWith(locale))
          .slice(0, 5)
          .map((sourceEntry) => sourceEntry.content.replace(/\s+/g, " ").trim())
          .filter(Boolean)
          .join(" ")
          .slice(0, 700) ?? ""
      return {
        slug: entry.slug,
        number: entry.number,
        nameZh: entry.nameZh,
        shortNameZh: entry.shortNameZh,
        pinyin: getHexagramPinyin(entry.slug),
        title: locale === "zh" ? entry.nameZh : entry.titleEn,
        meaning: localizedHexagramMeaning(entry, locale),
        themes: entry.themes,
        localizedThemes: localizedHexagramThemes(entry.themes, locale),
        sourceSnippet,
      }
    }),
  )
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const canonical = `/${locale}/library`
  return {
    title: locale === "zh" ? "查阅六十四卦 · I Ching Studio" : "Explore the 64 Hexagrams · I Ching Studio",
    description:
      locale === "zh"
        ? "按卦名、拼音、处境与主题查阅六十四卦，并阅读卦辞、高岛易断、英文注释与象意。"
        : "Explore the 64 hexagrams by name, pinyin, situation, and theme, with optional classical source layers.",
    alternates: {
      canonical,
      languages: {
        en: "/en/library",
        zh: "/zh/library",
      },
    },
    openGraph: {
      url: `${PUBLIC_SITE_URL}${canonical}`,
    },
  }
}

export default async function LibraryPage({ params }: Props) {
  const resolved = await params
  const locale: Locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const searchDocuments = await buildSearchDocuments(locale)
  const copy =
    locale === "zh"
      ? {
          eyebrow: "六十四卦",
          title: "查阅六十四卦",
          subtitle: "按名称、拼音、常见处境或主题查找一卦。每一页先说明卦意与六爻进程，再按需展开经典来源。",
          deskCta: "另行起卦",
          browse: "依次浏览",
          open: "查看此卦",
        }
      : {
          eyebrow: "The 64 hexagrams",
          title: "Explore the 64 hexagrams",
          subtitle: "Find a hexagram by name, pinyin, common situation, or theme. Each page leads with meaning and progression, with source layers available on demand.",
          deskCta: "Start a separate reading",
          browse: "Browse in order",
          open: "View hexagram",
        }

  return (
    <div className="space-y-8">
      <header className="grid gap-5 border-b border-border/60 pb-8 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="kicker">{copy.eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-muted-foreground">{copy.subtitle}</p>
        </div>
        <Link
          href={withLocale(locale, "/app")}
          className="inline-flex min-h-11 items-center justify-center rounded-md border border-border/70 px-4 text-sm font-semibold text-foreground outline-none transition hover:border-primary/50 hover:text-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          {copy.deskCta}
        </Link>
      </header>

      <LibrarySearch locale={locale} documents={searchDocuments} />

      <section aria-labelledby="hexagram-browse-title">
        <h2 id="hexagram-browse-title" className="text-lg font-semibold text-foreground">{copy.browse}</h2>
        <div className="mt-4 grid gap-x-6 sm:grid-cols-2 xl:grid-cols-4">
          {HEXAGRAM_LIBRARY.map((entry) => {
            const meaning = localizedHexagramMeaning(entry, locale)
            const themes = localizedHexagramThemes(entry.themes, locale)
            return (
              <Link
                key={entry.slug}
                href={withLocale(locale, `/hexagram/${entry.slug}`)}
                className="group min-h-44 border-b border-border/60 py-5 outline-none transition hover:border-primary/60 focus-visible:rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">#{entry.number.toString().padStart(2, "0")}</p>
                    <h3 className="mt-1 text-lg font-semibold text-foreground group-hover:text-primary">{entry.nameZh}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">{getHexagramPinyin(entry.slug)}</p>
                    {locale === "en" && <p className="mt-1 text-sm text-muted-foreground">{entry.titleEn}</p>}
                  </div>
                  <div className="grid w-12 gap-1" aria-hidden="true">
                    {hexagramLines(entry.binary).map((line, index) => (
                      <span
                        key={`${entry.slug}-${index}`}
                        className={line === "1" ? "h-1.5 rounded bg-foreground" : "h-1.5 rounded bg-gradient-to-r from-foreground from-40% via-transparent via-40% to-foreground to-60%"}
                      />
                    ))}
                  </div>
                </div>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">{meaning}</p>
                <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  {themes.map((theme) => <span key={theme}>#{theme}</span>)}
                </div>
                <p className="mt-4 text-xs font-semibold text-primary">{copy.open}</p>
              </Link>
            )
          })}
        </div>
      </section>
    </div>
  )
}
