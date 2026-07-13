"use client"

import { useEffect, useId, useRef, useState } from "react"
import { Loader2, LocateFixed, MapPin } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { LocationResult } from "@/lib/location-search"

type Locale = "en" | "zh"
type CurrentLocationCandidate = { result: LocationResult; distanceKm: number }

type Props = {
  locale: Locale
  selectedLocation: LocationResult | null
  overrideActive: boolean
  effectiveTimezone: string
  effectiveLongitude: string
  onSelect: (location: LocationResult) => void
  onClear: () => void
}

export function BirthPlaceField({ locale, selectedLocation, overrideActive, effectiveTimezone, effectiveLongitude, onSelect, onClear }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const requestSequenceRef = useRef(0)
  const geolocationSequenceRef = useRef(0)
  const geolocationControllerRef = useRef<AbortController | null>(null)
  const listboxId = useId()
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<LocationResult[]>([])
  const [activeIndex, setActiveIndex] = useState(-1)
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [geolocationLoading, setGeolocationLoading] = useState(false)
  const [geolocationError, setGeolocationError] = useState<string | null>(null)
  const [currentLocationCandidate, setCurrentLocationCandidate] = useState<CurrentLocationCandidate | null>(null)

  const copy = locale === "zh" ? {
    label: "出生城市",
    placeholder: "输入城市，如上海、成都、London",
    hint: "请从结果中选择；选择后会填写时区和经度，专业设置中的手动修改仍优先。",
    loading: "正在查找城市…",
    empty: "没有找到匹配城市，请尝试城市、地区或国家名称。",
    error: "城市查找暂时不可用，请稍后重试。",
    resolved: "已选择出生城市",
    cityDefault: "城市默认值",
    override: "专业设置覆盖已生效；排盘将使用手动时区和经度",
    replace: "更换城市",
    clear: "清除",
    listLabel: "城市搜索结果",
    useCurrent: "使用当前位置",
    locating: "正在定位并匹配附近城市…",
    geolocationError: "无法确定清晰的附近城市。你仍可手动搜索出生城市。",
    unsupported: "此设备不支持定位。你仍可手动搜索出生城市。",
    candidate: "附近城市候选",
    warning: "当前位置可能不是出生地，请确认后再应用。",
    confirm: "确认使用",
    cancel: "取消",
    distance: "约 {distance} 公里",
  } : {
    label: "Birth city",
    placeholder: "Enter a city, such as Shanghai or London",
    hint: "Choose a result to fill time zone and longitude. Manual changes in professional settings remain authoritative.",
    loading: "Searching cities…",
    empty: "No matching city found. Try a city, region, or country name.",
    error: "City search is temporarily unavailable. Please try again.",
    resolved: "Selected birth city",
    cityDefault: "City defaults",
    override: "Professional override active; the chart will use the manual time zone and longitude",
    replace: "Replace city",
    clear: "Clear",
    listLabel: "City search results",
    useCurrent: "Use current location",
    locating: "Locating and matching a nearby city…",
    geolocationError: "No clear nearby city could be determined. You can still search manually.",
    unsupported: "Location is unavailable on this device. You can still search manually.",
    candidate: "Nearby city candidate",
    warning: "Your current location may not be your birth place. Confirm before applying it.",
    confirm: "Confirm city",
    cancel: "Cancel",
    distance: "about {distance} km away",
  }

  useEffect(() => {
    const trimmedQuery = query.trim()
    if (selectedLocation || trimmedQuery.length < 2) return

    const requestId = requestSequenceRef.current
    const controller = new AbortController()
    const timer = window.setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await fetch(`/api/locations?q=${encodeURIComponent(trimmedQuery)}&locale=${locale}`, { signal: controller.signal })
        if (!response.ok) throw new Error("location search failed")
        const payload = await response.json() as { results?: LocationResult[] }
        if (!controller.signal.aborted && requestId === requestSequenceRef.current) {
          setResults((payload.results || []).slice(0, 8))
          setActiveIndex(-1)
          setSearched(true)
        }
      } catch (requestError) {
        if (!controller.signal.aborted && requestId === requestSequenceRef.current && (requestError as Error).name !== "AbortError") {
          setResults([])
          setError(copy.error)
          setSearched(true)
        }
      } finally {
        if (!controller.signal.aborted && requestId === requestSequenceRef.current) setLoading(false)
      }
    }, 250)

    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [copy.error, locale, query, selectedLocation])

  useEffect(() => {
    if (activeIndex < 0) return
    document.getElementById(`${listboxId}-option-${activeIndex}`)?.scrollIntoView({ block: "nearest" })
  }, [activeIndex, listboxId])

  useEffect(() => () => {
    geolocationSequenceRef.current += 1
    geolocationControllerRef.current?.abort()
  }, [])

  function invalidateGeolocation() {
    geolocationSequenceRef.current += 1
    geolocationControllerRef.current?.abort()
    geolocationControllerRef.current = null
    setGeolocationLoading(false)
    setGeolocationError(null)
    setCurrentLocationCandidate(null)
  }

  function clearSearchState() {
    requestSequenceRef.current += 1
    setResults([])
    setActiveIndex(-1)
    setLoading(false)
    setSearched(false)
    setError(null)
  }

  function handleQueryChange(value: string) {
    invalidateGeolocation()
    requestSequenceRef.current += 1
    setResults([])
    setActiveIndex(-1)
    setLoading(false)
    setSearched(false)
    setError(null)
    setQuery(value)
  }

  function selectResult(result: LocationResult) {
    invalidateGeolocation()
    onSelect(result)
    setQuery("")
    clearSearchState()
    setGeolocationError(null)
    setCurrentLocationCandidate(null)
  }

  function clearSelection(focusInput: boolean) {
    invalidateGeolocation()
    onClear()
    setQuery("")
    clearSearchState()
    setGeolocationError(null)
    setCurrentLocationCandidate(null)
    if (focusInput) window.requestAnimationFrame(() => inputRef.current?.focus())
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && results.length) {
      event.preventDefault()
      setActiveIndex((index) => index >= results.length - 1 ? 0 : index + 1)
    } else if (event.key === "ArrowUp" && results.length) {
      event.preventDefault()
      setActiveIndex((index) => index <= 0 ? results.length - 1 : index - 1)
    } else if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault()
      const result = results[activeIndex]
      if (result) selectResult(result)
    } else if (event.key === "Escape") {
      clearSearchState()
    }
  }

  async function matchCurrentCoordinates(position: GeolocationPosition, requestId: number) {
    const controller = new AbortController()
    geolocationControllerRef.current?.abort()
    geolocationControllerRef.current = controller
    try {
      const response = await fetch("/api/locations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          locale,
        }),
      })
      if (!response.ok) throw new Error("nearest location failed")
      const payload = await response.json() as { result: LocationResult | null; distanceKm?: number }
      if (controller.signal.aborted || requestId !== geolocationSequenceRef.current) return
      if (!payload.result || typeof payload.distanceKm !== "number") {
        setGeolocationError(copy.geolocationError)
        return
      }
      setCurrentLocationCandidate({ result: payload.result, distanceKm: payload.distanceKm })
    } catch (requestError) {
      if (!controller.signal.aborted && requestId === geolocationSequenceRef.current && (requestError as Error).name !== "AbortError") {
        setGeolocationError(copy.geolocationError)
      }
    } finally {
      if (requestId === geolocationSequenceRef.current) {
        geolocationControllerRef.current = null
        setGeolocationLoading(false)
      }
    }
  }

  function useCurrentLocation() {
    invalidateGeolocation()
    const requestId = geolocationSequenceRef.current
    setGeolocationError(null)
    setCurrentLocationCandidate(null)
    if (!("geolocation" in navigator)) {
      setGeolocationError(copy.unsupported)
      return
    }
    setGeolocationLoading(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        if (requestId === geolocationSequenceRef.current) void matchCurrentCoordinates(position, requestId)
      },
      () => {
        if (requestId !== geolocationSequenceRef.current) return
        setGeolocationLoading(false)
        setGeolocationError(copy.geolocationError)
      },
      { enableHighAccuracy: false, timeout: 8_000, maximumAge: 300_000 },
    )
  }

  function confirmCurrentLocation() {
    if (!currentLocationCandidate) return
    geolocationControllerRef.current?.abort()
    onSelect(currentLocationCandidate.result)
    setCurrentLocationCandidate(null)
    setGeolocationError(null)
  }

  function cancelCurrentLocation() {
    invalidateGeolocation()
    inputRef.current?.focus()
  }

  if (selectedLocation) {
    return (
      <div className="space-y-2 md:col-span-2">
        <p className="text-sm font-medium">{copy.label}</p>
        <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 gap-2">
              <MapPin aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-primary" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-muted-foreground">{copy.resolved}</p>
                <p className="mt-1 font-medium">{selectedLocation.name}</p>
                <p className="text-xs text-muted-foreground">{[selectedLocation.region, selectedLocation.country].filter(Boolean).join(" · ")}</p>
                <p className="mt-1 text-xs text-muted-foreground">{copy.cityDefault}: {selectedLocation.timezone} · {selectedLocation.longitude.toFixed(4)}°</p>
                {overrideActive ? <p role="status" className="mt-2 rounded border border-primary/30 bg-surface px-2 py-1 text-xs text-foreground">{copy.override}: {effectiveTimezone} · {effectiveLongitude || "—"}°</p> : null}
              </div>
            </div>
            <div className="flex gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => clearSelection(true)}>{copy.replace}</Button>
              <Button type="button" variant="ghost" size="sm" onClick={() => clearSelection(false)}>{copy.clear}</Button>
            </div>
          </div>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{copy.hint}</p>
        </div>
      </div>
    )
  }

  const listboxOpen = results.length > 0
  const currentLocationCandidateVisible = !query.trim() ? currentLocationCandidate : null
  return (
    <div className="relative space-y-2 md:col-span-2">
      <label htmlFor="bazi-birth-place" className="text-sm font-medium">{copy.label}</label>
      <Input
        ref={inputRef}
        id="bazi-birth-place"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={listboxOpen}
        aria-controls={listboxOpen ? listboxId : undefined}
        aria-activedescendant={listboxOpen && activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined}
        aria-describedby="bazi-birth-place-hint"
        autoComplete="off"
        value={query}
        maxLength={100}
        placeholder={copy.placeholder}
        onChange={(event) => handleQueryChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <p id="bazi-birth-place-hint" className="text-xs leading-5 text-muted-foreground">{copy.hint}</p>
      <Button type="button" variant="outline" size="sm" disabled={geolocationLoading} onClick={useCurrentLocation}>
        {geolocationLoading ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : <LocateFixed aria-hidden="true" className="mr-2 size-4" />}
        {geolocationLoading ? copy.locating : copy.useCurrent}
      </Button>

      {geolocationError ? <p role="alert" className="text-sm text-destructive">{geolocationError}</p> : null}
      {currentLocationCandidateVisible ? (
        <section aria-label={copy.candidate} className="rounded-md border border-primary/30 bg-primary/5 p-3">
          <p className="text-xs font-semibold text-muted-foreground">{copy.candidate}</p>
          <p className="mt-1 font-medium">{currentLocationCandidateVisible.result.name}</p>
          <p className="text-xs text-muted-foreground">{[currentLocationCandidateVisible.result.region, currentLocationCandidateVisible.result.country].filter(Boolean).join(" · ")} · {copy.distance.replace("{distance}", String(currentLocationCandidateVisible.distanceKm))}</p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{copy.warning}</p>
          <div className="mt-3 flex gap-2">
            <Button type="button" size="sm" onClick={confirmCurrentLocation}>{copy.confirm}</Button>
            <Button type="button" variant="outline" size="sm" onClick={cancelCurrentLocation}>{copy.cancel}</Button>
          </div>
        </section>
      ) : null}

      {loading ? <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 aria-hidden="true" className="size-4 animate-spin" />{copy.loading}</p> : null}
      {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
      {!loading && !error && searched && results.length === 0 ? <p role="status" className="text-sm text-muted-foreground">{copy.empty}</p> : null}
      {listboxOpen ? (
        <ul id={listboxId} role="listbox" aria-label={copy.listLabel} className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-border bg-surface p-1 shadow-lg">
          {results.map((result, index) => (
            <li key={result.id}>
              <button
                id={`${listboxId}-option-${index}`}
                type="button"
                role="option"
                aria-selected={activeIndex === index}
                tabIndex={-1}
                className={`w-full rounded px-3 py-2 text-left text-sm focus-visible:outline-none ${activeIndex === index ? "bg-primary/10" : "hover:bg-surface-elevated"}`}
                onMouseEnter={() => setActiveIndex(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => selectResult(result)}
              >
                <span className="block font-medium">{result.name}</span>
                <span className="block text-xs text-muted-foreground">{[result.region, result.country].filter(Boolean).join(" · ")} · {result.timezone}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
