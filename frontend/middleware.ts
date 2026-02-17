import { NextRequest, NextResponse } from "next/server"
import { defaultLocale, isLocale, type Locale } from "./src/i18n/config"

const PUBLIC_FILE = /\.(.*)$/

function localeFromAcceptLanguage(header: string | null): Locale {
  if (!header) return defaultLocale
  const lower = header.toLowerCase()
  if (lower.includes("zh")) return "zh"
  return "en"
}

function resolveLocale(request: NextRequest): Locale {
  const cookieLocale = request.cookies.get("locale")?.value
  if (cookieLocale && isLocale(cookieLocale)) {
    return cookieLocale
  }
  return localeFromAcceptLanguage(request.headers.get("accept-language"))
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (
    pathname.startsWith("/api")
    || pathname.startsWith("/_next")
    || PUBLIC_FILE.test(pathname)
  ) {
    return NextResponse.next()
  }

  const segment = pathname.split("/")[1]
  if (isLocale(segment)) {
    return NextResponse.next()
  }

  const locale = resolveLocale(request)
  const url = request.nextUrl.clone()
  url.pathname = pathname === "/" ? `/${locale}` : `/${locale}${pathname}`
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
}
