import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { HexagramGlyph } from "@/components/hexagram/hexagram-glyph"
import { HexagramQuickNav } from "@/components/hexagram/hexagram-quick-nav"
import { defaultLocale, isLocale, locales, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { PUBLIC_SITE_URL } from "@/lib/env"
import { getHexagramArchive, type HexagramArchiveEntry, type HexagramArchiveSourceKey } from "@/lib/hexagram-archive"
import { localizedHexagramMeaning, localizedHexagramThemes, localizedTrigram } from "@/lib/hexagram-copy"
import { getHexagramBySlug, getHexagramPinyin, HEXAGRAM_LIBRARY, hexagramLines } from "@/lib/hexagram-library"

type Props = {
  params: Promise<{ locale: string; slug: string }>
}

type ArchiveSlot = {
  slotKey: string
  slotKind: HexagramArchiveEntry["slotKind"]
  lineNo: number | null
  useKind: string | null
  entries: readonly HexagramArchiveEntry[]
}

const SOURCE_KEYS = ["guaci", "takashima", "english_commentary", "symbolic"] as const satisfies readonly HexagramArchiveSourceKey[]

const SOURCE_NAMES: Record<HexagramArchiveSourceKey, { zh: string; en: string }> = {
  guaci: { zh: "卦爻原文", en: "Received text" },
  takashima: { zh: "高岛易断", en: "Takashima" },
  english_commentary: { zh: "英文注释（可选）", en: "English commentary" },
  symbolic: { zh: "八卦象意", en: "Symbolic layer" },
}

const LINE_LABELS_ZH: Record<number, string> = {
  1: "初爻",
  2: "二爻",
  3: "三爻",
  4: "四爻",
  5: "五爻",
  6: "上爻",
}

export function generateStaticParams() {
  return locales.flatMap((locale) => HEXAGRAM_LIBRARY.map((entry) => ({ locale, slug: entry.slug })))
}

function groupArchiveEntriesBySlot(entries: readonly HexagramArchiveEntry[]): ArchiveSlot[] {
  const grouped = new Map<string, ArchiveSlot>()
  for (const sourceEntry of entries) {
    const existing = grouped.get(sourceEntry.slotKey)
    if (existing) {
      existing.entries = [...existing.entries, sourceEntry]
      continue
    }
    grouped.set(sourceEntry.slotKey, {
      slotKey: sourceEntry.slotKey,
      slotKind: sourceEntry.slotKind,
      lineNo: sourceEntry.lineNo,
      useKind: sourceEntry.useKind,
      entries: [sourceEntry],
    })
  }
  return [...grouped.values()]
}

function slotTitle(slot: ArchiveSlot, locale: Locale) {
  if (slot.slotKind === "gua") return locale === "zh" ? "本卦卦辞" : "Whole hexagram"
  if (slot.slotKind === "use") return locale === "zh" ? "用九 / 用六" : "Yong Jiu / Yong Liu"
  if (slot.lineNo) return locale === "zh" ? LINE_LABELS_ZH[slot.lineNo] ?? `第 ${slot.lineNo} 爻` : `Line ${slot.lineNo}`
  return locale === "zh" ? "爻位资料" : "Line material"
}

function slotSubtitle(slot: ArchiveSlot, locale: Locale) {
  if (slot.slotKind === "gua") return locale === "zh" ? "先读全卦主旨，再按需核对不同来源。" : "Start with the whole-hexagram meaning, then compare sources as needed."
  if (slot.slotKind === "use") return locale === "zh" ? "乾坤全动时采用的特殊断法。" : "The special rule for Qian or Kun when all lines move."
  return locale === "zh" ? "沿着这一爻查看原文、象意与解释。" : "Follow this line through its text, image, and commentary."
}

function sourcePreview(slot: ArchiveSlot) {
  const preferred = slot.entries.find((entry) => entry.sourceKey === "guaci") ?? slot.entries[0]
  return preferred?.content.replace(/\s+/g, " ").trim().slice(0, 150) ?? ""
}

function SourceEntryCard({ entry, locale }: { entry: HexagramArchiveEntry; locale: Locale }) {
  const sourceName = SOURCE_NAMES[entry.sourceKey][locale]
  return (
    <article className="border-t border-border/60 py-5 first:border-t-0 first:pt-0">
      <div>
        <p className="text-sm font-semibold text-foreground">{sourceName}</p>
        <p className="mt-1 text-xs text-muted-foreground">{entry.sourceLabel}</p>
      </div>
      <pre
        tabIndex={0}
        aria-label={`${sourceName} · ${entry.sourceLabel}`}
        className="custom-scrollbar mt-4 max-h-[28rem] overflow-y-auto whitespace-pre-wrap rounded-md bg-surface-elevated/70 p-4 font-sans text-sm leading-7 text-foreground/90 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        {entry.content}
      </pre>
    </article>
  )
}

function ArchiveSlotSection({ slot, locale }: { slot: ArchiveSlot; locale: Locale }) {
  const orderedEntries = [...slot.entries].sort((a, b) => SOURCE_KEYS.indexOf(a.sourceKey) - SOURCE_KEYS.indexOf(b.sourceKey))
  return (
    <details className="group border-b border-border/60">
      <summary className="cursor-pointer list-none rounded-md px-1 py-5 outline-none marker:hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-foreground">{slotTitle(slot, locale)}</h3>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{slotSubtitle(slot, locale)}</p>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-foreground/80">{sourcePreview(slot)}</p>
          </div>
          <span className="min-h-11 shrink-0 py-3 text-sm font-semibold text-primary group-open:hidden">{locale === "zh" ? "展开" : "Open"}</span>
          <span className="hidden min-h-11 shrink-0 py-3 text-sm font-semibold text-primary group-open:block">{locale === "zh" ? "收起" : "Close"}</span>
        </div>
      </summary>
      <div className="pb-5 pl-0 lg:pl-5">
        {orderedEntries.map((sourceEntry, index) => (
          <SourceEntryCard key={`${sourceEntry.sourceKey}-${sourceEntry.locale}-${index}`} entry={sourceEntry} locale={locale} />
        ))}
      </div>
    </details>
  )
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

  const archiveSlots = groupArchiveEntriesBySlot(archive.entries)
  const sixLineProgression = archiveSlots.filter((slot) => slot.slotKind === "line").sort((a, b) => (a.lineNo ?? 0) - (b.lineNo ?? 0))
  const pinyin = getHexagramPinyin(entry.slug)
  const meaning = localizedHexagramMeaning(entry, locale)
  const themes = localizedHexagramThemes(entry.themes, locale)
  const copy = locale === "zh"
    ? {
        eyebrow: "卦意与六爻",
        back: "返回六十四卦",
        desk: "另行起卦",
        number: "第",
        gua: "卦",
        structure: "卦象结构",
        upper: "上卦",
        lower: "下卦",
        situations: "常见处境",
        progression: "六爻进程",
        progressionBody: "六爻从初爻向上推进，呈现局势由起点到完成或转折的过程。",
        sources: "按需查看经典来源",
        sourcesBody: "每一段先给出简短预览；展开后可查看完整卦爻原文、高岛易断、英文注释与象意。",
        noteTitle: "阅读原则",
        noteBody: "查卦用于理解卦意，不代表已经为当前问题起卦。正式判断仍需结合问题、起卦时间、动爻与变卦。",
      }
    : {
        eyebrow: "Meaning and progression",
        back: "Back to the 64 hexagrams",
        desk: "Start a separate reading",
        number: "Hexagram",
        gua: "",
        structure: "Structure",
        upper: "Upper trigram",
        lower: "Lower trigram",
        situations: "Common situations",
        progression: "Six-line progression",
        progressionBody: "The six lines move upward from the opening condition toward completion, consequence, or transition.",
        sources: "Open classical sources as needed",
        sourcesBody: "Each section starts with a concise preview. Expand it for the complete received text, Takashima, English commentary, and symbolic material.",
        noteTitle: "Reading principle",
        noteBody: "Studying a hexagram does not mean it has been cast for your situation. A full reading still depends on the question, casting time, moving lines, and changed hexagram.",
      }

  return (
    <div className="mx-auto grid max-w-[90rem] items-start gap-7 lg:grid-cols-[11rem_minmax(0,1fr)]">
      <HexagramQuickNav locale={locale} mode="routes" activeSlug={entry.slug} />
      <article className="min-w-0 space-y-8">
      <nav className="flex flex-wrap gap-4 text-sm">
        <Link href={withLocale(locale, "/library")} className="min-h-11 rounded-md py-3 text-primary outline-none underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring">{copy.back}</Link>
        <Link href={withLocale(locale, "/app")} className="min-h-11 rounded-md py-3 text-primary outline-none underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring">{copy.desk}</Link>
      </nav>

      <header className="grid gap-7 border-b border-border/60 pb-8 lg:grid-cols-[1fr_14rem]">
        <div>
          <p className="kicker">{copy.eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">{copy.number} {entry.number} {copy.gua} · {entry.nameZh}</h1>
          <p className="mt-3 text-xl text-muted-foreground">{pinyin}{locale === "en" ? ` · ${entry.titleEn}` : ""}</p>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-foreground">{meaning}</p>
          <div className="mt-4 flex flex-wrap gap-2" aria-label={copy.situations}>
            {themes.map((theme) => <span key={theme} className="rounded-full bg-primary/10 px-3 py-1.5 text-sm text-primary">{theme}</span>)}
          </div>
        </div>
        <div className="grid place-items-center rounded-lg bg-surface-elevated p-5">
          <HexagramGlyph lines={hexagramLines(entry.binary)} className="w-28 gap-3" lineClassName="h-2" />
        </div>
      </header>

      <section className="grid gap-6 border-b border-border/60 pb-8 md:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold text-foreground">{copy.structure}</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4">
            <div><dt className="text-sm text-muted-foreground">{copy.upper}</dt><dd className="mt-1 text-lg font-semibold text-foreground">{localizedTrigram(entry.upper, locale)}</dd></div>
            <div><dt className="text-sm text-muted-foreground">{copy.lower}</dt><dd className="mt-1 text-lg font-semibold text-foreground">{localizedTrigram(entry.lower, locale)}</dd></div>
          </dl>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-foreground">{copy.situations}</h2>
          <p className="mt-4 text-sm leading-7 text-muted-foreground">{themes.join(locale === "zh" ? "、" : " · ")}</p>
        </div>
      </section>

      <section className="border-b border-border/60 pb-8">
        <h2 className="text-xl font-semibold text-foreground">{copy.progression}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{copy.progressionBody}</p>
        <ol className="mt-5 grid gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {sixLineProgression.map((slot) => (
            <li key={slot.slotKey}>
              <a href={`#${slot.slotKey.replaceAll(".", "-")}`} className="flex min-h-11 items-center justify-between rounded-md border-b border-border/60 px-2 py-3 text-sm font-semibold text-foreground outline-none transition hover:border-primary hover:text-primary focus-visible:ring-2 focus-visible:ring-ring">
                <span>{slotTitle(slot, locale)}</span><span aria-hidden="true">↓</span>
              </a>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="sources-heading">
        <h2 id="sources-heading" className="text-xl font-semibold text-foreground">{copy.sources}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{copy.sourcesBody}</p>
        <div className="mt-5">
          {archiveSlots.map((slot) => (
            <section key={slot.slotKey} id={slot.slotKey.replaceAll(".", "-")} className="scroll-mt-[9rem] md:scroll-mt-24">
              <ArchiveSlotSection slot={slot} locale={locale} />
            </section>
          ))}
        </div>
      </section>

      <section className="border-l-2 border-primary/50 pl-5">
        <h2 className="text-base font-semibold text-foreground">{copy.noteTitle}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.noteBody}</p>
      </section>
      </article>
    </div>
  )
}
