import type { Metadata } from "next"
import Link from "next/link"
import Image from "next/image"
import { notFound } from "next/navigation"
import { Suspense } from "react"
import { I18nProvider } from "@/components/providers/i18n-provider"
import { AutumnMotionProvider } from "@/components/autumn/autumn-motion"
import { PrimaryNavigation } from "@/components/navigation/primary-navigation"
import { ProfileMenu } from "@/components/profile/profile-menu"
import { LanguageToggle } from "@/components/theme/language-toggle"
import { ThemeToggle } from "@/components/theme/theme-toggle"
import { defaultLocale, isLocale, locales, type Locale } from "@/i18n/config"
import { getMessages } from "@/i18n/get-messages"
import { withLocale } from "@/i18n/path"
import { PUBLIC_SITE_URL } from "@/lib/env"
import { cn } from "@/lib/utils"

type Props = {
  children: React.ReactNode
  params: Promise<{ locale: string }>
}

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const resolved = await params
  const locale = isLocale(resolved.locale) ? resolved.locale : defaultLocale
  const messages = getMessages(locale)
  return {
    title: messages.meta.appTitle,
    description: messages.meta.appDescription,
    alternates: {
      canonical: `/${locale}`,
      languages: {
        en: "/en",
        zh: "/zh",
      },
    },
    openGraph: {
      url: `${PUBLIC_SITE_URL}/${locale}`,
    },
  }
}

export default async function LocaleLayout({ children, params }: Props) {
  const resolved = await params
  if (!isLocale(resolved.locale)) {
    notFound()
  }
  const locale: Locale = resolved.locale
  const messages = getMessages(locale)

  return (
    <I18nProvider locale={locale} messages={messages}>
      <AutumnMotionProvider>
      <div className={cn("app-shell relative min-h-screen", locale === "en" ? "locale-en" : "locale-zh")}>
        <a href="#main-content" className="autumn-skip-link">{locale === "zh" ? "跳至正文" : "Skip to content"}</a>
        <div className="pointer-events-none absolute inset-0 app-overlay" />
        <header className="shell-header sticky top-0 z-30 border-b border-border/50">
          <div className="autumn-header-inner mx-auto flex h-[72px] w-full items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
            <div className="flex items-center gap-3">
              <Link href={withLocale(locale, "/")} className="autumn-brand text-foreground">
                <Image src="/autumn/ginkgo-leaf.webp" alt="" width={28} height={28} />
                {messages.nav.brand}
              </Link>
              <Suspense fallback={null}><PrimaryNavigation className="hidden md:flex" /></Suspense>
            </div>
            <div className="flex items-center gap-2">
              <Suspense fallback={null}>
                <LanguageToggle />
              </Suspense>
              <ThemeToggle />
              <ProfileMenu />
            </div>
          </div>
          <div className="mx-auto w-full max-w-7xl border-t border-border/40 md:hidden">
            <Suspense fallback={null}><PrimaryNavigation mobile /></Suspense>
          </div>
        </header>
        <main id="main-content" lang={locale} className="autumn-main relative z-10 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
          {children}
        </main>
      </div>
      </AutumnMotionProvider>
    </I18nProvider>
  )
}
