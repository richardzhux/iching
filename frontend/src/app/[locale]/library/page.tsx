import type { Metadata } from "next"
import Link from "next/link"
import { defaultLocale, isLocale, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { HEXAGRAM_LIBRARY, hexagramLines } from "@/lib/hexagram-library"

type Props = {
  params: Promise<{ locale: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  return {
    title: locale === "zh" ? "易经经典档案 · I Ching Studio" : "Source Library · I Ching Studio",
    description:
      locale === "zh"
        ? "浏览六十四卦、卦名、卦象、主题与来源层。"
        : "Browse the 64 hexagrams as a public source library for serious readings.",
  }
}

export default async function LibraryPage({ params }: Props) {
  const resolved = await params
  const locale: Locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const copy =
    locale === "zh"
      ? {
          eyebrow: "Source Library",
          title: "经典档案",
          subtitle: "六十四卦作为公开阅读索引。先看卦象、主题与来源层，再进入具体解读。",
          deskCta: "回到阅读桌",
          count: "64 卦",
          sourceLayers: "来源层",
          sources: "卦辞 · 高岛 · 英文注释 · 卦象",
          open: "打开卦页",
        }
      : {
          eyebrow: "Source Library",
          title: "Classical Archive",
          subtitle: "A public index of the 64 hexagrams for study before or after a reading.",
          deskCta: "Open Reading Desk",
          count: "64 hexagrams",
          sourceLayers: "Source layers",
          sources: "Judgment · Takashima · English commentary · Symbolic structure",
          open: "Open hexagram",
        }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 border-b border-border/60 pb-8 lg:grid-cols-[1fr_18rem] lg:items-end">
        <div>
          <p className="kicker">{copy.eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-muted-foreground">{copy.subtitle}</p>
        </div>
        <div className="surface-soft rounded-lg p-4">
          <p className="text-sm font-semibold text-foreground">{copy.count}</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {copy.sourceLayers}: {copy.sources}
          </p>
          <Link
            href={withLocale(locale, "/app")}
            className="mt-4 inline-flex rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground"
          >
            {copy.deskCta}
          </Link>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {HEXAGRAM_LIBRARY.map((entry) => (
          <Link
            key={entry.slug}
            href={withLocale(locale, `/hexagram/${entry.slug}`)}
            className="group rounded-lg border border-border/60 bg-surface p-4 transition hover:border-primary/50 hover:bg-surface-elevated"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs text-muted-foreground">#{entry.number.toString().padStart(2, "0")}</p>
                <h2 className="mt-1 text-lg font-semibold text-foreground">{entry.nameZh}</h2>
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
            <p className="mt-3 text-xs font-semibold text-primary">{copy.open}</p>
          </Link>
        ))}
      </section>
    </div>
  )
}
