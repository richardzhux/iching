"use client"

import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { BirthPlaceField } from "@/components/tools/birth-place-field"
import type { LocationResult } from "@/lib/location-search"

export type BaziControlCopy = {
  subjectName: string
  basicSettings: string
  professionalSettings: string
  professionalSettingsHint: string
  timezone: string
  birth: string
  calendar: string
  solar: string
  lunar: string
  lunarDateFormat: string
  leapMonth: string
  birthPlace: string
  birthPlaceHint: string
  dayunRule: string
  dayunRuleHint: string
  dayunSect1: string
  dayunSect2: string
  longitude: string
  longitudeHint: string
  trueSolar: string
  boundary: string
  gender: string
  male: string
  female: string
}

type Props = {
  copy: BaziControlCopy
  locale: "en" | "zh"
  subjectName: string
  setSubjectName: (value: string) => void
  birthTime: string
  setBirthTime: (value: string) => void
  lunarBirthDate: string
  setLunarBirthDate: (value: string) => void
  lunarBirthTime: string
  setLunarBirthTime: (value: string) => void
  timezone: string
  setTimezone: (value: string) => void
  timezoneOptions: string[]
  longitude: string
  setLongitude: (value: string) => void
  trueSolar: boolean
  setTrueSolar: (value: boolean) => void
  dayBoundary: "current" | "forward"
  setDayBoundary: (value: "current" | "forward") => void
  calendar: "solar" | "lunar"
  setCalendar: (value: "solar" | "lunar") => void
  gender: "male" | "female"
  setGender: (value: "male" | "female") => void
  selectedLocation: LocationResult | null
  birthPlaceOverrideActive: boolean
  effectiveTimezone: string
  effectiveLongitude: string
  onBirthPlaceSelect: (location: LocationResult) => void
  onBirthPlaceClear: () => void
  isLeapMonth: boolean
  setIsLeapMonth: (value: boolean) => void
  dayunAlgorithm: "sect1" | "sect2"
  setDayunAlgorithm: (value: "sect1" | "sect2") => void
}

