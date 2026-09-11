import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { HexagramGlyph } from "@/components/hexagram/hexagram-glyph"
import { ClassicalReader } from "@/components/hexagram/classical-reader"
import { chapterTitle, type ClassicalChapter } from "@/lib/classical-text"
import { defaultLocale, isLocale, locales, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { PUBLIC_SITE_URL } from "@/lib/env"
import { getHexagramArchive } from "@/lib/hexagram-archive"
import { localizedHexagramMeaning, localizedTrigram } from "@/lib/hexagram-copy"
import { getHexagramBySlug, getHexagramPinyin, HEXAGRAM_LIBRARY, hexagramLines } from "@/lib/hexagram-library"

type Props = { params: Promise<{ locale: string; slug: string }> }

export function generateStaticParams() {
  return locales.flatMap((locale) => HEXAGRAM_LIBRARY.map((entry) => ({ locale, slug: entry.slug })))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const entry = getHexagramBySlug(resolved.slug)
  if (!entry) return {}
  const canonical = `/${locale}/hexagram/${entry.slug}`
  const pinyin = getHexagramPinyin(entry.slug)
  return {
    title: locale === "zh" ? `${entry.nameZh} ${pinyin} · 第 ${entry.number} 卦 · I Ching Studio` : `Hexagram ${entry.number}: ${entry.shortNameZh} ${pinyin} — ${entry.titleEn} · I Ching Studio`,
    description: localizedHexagramMeaning(entry, locale),
    alternates: {
      canonical,
      languages: { en: `/en/hexagram/${entry.slug}`, zh: `/zh/hexagram/${entry.slug}` },
    },
    openGraph: { url: `${PUBLIC_SITE_URL}${canonical}` },
  }
}

export default async function HexagramDetailPage({ params }: Props) {
  const resolved = await params
  const locale: Locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const entry = getHexagramBySlug(resolved.slug)
  const archive = await getHexagramArchive(resolved.slug)
  if (!entry || !archive) notFound()
  const chapters = new Map<string, ClassicalChapter>()
  for (const source of archive.entries) {
    const chapter = chapters.get(source.slotKey) ?? {
      key: source.slotKey,
      title: chapterTitle(source.lineNo, source.useKind, locale),
      lineNo: source.lineNo,
      sources: [],
    }
    chapter.sources.push({ key: source.sourceKey, label: source.sourceLabel, content: source.content })
    chapters.set(source.slotKey, chapter)
  }
  const previous = HEXAGRAM_LIBRARY.find((hexagram) => hexagram.number === entry.number - 1)
  const next = HEXAGRAM_LIBRARY.find((hexagram) => hexagram.number === entry.number + 1)
  return <article className="autumn-study autumn-archive classical-archive mx-auto max-w-[90rem]">
    <nav className="classical-library-navigation" aria-label={locale === "zh" ? "六十四卦导航" : "Hexagram library navigation"}>
      <Link href={withLocale(locale, "/library")}>← {locale === "zh" ? "六十四卦" : "64 hexagrams"}</Link>
      <div>
        {previous ? <Link href={withLocale(locale, `/hexagram/${previous.slug}`)}>← {previous.number} · {previous.shortNameZh}</Link> : null}
        {next ? <Link href={withLocale(locale, `/hexagram/${next.slug}`)}>{next.number} · {next.shortNameZh} →</Link> : null}
      </div>
    </nav>
    <header className="classical-archive-header">
      <div>
        <p className="kicker">{locale === "zh" ? "周易 · 经传与注解" : "I Ching · Texts & commentaries"}</p>
        <h1 className="autumn-page-title">{entry.number.toString().padStart(2, "0")} · {entry.nameZh}</h1>
        <p className="classical-archive-subtitle">{getHexagramPinyin(entry.slug)} · {entry.titleEn}</p>
        <p className="classical-trigram-caption">{locale === "zh" ? "上卦" : "Upper"} {localizedTrigram(entry.upper, locale)}<span>／</span>{locale === "zh" ? "下卦" : "Lower"} {localizedTrigram(entry.lower, locale)}</p>
      </div>
      <HexagramGlyph lines={hexagramLines(entry.binary)} className="w-28 gap-3" lineClassName="h-2" />
    </header>
    <ClassicalReader chapters={[...chapters.values()]} locale={locale} heading={entry.nameZh} />
  </article>
}
