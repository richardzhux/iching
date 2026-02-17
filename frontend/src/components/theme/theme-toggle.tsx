"use client"

import { useState } from "react"
import { MoonStar, SunMedium } from "lucide-react"
import { useTheme } from "next-themes"

import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function ThemeToggle({ className }: { className?: string }) {
  const { messages } = useI18n()
  const { setTheme, theme, resolvedTheme } = useTheme()
  const [mounted] = useState(() => typeof window !== "undefined")

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
          "rounded-full border-border/70 bg-background/80 text-foreground shadow-lg backdrop-blur",
          className
        )}
        data-state="loading"
        disabled
      >
        <span className="h-3 w-12 animate-pulse rounded-full bg-foreground/20" />
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
        "rounded-full border-border/70 bg-background/80 text-foreground shadow-lg backdrop-blur data-[state=loading]:pointer-events-none",
        className
      )}
      data-state={mounted ? undefined : "loading"}
    >
      {mounted ? (
        <>
          {icon}
          <span className="text-xs font-medium">
            {resolvedTheme === "dark"
              ? messages.theme.dark
              : resolvedTheme === "light"
                ? messages.theme.light
                : theme}
          </span>
        </>
      ) : (
        <span className="h-3 w-12 animate-pulse rounded-full bg-foreground/20" />
      )}
    </Button>
  )
}
