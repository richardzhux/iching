"use client"

import { createContext, useContext, type ReactNode } from "react"
import { useSupabaseAuth } from "@/hooks/use-supabase-auth"

type AuthContextValue = ReturnType<typeof useSupabaseAuth>

const AuthContext = createContext<AuthContextValue | null>(null)

type Props = {
  children: ReactNode
}

export function SupabaseAuthProvider({ children }: Props) {
  const auth = useSupabaseAuth()
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>
}

export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuthContext must be used within SupabaseAuthProvider")
  }
  return context
}