export function BaziControls({
  copy,
  locale,
  subjectName,
  setSubjectName,
  birthTime,
  setBirthTime,
  lunarBirthDate,
  setLunarBirthDate,
  lunarBirthTime,
  setLunarBirthTime,
  timezone,
  setTimezone,
  timezoneOptions,
  longitude,
  setLongitude,
  trueSolar,
  setTrueSolar,
  dayBoundary,
  setDayBoundary,
  calendar,
  setCalendar,
  gender,
  setGender,
  selectedLocation,
  birthPlaceOverrideActive,
  effectiveTimezone,
  effectiveLongitude,
  onBirthPlaceSelect,
  onBirthPlaceClear,
  isLeapMonth,
  setIsLeapMonth,
  dayunAlgorithm,
  setDayunAlgorithm,
}: Props) {
  return (
    <div className="space-y-4">
      <section aria-labelledby="bazi-basic-heading" className="rounded-lg border border-border/60 bg-surface p-4">
        <h2 id="bazi-basic-heading" className="text-sm font-semibold text-foreground">{copy.basicSettings}</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label htmlFor="bazi-subject-name" className="text-sm font-medium">{copy.subjectName}</label>
            <Input id="bazi-subject-name" value={subjectName} maxLength={40} autoComplete="name" placeholder={locale === "zh" ? "选填，用于命盘与导出" : "Optional, used on the chart and export"} onChange={(event) => setSubjectName(event.target.value)} />
          </div>
          <div className="space-y-2">
            <label id="bazi-calendar-label" className="text-sm font-medium">{copy.calendar}</label>
            <Select value={calendar} onValueChange={(value) => setCalendar(value as "solar" | "lunar")}>
              <SelectTrigger id="bazi-calendar" aria-labelledby="bazi-calendar-label"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="solar">{copy.solar}</SelectItem><SelectItem value="lunar">{copy.lunar}</SelectItem></SelectContent>
            </Select>
          </div>

          {calendar === "solar" ? (
            <div className="space-y-2">
              <label htmlFor="bazi-birth-time" className="text-sm font-medium">{copy.birth}</label>
              <Input id="bazi-birth-time" type="datetime-local" value={birthTime} required onChange={(event) => setBirthTime(event.target.value)} />
            </div>
          ) : (
            <div className="grid gap-2 sm:grid-cols-[1fr_8rem]">
              <div className="space-y-2">
                <label htmlFor="bazi-lunar-date" className="text-sm font-medium">{copy.lunarDateFormat}</label>
                <Input id="bazi-lunar-date" value={lunarBirthDate} inputMode="numeric" placeholder="1990-01-01" onChange={(event) => setLunarBirthDate(event.target.value)} />
              </div>
              <div className="space-y-2">
                <label htmlFor="bazi-lunar-time" className="text-sm font-medium">{copy.birth}</label>
                <Input id="bazi-lunar-time" type="time" value={lunarBirthTime} required onChange={(event) => setLunarBirthTime(event.target.value)} />
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label id="bazi-gender-label" className="text-sm font-medium">{copy.gender}</label>
            <Select value={gender} onValueChange={(value) => setGender(value as "male" | "female")}>
              <SelectTrigger id="bazi-gender" aria-labelledby="bazi-gender-label"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="male">{copy.male}</SelectItem><SelectItem value="female">{copy.female}</SelectItem></SelectContent>
            </Select>
          </div>

          <BirthPlaceField locale={locale} selectedLocation={selectedLocation} overrideActive={birthPlaceOverrideActive} effectiveTimezone={effectiveTimezone} effectiveLongitude={effectiveLongitude} onSelect={onBirthPlaceSelect} onClear={onBirthPlaceClear} />

        </div>
      </section>

      <details className="rounded-lg border border-border/60 bg-surface px-4 py-3">
        <summary className="cursor-pointer text-sm font-semibold text-foreground">{copy.professionalSettings}</summary>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">{copy.professionalSettingsHint}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label id="bazi-timezone-label" className="text-sm font-medium">{copy.timezone}</label>
            <Select value={timezone} onValueChange={setTimezone}>
              <SelectTrigger id="bazi-timezone" aria-labelledby="bazi-timezone-label"><SelectValue /></SelectTrigger>
              <SelectContent>{timezoneOptions.map((zone) => <SelectItem key={zone} value={zone}>{zone}</SelectItem>)}</SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2">
            <label htmlFor="bazi-true-solar" className="text-sm">{copy.trueSolar}</label>
            <Switch id="bazi-true-solar" checked={trueSolar} onCheckedChange={setTrueSolar} />
          </div>

          {trueSolar ? (
            <div className="space-y-2">
              <label htmlFor="bazi-longitude" className="text-sm font-medium">{copy.longitude}</label>
              <Input id="bazi-longitude" type="number" min={-180} max={180} step="0.0001" placeholder="121.4737" value={longitude} aria-describedby="bazi-longitude-hint" onChange={(event) => setLongitude(event.target.value)} />
              <p id="bazi-longitude-hint" className="text-xs leading-5 text-muted-foreground">{copy.longitudeHint}</p>
            </div>
          ) : null}

          <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2">
            <label htmlFor="bazi-day-boundary" className="text-sm">{copy.boundary}</label>
            <Switch id="bazi-day-boundary" checked={dayBoundary === "forward"} onCheckedChange={(checked) => setDayBoundary(checked ? "forward" : "current")} />
          </div>

          {calendar === "lunar" ? (
            <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2">
              <label htmlFor="bazi-leap-month" className="text-sm">{copy.leapMonth}</label>
              <Switch id="bazi-leap-month" checked={isLeapMonth} onCheckedChange={setIsLeapMonth} />
            </div>
          ) : null}

          <div className="space-y-2">
            <label id="bazi-dayun-algorithm-label" className="text-sm font-medium">{copy.dayunRule}</label>
            <Select value={dayunAlgorithm} onValueChange={(value) => setDayunAlgorithm(value as "sect1" | "sect2")}>
              <SelectTrigger id="bazi-dayun-algorithm" aria-labelledby="bazi-dayun-algorithm-label"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="sect2">{copy.dayunSect2}</SelectItem><SelectItem value="sect1">{copy.dayunSect1}</SelectItem></SelectContent>
            </Select>
            <p className="text-xs leading-5 text-muted-foreground">{copy.dayunRuleHint}</p>
          </div>
        </div>
      </details>
    </div>
  )
}
