import type { Metadata } from "next"
import Link from "next/link"
import { notFound } from "next/navigation"
import { Suspense } from "react"
import { I18nProvider } from "@/components/providers/i18n-provider"
import { ProfileMenu } from "@/components/profile/profile-menu"
import { LanguageToggle } from "@/components/theme/language-toggle"
import { ThemeToggle } from "@/components/theme/theme-toggle"
import { buttonVariants } from "@/components/ui/button"
import { defaultLocale, isLocale, locales, type Locale } from "@/i18n/config"
import { getMessages } from "@/i18n/get-messages"
import { withLocale } from "@/i18n/path"
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
      <div className={cn("app-shell relative min-h-screen", locale === "en" ? "locale-en" : "locale-zh")}>
        <div className="pointer-events-none absolute inset-0 app-overlay" />
        <header className="shell-header sticky top-0 z-30 border-b border-border/50">
          <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
            <div className="flex items-center gap-3">
              <Link href={withLocale(locale, "/")} className="text-sm font-semibold tracking-wide text-foreground">
                {messages.nav.brand}
              </Link>
              <nav className="hidden items-center gap-2 md:flex">
                <Link
                  href={withLocale(locale, "/app")}
                  className={cn(
                    buttonVariants({ variant: "ghost", size: "sm" }),
                    "rounded-full text-xs font-medium",
                  )}
                >
                  {messages.nav.workspace}
                </Link>
                <Link
                  href={withLocale(locale, "/profile")}
                  className={cn(
                    buttonVariants({ variant: "ghost", size: "sm" }),
                    "rounded-full text-xs font-medium",
                  )}
                >
                  {messages.nav.profile}
                </Link>
                <a
                  href="https://github.com/richardzhux/iching"
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    buttonVariants({ variant: "ghost", size: "sm" }),
                    "rounded-full text-xs font-medium",
                  )}
                >
                  {messages.nav.github}
                </a>
              </nav>
            </div>
            <div className="flex items-center gap-2">
              <Suspense fallback={null}>
                <LanguageToggle />
              </Suspense>
              <ThemeToggle />
              <ProfileMenu />
            </div>
          </div>
        </header>
        <main className="relative z-10 mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-10 lg:py-12">
          {children}
        </main>
      </div>
    </I18nProvider>
  )
}
