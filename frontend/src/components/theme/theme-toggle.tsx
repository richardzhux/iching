"use client"

import { useEffect, useState } from "react"
import { MoonStar, SunMedium } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export function ThemeToggle({ className }: { className?: string }) {
  const { setTheme, theme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

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
        aria-label="切换主题"
        title="切换主题"
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

  const label = resolvedTheme === "dark" ? "切换至浅色模式" : "切换至深色模式"
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
            {resolvedTheme === "dark" ? "深色" : resolvedTheme === "light" ? "浅色" : theme}
          </span>
        </>
      ) : (
        <span className="h-3 w-12 animate-pulse rounded-full bg-foreground/20" />
      )}
    </Button>
  )
}
