"use client"

import { useSyncExternalStore } from "react"
import { MoonStar, SunMedium } from "lucide-react"
import { useTheme } from "next-themes"

import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function ThemeToggle({ className }: { className?: string }) {
  const { messages } = useI18n()
  const { setTheme, theme, resolvedTheme } = useTheme()
  const mounted = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  )

  const nextTheme = () => {
    if (!mounted) return
    if (resolvedTheme === "dark") {
      setTheme("light")
    } else {
      setTheme("dark")
    }
  }

  if (!mounted) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-label={messages.theme.toDark}
        title={messages.theme.toDark}
        className={cn(
          "autumn-theme-toggle border-transparent bg-transparent text-muted-foreground",
          className
        )}
        data-state="loading"
        disabled
      >
        <span className="size-4 animate-pulse rounded-sm bg-foreground/20" />
      </Button>
    )
  }

  const label = resolvedTheme === "dark" ? messages.theme.toLight : messages.theme.toDark
  const icon =
    resolvedTheme === "dark" ? (
      <SunMedium className="size-4" aria-hidden="true" />
    ) : (
      <MoonStar className="size-4" aria-hidden="true" />
    )

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-label={label}
      title={label}
      onClick={nextTheme}
      className={cn(
        "autumn-theme-toggle border-transparent bg-transparent text-muted-foreground data-[state=loading]:pointer-events-none",
        className
      )}
      data-state={mounted ? undefined : "loading"}
    >
      {mounted ? (
        <>
          {icon}
          <span className="hidden text-xs font-medium lg:inline">
            {resolvedTheme === "dark"
              ? messages.theme.dark
              : resolvedTheme === "light"
                ? messages.theme.light
                : theme}
          </span>
        </>
      ) : (
        <span className="size-4 animate-pulse rounded-sm bg-foreground/20" />
      )}
    </Button>
  )
}
