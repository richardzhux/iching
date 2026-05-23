import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { defaultLocale, isLocale, locales, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { PUBLIC_SITE_URL } from "@/lib/env"
import {
  getHexagramArchive,
  type HexagramArchiveEntry,
  type HexagramArchiveSourceKey,
} from "@/lib/hexagram-archive"
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
  english_commentary: { zh: "英文注释", en: "English commentary" },
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
  return locales.flatMap((locale) =>
    HEXAGRAM_LIBRARY.map((entry) => ({
      locale,
      slug: entry.slug,
    })),
  )
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value)
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
  return Array.from(grouped.values())
}

function slotTitle(slot: ArchiveSlot, locale: Locale) {
  if (slot.slotKind === "gua") {
    return locale === "zh" ? "本卦卦辞" : "Judgment and image"
  }
  if (slot.slotKind === "use") {
    return locale === "zh" ? "用九 / 用六" : "Yong Jiu / Yong Liu"
  }
  if (slot.lineNo) {
    return locale === "zh" ? LINE_LABELS_ZH[slot.lineNo] ?? `第 ${slot.lineNo} 爻` : `Line ${slot.lineNo}`
  }
  return locale === "zh" ? "爻位资料" : "Line material"
}

function slotSubtitle(slot: ArchiveSlot, locale: Locale) {
  if (slot.slotKind === "gua") {
    return locale === "zh" ? "卦辞解析、象传、总论与本卦资料。" : "Received text, image, overview, and whole-hexagram commentary."
  }
  if (slot.slotKind === "use") {
    return locale === "zh" ? "乾坤全动时采用的特殊断法。" : "The special rule used when Qian or Kun has all moving lines."
  }
  return locale === "zh" ? "爻位资料：爻辞、象传、解释与来源对照。" : "Line material: line text, image, interpretation, and source comparison."
}

function SourceEntryCard({ entry, locale }: { entry: HexagramArchiveEntry; locale: Locale }) {
  return (
    <article className="rounded-lg border border-border/60 bg-surface-elevated p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-foreground">{SOURCE_NAMES[entry.sourceKey][locale]}</p>
          <p className="mt-1 text-xs text-muted-foreground">{entry.sourceLabel}</p>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
          <span className="rounded-md border border-border/60 px-2 py-1">{entry.locale}</span>
          <span className="rounded-md border border-border/60 px-2 py-1">{entry.slotKey}</span>
        </div>
      </div>
      <pre className="mt-4 max-h-[28rem] overflow-y-auto whitespace-pre-wrap font-sans text-sm leading-7 text-foreground/90">
        {entry.content}
      </pre>
    </article>
  )
}

