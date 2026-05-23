import { track } from "@vercel/analytics"

type AnalyticsPayload = Record<string, string | number | boolean | null | undefined>

const SAFE_EVENT_NAMES = new Set([
  "start_cast_clicked",
  "reading_created",
  "source_drawer_opened",
  "library_search_used",
])

export function trackProductEvent(name: string, payload: AnalyticsPayload = {}) {
  if (!SAFE_EVENT_NAMES.has(name)) return
  const safePayload = Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined),
  ) as Record<string, string | number | boolean | null>
  track(name, safePayload)
}
