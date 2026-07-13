import { NextResponse } from "next/server"
import { findNearestLocation, isValidCoordinates, normalizeLocationQuery, searchLocations } from "@/lib/location-search"

export const runtime = "nodejs"

export function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const query = normalizeLocationQuery(searchParams.get("q") || "")
  const localeParam = searchParams.get("locale")
  const locale = localeParam === "zh" ? "zh" : "en"

  if (query.trim().length < 2) return NextResponse.json({ results: [] })

  try {
    const results = searchLocations(query, locale).slice(0, 8)
    return NextResponse.json({ results })
  } catch {
    return NextResponse.json(
      { results: [], error: "Unable to search locations. Please try again." },
      { status: 500 },
    )
  }
}

function invalidCoordinatesResponse() {
  return NextResponse.json(
    { result: null, error: "Invalid location coordinates." },
    { status: 400 },
  )
}

export async function POST(request: Request) {
  let payload: unknown
  try {
    payload = await request.json()
  } catch {
    return invalidCoordinatesResponse()
  }

  if (!payload || typeof payload !== "object") return invalidCoordinatesResponse()
  const { latitude, longitude, locale: localeParam } = payload as Record<string, unknown>
  if (typeof latitude !== "number" || typeof longitude !== "number" || !isValidCoordinates(latitude, longitude)) {
    return invalidCoordinatesResponse()
  }
  const locale = localeParam === "zh" ? "zh" : "en"

  try {
    const nearest = findNearestLocation(latitude, longitude, locale)
    if (!nearest) return NextResponse.json({ result: null })
    return NextResponse.json({ result: nearest.result, distanceKm: nearest.distanceKm })
  } catch {
    return NextResponse.json(
      { result: null, error: "Unable to match the current location. Please try again." },
      { status: 500 },
    )
  }
}
