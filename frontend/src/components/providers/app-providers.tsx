"use client"

import { type ReactNode } from "react"
import { QueryProvider } from "@/components/providers/query-provider"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { Toaster } from "@/components/ui/sonner"

type Props = {
  children: ReactNode
}

export function AppProviders({ children }: Props) {
  return (
    <ThemeProvider>
      <QueryProvider>
        {children}
        <Toaster position="bottom-right" />
      </QueryProvider>
    </ThemeProvider>
  )
}
