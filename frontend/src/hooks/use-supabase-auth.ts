"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type { Provider, Session, User } from "@supabase/supabase-js"
import { getSupabaseClient } from "@/lib/supabase-browser"

type AuthHook = {
  session: Session | null
  user: User | null
  accessToken: string | null
  displayName: string | null
  avatarUrl: string | null
  loading: boolean
  error: string | null
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  signInWithProvider: (provider: Provider) => Promise<void>
}

export function useSupabaseAuth(): AuthHook {
  const supabase = useMemo(() => getSupabaseClient(), [])
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return
      setSession(data.session)
      setUser(data.session?.user ?? null)
      setLoading(false)
    })
    const { data: subscription } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setUser(nextSession?.user ?? null)
      setLoading(false)
    })
    return () => {
      mounted = false
      subscription.subscription.unsubscribe()
    }
  }, [supabase])

  const accessToken = session?.access_token ?? null

  const signIn = useCallback(
    async (email: string, password: string) => {
      setError(null)
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (signInError) {
        setError(signInError.message)
        throw signInError
      }
    },
    [supabase],
  )

  const signUp = useCallback(
    async (email: string, password: string) => {
      setError(null)
      const redirectTo =
        typeof window !== "undefined" ? `${window.location.origin}/app` : undefined
      const { error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: redirectTo,
        },
      })
      if (signUpError) {
        setError(signUpError.message)
        throw signUpError
      }
    },
    [supabase],
  )

  const signOut = useCallback(async () => {
    setError(null)
    const { error: signOutError } = await supabase.auth.signOut()
    if (signOutError) {
      setError(signOutError.message)
      throw signOutError
    }
  }, [supabase])

  const signInWithProvider = useCallback(
    async (provider: Provider) => {
      setError(null)
      const redirectTo = typeof window !== "undefined" ? window.location.href : undefined
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo,
        },
      })
      if (oauthError) {
        setError(oauthError.message)
        throw oauthError
      }
    },
    [supabase],
  )

  return {
    session,
    user,
    accessToken,
    displayName:
      (user?.user_metadata?.full_name as string | undefined) ||
      (user?.user_metadata?.name as string | undefined) ||
      (user?.user_metadata?.user_name as string | undefined) ||
      user?.email?.split("@")[0] ||
      null,
    avatarUrl:
      (user?.user_metadata?.avatar_url as string | undefined) ||
      (user?.user_metadata?.picture as string | undefined) ||
      (user?.user_metadata?.profile_image_url as string | undefined) ||
      null,
    loading,
    error,
    signIn,
    signUp,
    signOut,
    signInWithProvider,
  }
}
