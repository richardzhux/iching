import { CastWorkspace } from "@/components/workspace/cast-workspace"
import type { Metadata } from "next"
import { defaultLocale, isLocale } from "@/i18n/config"
import { getMessages } from "@/i18n/get-messages"

type Props = {
  params: Promise<{ locale: string }>
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const messages = getMessages(locale)
  return {
    title: messages.meta.workspaceTitle,
    description: messages.meta.workspaceDescription,
  }
}

export default function WorkspacePage() {
  return <CastWorkspace />
}