function ArchiveSlotSection({ slot, locale }: { slot: ArchiveSlot; locale: Locale }) {
  const sourceSummary = SOURCE_KEYS.map((sourceKey) => {
    const count = slot.entries.filter((entry) => entry.sourceKey === sourceKey).length
    return count > 0 ? `${SOURCE_NAMES[sourceKey][locale]} ${count}` : null
  }).filter(Boolean)

  return (
    <details open={slot.slotKind === "gua"} className="group rounded-lg border border-border/60 bg-surface">
      <summary className="cursor-pointer list-none p-5 marker:hidden">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-foreground">{slotTitle(slot, locale)}</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">{slotSubtitle(slot, locale)}</p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <p>{locale === "zh" ? `${slot.entries.length} 条来源` : `${slot.entries.length} sources`}</p>
            <p className="mt-1 text-primary group-open:hidden">{locale === "zh" ? "展开" : "Open"}</p>
            <p className="mt-1 text-primary hidden group-open:block">{locale === "zh" ? "收起" : "Close"}</p>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {sourceSummary.map((label) => (
            <span key={label} className="rounded-md border border-border/60 bg-surface-elevated px-2 py-1 text-[11px] text-muted-foreground">
              {label}
            </span>
          ))}
        </div>
      </summary>
      <div className="grid gap-3 border-t border-border/60 p-4 xl:grid-cols-2">
        {slot.entries.map((sourceEntry) => (
          <SourceEntryCard key={`${sourceEntry.slotKey}-${sourceEntry.sourceKey}-${sourceEntry.locale}`} entry={sourceEntry} locale={locale} />
        ))}
      </div>
    </details>
  )
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const entry = getHexagramBySlug(resolved.slug)
  if (!entry) {
    return {}
  }
  const canonical = `/${locale}/hexagram/${entry.slug}`
  const pinyin = getHexagramPinyin(entry.slug)
  return {
    title:
      locale === "zh"
        ? `${entry.nameZh} ${pinyin} · 第 ${entry.number} 卦 · I Ching Studio`
        : `Hexagram ${entry.number}: ${entry.shortNameZh} ${pinyin} — ${entry.titleEn} · I Ching Studio`,
    description:
      locale === "zh"
        ? `${entry.nameZh} ${pinyin}：${entry.titleEn}，${entry.meaningEn}。`
        : `Study Hexagram ${entry.number} ${entry.shortNameZh} ${pinyin}: ${entry.titleEn}, ${entry.meaningEn}.`,
    alternates: {
      canonical,
      languages: {
        en: `/en/hexagram/${entry.slug}`,
        zh: `/zh/hexagram/${entry.slug}`,
      },
    },
    openGraph: {
      url: `${PUBLIC_SITE_URL}${canonical}`,
    },
  }
}

