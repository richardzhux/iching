import { redirect } from "next/navigation"
import { defaultLocale, isLocale } from "@/i18n/config"
import { withLocale } from "@/i18n/path"

export default async function LegacyMethodPage({ params }: { params: Promise<{ locale: string }> }) {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  redirect(withLocale(locale, "/tools"))
}
