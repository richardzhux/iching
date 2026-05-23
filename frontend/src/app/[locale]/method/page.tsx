import type { Metadata } from "next"
import Link from "next/link"
import { defaultLocale, isLocale, type Locale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"
import { PUBLIC_SITE_URL } from "@/lib/env"

type Props = {
  params: Promise<{ locale: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const canonical = `/${locale}/method`
  return {
    title: locale === "zh" ? "方法与边界 · I Ching Studio" : "Method and Boundaries · I Ching Studio",
    description:
      locale === "zh"
        ? "了解 I Ching Studio 如何起卦、选择动爻、使用来源层、约束 AI 解读并处理阅读记录。"
        : "How I Ching Studio casts, selects moving lines, uses sources, constrains AI, and handles reading records.",
    alternates: {
      canonical,
      languages: {
        en: "/en/method",
        zh: "/zh/method",
      },
    },
    openGraph: {
      url: `${PUBLIC_SITE_URL}${canonical}`,
    },
  }
}

const sections = {
  en: [
    {
      title: "What the reading desk does",
      body: "I Ching Studio keeps the question, cast, primary hexagram, moving lines, changed hexagram, source passages, interpretation, follow-up, and journal state in one reading packet.",
    },
    {
      title: "Casting and moving lines",
      body: "The app supports yarrow-style, coin-style, Meihua time/number, and manual workflows. Manual and guided inputs build six values from bottom to top: 6 old yin, 7 young yang, 8 young yin, and 9 old yang.",
    },
    {
      title: "Source layers",
      body: "The current library uses the received judgment/line text, Takashima commentary, English commentary, and symbolic structure. These are organized by 450 canonical slots and 1,356 imported source entries.",
    },
    {
      title: "AI boundary",
      body: "AI synthesis is allowed to explain, compare, and apply selected evidence. It does not replace the received text, invent missing corpora, or speak as fate-certain authority.",
    },
    {
      title: "Saved data",
      body: "Signed-in cloud history stores reading records and follow-up transcripts for reopening and export. A 365-day cloud retention limit and 500-reading account limit apply.",
    },
    {
      title: "Safety boundary",
      body: "Readings are reflective and educational. They are not medical, legal, financial, emergency, or fate-certain advice.",
    },
  ],
  zh: [
    {
      title: "阅读桌做什么",
      body: "I Ching Studio 把问题、起卦、本卦、动爻、变卦、来源段落、解释、追问与复盘状态保留在同一份阅读包里。",
    },
    {
      title: "起卦与动爻",
      body: "系统支持蓍草式、铜钱式、梅花时间/数字与手动流程。手动和导引输入都按自下而上的六个数值建立卦：6 老阴、7 少阳、8 少阴、9 老阳。",
    },
    {
      title: "来源层",
      body: "当前资料层包括卦辞/爻辞、高岛易断、英文注释与卦象结构；它们按 450 个 canonical slots 与 1,356 条来源资料组织。",
    },
    {
      title: "AI 的边界",
      body: "AI 可以解释、比较与应用已选证据；它不能替代原文，不能假装已有未收录的学派资料，也不能用命定口吻给结论。",
    },
    {
      title: "保存的数据",
      body: "登录用户的云端历史会保存阅读记录与追问文本，用于重开与导出；云端记录最长保留 365 天，每个账户最多 500 条。",
    },
    {
      title: "安全边界",
      body: "阅读用于反思与学习，不构成医疗、法律、金融、紧急事项或命定式建议。",
    },
  ],
} as const satisfies Record<Locale, Array<{ title: string; body: string }>>

export default async function MethodPage({ params }: Props) {
  const resolved = await params
  const locale: Locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const copy =
    locale === "zh"
      ? {
          eyebrow: "Method",
          title: "方法、来源与边界",
          subtitle: "这里说明阅读桌如何从起卦进入证据链，以及 AI 在其中被允许和不允许做什么。",
          cta: "开始一次阅读",
          library: "浏览经典档案",
        }
      : {
          eyebrow: "Method",
          title: "Method, Sources, and Boundaries",
          subtitle: "How the reading desk moves from cast to evidence, and what the AI is allowed to do with that evidence.",
          cta: "Start a reading",
          library: "Browse source library",
        }

  return (
    <article className="mx-auto max-w-5xl space-y-8">
      <header className="border-b border-border/60 pb-8">
        <p className="kicker">{copy.eyebrow}</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
        <p className="mt-4 max-w-3xl text-base leading-7 text-muted-foreground">{copy.subtitle}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href={withLocale(locale, "/app")} className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground">
            {copy.cta}
          </Link>
          <Link href={withLocale(locale, "/library")} className="rounded-md border border-border/60 px-4 py-2 text-sm font-semibold text-foreground">
            {copy.library}
          </Link>
        </div>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        {sections[locale].map((section, index) => (
          <article key={section.title} className="rounded-lg border border-border/60 bg-surface p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-primary">
              {String(index + 1).padStart(2, "0")}
            </p>
            <h2 className="mt-3 text-lg font-semibold text-foreground">{section.title}</h2>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">{section.body}</p>
          </article>
        ))}
      </section>
    </article>
  )
}
