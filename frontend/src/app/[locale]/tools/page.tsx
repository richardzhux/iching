import type { Metadata } from "next"
import { MetaphysicsTools } from "@/components/tools/metaphysics-tools"
import { defaultLocale, isLocale } from "@/i18n/config"

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  return {
    title: locale === "zh" ? "术数工具 · I Ching Studio" : "Metaphysics Tools · I Ching Studio",
    description: locale === "zh" ? "当前时令、八字与紫微斗数排盘工具。" : "Current Chinese calendar, BaZi, and Zi Wei Dou Shu charting tools.",
  }
}

export default function ToolsPage() {
  return <MetaphysicsTools />
}
