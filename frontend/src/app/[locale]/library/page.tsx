import type { Metadata } from "next"
import Link from "next/link"
import { defaultLocale, isLocale, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { LibrarySearch, type LibrarySearchDocument } from "@/components/library/library-search"
import { PUBLIC_SITE_URL } from "@/lib/env"
import {
  HEXAGRAM_ARCHIVE_SUMMARY,
  getHexagramArchive,
  getHexagramArchiveSummary,
  type HexagramArchiveSourceKey,
} from "@/lib/hexagram-archive"
import { HEXAGRAM_LIBRARY, getHexagramPinyin, hexagramLines } from "@/lib/hexagram-library"

type Props = {
  params: Promise<{ locale: string }>
}

const SOURCE_KEYS = ["guaci", "takashima", "english_commentary", "symbolic"] as const satisfies readonly HexagramArchiveSourceKey[]

const SOURCE_NAMES: Record<HexagramArchiveSourceKey, { zh: string; en: string }> = {
  guaci: { zh: "卦辞库", en: "Judgment" },
  takashima: { zh: "高岛", en: "Takashima" },
  english_commentary: { zh: "英文", en: "English" },
  symbolic: { zh: "象意", en: "Symbolic" },
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value)
}

async function buildSearchDocuments(): Promise<LibrarySearchDocument[]> {
  return Promise.all(
    HEXAGRAM_LIBRARY.map(async (entry) => {
      const archive = await getHexagramArchive(entry.slug)
      const sourceSnippet =
        archive?.entries
          .slice(0, 8)
          .map((sourceEntry) => sourceEntry.content.replace(/\s+/g, " ").trim())
          .filter(Boolean)
          .join(" ")
          .slice(0, 900) ?? ""
      return {
        slug: entry.slug,
        number: entry.number,
        nameZh: entry.nameZh,
        shortNameZh: entry.shortNameZh,
        pinyin: getHexagramPinyin(entry.slug),
        titleEn: entry.titleEn,
        meaningEn: entry.meaningEn,
        themes: entry.themes,
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
    title: locale === "zh" ? "易经经典档案 · I Ching Studio" : "Source Library · I Ching Studio",
    description:
      locale === "zh"
        ? "浏览六十四卦、卦名、卦象、主题与来源层。"
        : "Browse the 64 hexagrams as a public source library for serious readings.",
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
  const searchDocuments = await buildSearchDocuments()
  const copy =
    locale === "zh"
      ? {
          eyebrow: "Source Library",
          title: "经典档案学习库",
          subtitle: "按每一卦整理卦辞、爻辞、高岛易断、英文注释与八卦象意。这里是起卦之外的精确学习入口。",
          deskCta: "回到阅读桌",
          count: "64 卦",
          slotCount: "450 canonical slots",
          entryCount: "1,356 source entries",
          sourceLayers: "来源层",
          sources: "卦辞库 · 高岛易断 · English Commentary · 八卦象意",
          open: "打开卦页",
          completeness: "资料完整度",
          entries: "条资料",
          slots: "槽位",
          studyLibrary: "学习库",
          sourceStats: "来源统计",
          available: "已收录",
        }
      : {
          eyebrow: "Source Library",
          title: "Classical Archive Study Library",
          subtitle: "Every hexagram is organized as a study page: received text, line texts, Takashima, English commentary, and symbolic layers.",
          deskCta: "Open Reading Desk",
          count: "64 hexagrams",
          slotCount: "450 canonical slots",
          entryCount: "1,356 source entries",
          sourceLayers: "Source layers",
          sources: "Judgment · Takashima · English commentary · Symbolic structure",
          open: "Open hexagram",
          completeness: "Archive coverage",
          entries: "entries",
          slots: "slots",
          studyLibrary: "Study library",
          sourceStats: "Source counts",
          available: "available",
        }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 border-b border-border/60 pb-8 lg:grid-cols-[1fr_22rem] lg:items-end">
        <div>
          <p className="kicker">{copy.eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-muted-foreground">{copy.subtitle}</p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold text-foreground">
            <span className="rounded-md border border-border/60 bg-surface px-3 py-1.5">{copy.studyLibrary}</span>
            <span className="rounded-md border border-border/60 bg-surface px-3 py-1.5">{copy.slotCount}</span>
            <span className="rounded-md border border-border/60 bg-surface px-3 py-1.5">{copy.entryCount}</span>
          </div>
        </div>
        <div className="surface-soft rounded-lg p-4">
          <p className="text-sm font-semibold text-foreground">{copy.count}</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {copy.sourceLayers}: {copy.sources}
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <div className="rounded-md border border-border/50 bg-surface px-3 py-2">
              <dt className="text-muted-foreground">{copy.slots}</dt>
              <dd className="mt-1 font-semibold text-foreground">{HEXAGRAM_ARCHIVE_SUMMARY.canonicalSlotCount}</dd>
            </div>
            <div className="rounded-md border border-border/50 bg-surface px-3 py-2">
              <dt className="text-muted-foreground">{copy.entries}</dt>
              <dd className="mt-1 font-semibold text-foreground">{formatNumber(HEXAGRAM_ARCHIVE_SUMMARY.totalEntries)}</dd>
            </div>
          </dl>
          <Link
            href={withLocale(locale, "/app")}
            className="mt-4 inline-flex rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
          >
            {copy.deskCta}
          </Link>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {HEXAGRAM_LIBRARY.map((entry) => {
          const archive = getHexagramArchiveSummary(entry.slug)

          return (
            <Link
              key={entry.slug}
              href={withLocale(locale, `/hexagram/${entry.slug}`)}
              className="group rounded-lg border border-border/60 bg-surface p-4 transition hover:border-primary/50 hover:bg-surface-elevated"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">#{entry.number.toString().padStart(2, "0")}</p>
                  <h2 className="mt-1 text-lg font-semibold text-foreground">{entry.nameZh}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{getHexagramPinyin(entry.slug)}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{entry.titleEn}</p>
                </div>
                <div className="grid w-12 gap-1">
                  {hexagramLines(entry.binary).map((line, index) => (
                    <span
                      key={`${entry.slug}-${index}`}
                      className={line === "1" ? "h-1.5 rounded bg-foreground" : "h-1.5 rounded bg-gradient-to-r from-foreground from-40% via-transparent via-40% to-foreground to-60%"}
                    />
                  ))}
                </div>
              </div>

              <p className="mt-3 text-xs leading-5 text-muted-foreground">{entry.meaningEn}</p>

              {archive ? (
                <div className="mt-4 space-y-3">
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <span className="font-semibold text-foreground">{copy.completeness}</span>
                    <span className="text-muted-foreground">
                      {archive.canonicalSlotCount} {copy.slots} · {archive.totalEntries} {copy.entries}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {SOURCE_KEYS.map((sourceKey) => (
                      <span
                        key={`${entry.slug}-${sourceKey}`}
                        className="rounded-md border border-border/50 bg-surface-elevated px-2 py-1 text-[11px] leading-4 text-muted-foreground"
                      >
                        <span className="text-foreground">{SOURCE_NAMES[sourceKey][locale]}</span>{" "}
                        {archive.sourceCounts[sourceKey]} {copy.available}
                      </span>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-xs text-muted-foreground">{copy.sourceStats}</p>
              )}

              <p className="mt-4 text-xs font-semibold text-primary">{copy.open}</p>
            </Link>
          )
        })}
      </section>

      <LibrarySearch locale={locale} documents={searchDocuments} />

      <section className="rounded-lg border border-border/60 bg-surface p-5">
        <p className="kicker">{copy.sourceStats}</p>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {SOURCE_KEYS.map((sourceKey) => (
            <div key={sourceKey} className="rounded-md border border-border/50 bg-surface-elevated p-3">
              <p className="text-sm font-semibold text-foreground">{SOURCE_NAMES[sourceKey][locale]}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {HEXAGRAM_ARCHIVE_SUMMARY.sourceCounts[sourceKey]} {copy.entries}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
