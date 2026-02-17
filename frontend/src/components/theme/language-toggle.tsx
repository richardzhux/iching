"use client"

import { useMemo, useTransition } from "react"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { useI18n } from "@/components/providers/i18n-provider"
import type { Locale } from "@/i18n/config"
import { replaceLocaleInPath } from "@/i18n/path"
import { cn } from "@/lib/utils"

function persistLocale(locale: Locale) {
  if (typeof document === "undefined") return
  document.cookie = `locale=${locale};path=/;max-age=31536000;samesite=lax`
}

export function LanguageToggle({ className }: { className?: string }) {
  const { locale, messages } = useI18n()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  const options: Array<{ value: Locale; label: string }> = useMemo(
    () => [
      { value: "en", label: messages.language.en },
      { value: "zh", label: messages.language.zh },
    ],
    [messages.language.en, messages.language.zh],
  )

  function handleSwitch(nextLocale: Locale) {
    if (nextLocale === locale || isPending) return
    const nextPath = replaceLocaleInPath(pathname || "/", nextLocale)
    const query = searchParams.toString()
    const href = query ? `${nextPath}?${query}` : nextPath

    persistLocale(nextLocale)

    startTransition(() => {
      router.replace(href)
    })
  }

  return (
    <div
      role="group"
      aria-label={messages.language.label}
      className={cn(
        "inline-flex items-center rounded-full border border-border/60 bg-background/75 p-1 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-background/65",
        className,
      )}
    >
      {options.map((option) => {
        const active = option.value === locale
        return (
          <Button
            key={option.value}
            type="button"
            size="sm"
            variant={active ? "default" : "ghost"}
            onClick={() => handleSwitch(option.value)}
            className={cn(
              "h-7 rounded-full px-3 text-xs font-semibold",
              active ? "shadow-sm" : "text-muted-foreground",
            )}
            disabled={isPending}
          >
            {option.label}
          </Button>
        )
      })}
    </div>
  )
}
