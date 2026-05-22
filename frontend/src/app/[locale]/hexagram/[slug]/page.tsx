import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { defaultLocale, isLocale, locales, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { getHexagramBySlug, HEXAGRAM_LIBRARY, hexagramLines } from "@/lib/hexagram-library"

type Props = {
  params: Promise<{ locale: string; slug: string }>
}

export function generateStaticParams() {
  return locales.flatMap((locale) =>
    HEXAGRAM_LIBRARY.map((entry) => ({
      locale,
      slug: entry.slug,
    })),
  )
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const entry = getHexagramBySlug(resolved.slug)
  if (!entry) {
    return {}
  }
  return {
    title:
      locale === "zh"
        ? `${entry.nameZh} · 第 ${entry.number} 卦 · I Ching Studio`
        : `Hexagram ${entry.number}: ${entry.titleEn} · I Ching Studio`,
    description:
      locale === "zh"
        ? `${entry.nameZh}：${entry.titleEn}，${entry.meaningEn}。`
        : `${entry.nameZh}, ${entry.titleEn}: ${entry.meaningEn}.`,
  }
}

export default async function HexagramDetailPage({ params }: Props) {
  const resolved = await params
  const locale: Locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const entry = getHexagramBySlug(resolved.slug)

  if (!entry) {
    notFound()
  }

  const copy =
    locale === "zh"
      ? {
          eyebrow: "Hexagram Source Page",
          back: "返回经典档案",
          desk: "用此卦起一条阅读",
          number: "第",
          gua: "卦",
          structure: "卦象结构",
          upper: "上卦",
          lower: "下卦",
          sourceLayers: "来源层",
          sourceBody: "正式阅读会把卦辞、动爻、高岛、英文注释、卦象结构和 AI 综合分层呈现，并保留可跳转来源。",
          themes: "主题索引",
          noteTitle: "阅读原则",
          noteBody: "此页是公开档案入口，不替代完整起卦。完整阅读仍以问题、起卦时间、动爻和来源证据为准。",
        }
      : {
          eyebrow: "Hexagram Source Page",
          back: "Back to Source Library",
          desk: "Cast with this context",
          number: "Hexagram",
          gua: "",
          structure: "Structure",
          upper: "Upper trigram",
          lower: "Lower trigram",
          sourceLayers: "Source layers",
          sourceBody: "A full reading separates the received text, moving-line evidence, Takashima, English commentary, symbolic structure, and AI synthesis with jumpable source ids.",
          themes: "Theme index",
          noteTitle: "Reading principle",
          noteBody: "This public page is a study entry, not a complete divination. A reading still depends on the question, casting time, moving lines, and source evidence.",
        }

  return (
    <article className="mx-auto max-w-5xl space-y-8">
      <nav className="flex flex-wrap gap-3 text-sm">
        <Link href={withLocale(locale, "/library")} className="text-primary underline-offset-4 hover:underline">
          {copy.back}
        </Link>
        <Link href={withLocale(locale, "/app")} className="text-primary underline-offset-4 hover:underline">
          {copy.desk}
        </Link>
      </nav>

      <header className="grid gap-6 rounded-lg border border-border/60 bg-surface p-6 lg:grid-cols-[1fr_13rem]">
        <div>
          <p className="kicker">{copy.eyebrow}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">
            {copy.number} {entry.number} {copy.gua} · {entry.nameZh}
          </h1>
          <p className="mt-3 text-xl text-muted-foreground">{entry.titleEn}</p>
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

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-border/60 bg-surface p-4">
          <p className="kicker">{copy.structure}</p>
          <p className="mt-3 text-sm text-muted-foreground">{copy.upper}</p>
          <p className="text-lg font-semibold text-foreground">{entry.upper}</p>
          <p className="mt-3 text-sm text-muted-foreground">{copy.lower}</p>
          <p className="text-lg font-semibold text-foreground">{entry.lower}</p>
        </div>
        <div className="rounded-lg border border-border/60 bg-surface p-4 md:col-span-2">
          <p className="kicker">{copy.sourceLayers}</p>
          <p className="mt-3 text-sm leading-6 text-foreground">{copy.sourceBody}</p>
        </div>
      </section>

      <section className="rounded-lg border border-border/60 bg-surface p-5">
        <p className="kicker">{copy.themes}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {entry.themes.map((theme) => (
            <span key={theme} className="rounded-md border border-border/60 bg-surface-elevated px-3 py-1 text-sm text-foreground">
              {theme}
            </span>
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
