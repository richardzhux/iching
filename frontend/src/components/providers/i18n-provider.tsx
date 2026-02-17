"use client"

import { createContext, useContext, useEffect, type ReactNode } from "react"
import type { Locale } from "@/i18n/config"
import type { Messages } from "@/i18n/messages"
import { withLocale } from "@/i18n/path"

type I18nContextValue = {
  locale: Locale
  messages: Messages
  toLocalePath: (path?: string) => string
}

const I18nContext = createContext<I18nContextValue | null>(null)

type Props = {
  locale: Locale
  messages: Messages
  children: ReactNode
}

export function I18nProvider({ locale, messages, children }: Props) {
  useEffect(() => {
    if (typeof document === "undefined") return
    document.documentElement.lang = locale === "zh" ? "zh-Hans" : "en"
  }, [locale])

  return (
    <I18nContext.Provider
      value={{
        locale,
        messages,
        toLocalePath: (path = "/") => withLocale(locale, path),
      }}
    >
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const context = useContext(I18nContext)
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider")
  }
  return context
}
