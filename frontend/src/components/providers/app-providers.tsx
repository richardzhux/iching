"use client"

import { type ReactNode } from "react"
import { QueryProvider } from "@/components/providers/query-provider"
import { SupabaseAuthProvider } from "@/components/providers/auth-provider"
import { ThemeProvider } from "@/components/providers/theme-provider"
import { Toaster } from "@/components/ui/sonner"

type Props = {
  children: ReactNode
}

export function AppProviders({ children }: Props) {
  return (
    <ThemeProvider>
      <QueryProvider>
        <SupabaseAuthProvider>
          {children}
          <Toaster position="bottom-right" />
        </SupabaseAuthProvider>
      </QueryProvider>
    </ThemeProvider>
  )
}