export default async function HexagramDetailPage({ params }: Props) {
  const resolved = await params
  const locale: Locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const entry = getHexagramBySlug(resolved.slug)
  const archive = await getHexagramArchive(resolved.slug)

  if (!entry || !archive) {
    notFound()
  }

  const archiveSlots = groupArchiveEntriesBySlot(archive.entries)
  const pinyin = getHexagramPinyin(entry.slug)
  const copy =
    locale === "zh"
      ? {
          eyebrow: "Hexagram Study Page",
          back: "返回经典档案",
          desk: "用此卦起一条阅读",
          number: "第",
          gua: "卦",
          structure: "卦象结构",
          upper: "上卦",
          lower: "下卦",
          sourceLayers: "来源层",
          sourceBody: "此页按槽位整理现有资料：本卦卦辞、六爻、用九/用六，并把卦辞库、高岛易断、英文注释与象意分层展示。",
          themes: "主题索引",
          studyTable: "学习目录",
          sourceCounts: "来源统计",
          entries: "条资料",
          slots: "槽位",
          noteTitle: "阅读原则",
          noteBody: "此页是学习库，不替代完整起卦。正式阅读仍以问题、起卦时间、动爻、变卦与来源证据共同判断。",
        }
      : {
          eyebrow: "Hexagram Study Page",
          back: "Back to Source Library",
          desk: "Cast with this context",
          number: "Hexagram",
          gua: "",
          structure: "Structure",
          upper: "Upper trigram",
          lower: "Lower trigram",
          sourceLayers: "Source layers",
          sourceBody: "This page organizes the existing corpus by canonical slot: judgment, six lines, special Qian/Kun use rules, and source layers.",
          themes: "Theme index",
          studyTable: "Study table",
          sourceCounts: "Source counts",
          entries: "entries",
          slots: "slots",
          noteTitle: "Reading principle",
          noteBody: "This is a study library page, not a complete divination. A full reading still depends on the question, casting time, moving lines, changed hexagram, and evidence chain.",
        }

  return (
    <article className="mx-auto max-w-7xl space-y-8">
      <nav className="flex flex-wrap gap-3 text-sm">
        <Link href={withLocale(locale, "/library")} className="text-primary underline-offset-4 hover:underline">
          {copy.back}
        </Link>
        <Link href={withLocale(locale, "/app")} className="text-primary underline-offset-4 hover:underline">
          {copy.desk}
        </Link>
      </nav>

      <header className="grid gap-6 rounded-lg border border-border/60 bg-surface p-6 lg:grid-cols-[1fr_15rem]">
        <div>
          <p className="kicker">{copy.eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">
            {copy.number} {entry.number} {copy.gua} · {entry.nameZh}
          </h1>
          <p className="mt-3 text-xl text-muted-foreground">{pinyin} · {entry.titleEn}</p>
          <p className="mt-4 max-w-2xl text-base leading-7 text-foreground">{entry.meaningEn}</p>
        </div>
        <div className="grid place-items-center rounded-lg border border-border/60 bg-surface-elevated p-5">
          <div className="grid w-28 gap-3">
            {hexagramLines(entry.binary).map((line, index) => (
              <span
                key={`${entry.slug}-line-${index}`}
                className={line === "1" ? "h-2 rounded bg-foreground" : "h-2 rounded bg-gradient-to-r from-foreground from-40% via-transparent via-40% to-foreground to-60%"}
              />
            ))}
          </div>
        </div>
      </header>

      <section className="grid gap-4 lg:grid-cols-4">
        <div className="rounded-lg border border-border/60 bg-surface p-4">
          <p className="kicker">{copy.structure}</p>
          <p className="mt-3 text-sm text-muted-foreground">{copy.upper}</p>
          <p className="text-lg font-semibold text-foreground">{entry.upper}</p>
          <p className="mt-3 text-sm text-muted-foreground">{copy.lower}</p>
          <p className="text-lg font-semibold text-foreground">{entry.lower}</p>
        </div>
        <div className="rounded-lg border border-border/60 bg-surface p-4 lg:col-span-2">
          <p className="kicker">{copy.sourceLayers}</p>
          <p className="mt-3 text-sm leading-6 text-foreground">{copy.sourceBody}</p>
        </div>
        <div className="rounded-lg border border-border/60 bg-surface p-4">
          <p className="kicker">{copy.sourceCounts}</p>
          <p className="mt-3 text-2xl font-semibold text-foreground">{archive.totalEntries}</p>
          <p className="text-xs text-muted-foreground">
            {archive.canonicalSlotCount} {copy.slots}
          </p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
          <div className="rounded-lg border border-border/60 bg-surface p-4">
            <p className="kicker">{copy.studyTable}</p>
            <div className="mt-4 space-y-2">
              {archiveSlots.map((slot) => (
                <a
                  key={slot.slotKey}
                  href={`#${slot.slotKey.replaceAll(".", "-")}`}
                  className="block rounded-md border border-border/50 bg-surface-elevated px-3 py-2 text-xs text-muted-foreground transition hover:border-primary/50 hover:text-foreground"
                >
                  <span className="font-semibold text-foreground">{slotTitle(slot, locale)}</span>
                  <span className="mt-1 block">
                    {slot.entries.length} {copy.entries}
                  </span>
                </a>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-surface p-4">
            <p className="kicker">{copy.themes}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {entry.themes.map((theme) => (
                <span key={theme} className="rounded-md border border-border/60 bg-surface-elevated px-3 py-1 text-xs text-foreground">
                  {theme}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-surface p-4">
            <p className="kicker">{copy.sourceCounts}</p>
            <div className="mt-3 space-y-2">
              {SOURCE_KEYS.map((sourceKey) => (
                <div key={sourceKey} className="flex items-center justify-between gap-3 text-xs">
                  <span className="text-muted-foreground">{SOURCE_NAMES[sourceKey][locale]}</span>
                  <span className="font-semibold text-foreground">{formatNumber(archive.sourceCounts[sourceKey])}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <div className="space-y-4">
          {archiveSlots.map((slot) => (
            <section key={slot.slotKey} id={slot.slotKey.replaceAll(".", "-")} className="scroll-mt-6">
              <ArchiveSlotSection slot={slot} locale={locale} />
            </section>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-primary/30 bg-primary/10 p-5">
        <h2 className="text-base font-semibold text-foreground">{copy.noteTitle}</h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.noteBody}</p>
      </section>
    </article>
  )
}
