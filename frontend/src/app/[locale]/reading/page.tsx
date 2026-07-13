import type { Metadata } from "next"
import { ReadingWorkspace } from "@/components/workspace/reading-workspace"
import { defaultLocale, isLocale } from "@/i18n/config"

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  return {
    title: locale === "zh" ? "解卦 · I Ching Studio" : "Reading · I Ching Studio",
    description: locale === "zh" ? "查看当前卦盘、经典依据并继续 AI 追问。" : "Review the active chart, classical evidence, and continue with AI follow-up.",
  }
}

export default function ReadingPage() {
  return <ReadingWorkspace />
}
