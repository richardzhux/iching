import type { Locale } from "@/i18n/config"
import { enMessages } from "@/i18n/catalog/en"
import { zhMessages } from "@/i18n/catalog/zh"
import type { Messages } from "@/i18n/messages"

const dictionaryMap: Record<Locale, Messages> = {
  en: enMessages,
  zh: zhMessages,
}

export function getMessages(locale: Locale): Messages {
  return dictionaryMap[locale]
}
