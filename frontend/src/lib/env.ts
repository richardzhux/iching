const DEV_API_BASE_URL = "http://localhost:8000"

export class PublicEnvError extends Error {
  constructor(message: string) {
    super(message)
    this.name = "PublicEnvError"
  }
}

function trimTrailingSlash(value: string) {
  return value.replace(/\/+$/, "")
}

export function getApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim()
  if (configured) {
    return trimTrailingSlash(configured)
  }

  if (process.env.NODE_ENV === "production") {
    throw new PublicEnvError("Missing NEXT_PUBLIC_API_BASE_URL for the public reading API.")
  }

  return DEV_API_BASE_URL
}

export const PUBLIC_SITE_URL = "https://iching.richardzhux.com"
