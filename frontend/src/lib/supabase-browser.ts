"use client"

import { createClient, type SupabaseClient } from "@supabase/supabase-js"

let browserClient: SupabaseClient | null = null

export function getSupabaseClient() {
  if (browserClient) {
    return browserClient
  }
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !anonKey) {
    throw new Error("Supabase 环境变量缺失。")
  }
  browserClient = createClient(url, anonKey, {
    auth: {
      persistSession: true,
      detectSessionInUrl: true,
    },
  })
  return browserClient
}
