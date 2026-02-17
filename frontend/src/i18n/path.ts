import { defaultLocale, isLocale, type Locale } from "@/i18n/config"

function normalizePath(path: string): string {
  if (!path) return "/"
  return path.startsWith("/") ? path : `/${path}`
}

export function withLocale(locale: Locale, path: string = "/"): string {
  const normalized = normalizePath(path)
  if (normalized === "/") {
    return `/${locale}`
  }
  return `/${locale}${normalized}`
}

export function stripLocaleFromPath(pathname: string): string {
  const normalized = normalizePath(pathname)
  const segments = normalized.split("/")
  const first = segments[1]
  if (!isLocale(first)) {
    return normalized
  }
  const remainder = segments.slice(2).join("/")
  return remainder ? `/${remainder}` : "/"
}

export function replaceLocaleInPath(pathname: string, locale: Locale): string {
  const routeWithoutLocale = stripLocaleFromPath(pathname)
  return withLocale(locale, routeWithoutLocale)
}

export function resolveLocaleFromPath(pathname: string): Locale {
  const normalized = normalizePath(pathname)
  const first = normalized.split("/")[1]
  return isLocale(first) ? first : defaultLocale
}
