const DEV_API_BASE_URL = "http://localhost:8000"

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "")
}

export function getApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
  if (configured) {
    return trimTrailingSlash(configured)
  }

  if (process.env.NODE_ENV === "production") {
    // Vercel routes the frontend and reading API on the same public domain.
    return ""
  }

  return DEV_API_BASE_URL
}

export const PUBLIC_SITE_URL = "https://iching.richardzhux.com"
