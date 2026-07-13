"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useI18n } from "@/components/providers/i18n-provider"
import { cn } from "@/lib/utils"

type Props = {
  className?: string
  mobile?: boolean
}

export function PrimaryNavigation({ className, mobile = false }: Props) {
  const pathname = usePathname()
  const { messages, toLocalePath } = useI18n()
  const links = [
    { href: "/app", label: messages.nav.workspace, matches: ["/app"] },
    { href: "/reading", label: messages.nav.reading, matches: ["/reading"] },
    { href: "/library", label: messages.nav.library, matches: ["/library", "/hexagram"] },
    { href: "/tools", label: messages.nav.method, matches: ["/tools"] },
  ]

  return (
    <nav
      aria-label={mobile ? messages.nav.mobileMenuAria : undefined}
      className={cn(
        "items-center gap-1",
        mobile ? "flex w-full gap-2 overflow-x-auto px-4 py-2 sm:px-6" : "flex",
        className,
      )}
    >
      {links.map(({ href, label, matches }) => {
        const localizedHref = toLocalePath(href)
        const active = matches.some((route) => {
          const localizedRoute = toLocalePath(route)
          return pathname === localizedRoute || pathname.startsWith(`${localizedRoute}/`)
        })
        return (
          <Link
            key={href}
            href={localizedHref}
            aria-current={active ? "page" : undefined}
            className={cn(
              "inline-flex min-h-11 shrink-0 items-center justify-center rounded-md px-3 text-sm font-medium text-muted-foreground outline-none transition",
              "hover:bg-accent/75 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              active && "bg-primary/10 text-primary ring-1 ring-primary/25",
            )}
          >
            {label}
          </Link>
        )
      })}
    </nav>
  )
}
