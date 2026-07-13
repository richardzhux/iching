"use client"

import Link from "next/link"
import { useEffect, useMemo, useState } from "react"
import { CalendarClock, Compass, Loader2, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BaziChartView } from "@/components/tools/bazi-chart-view"
import { BaziControls } from "@/components/tools/metaphysics-controls"
import { ZiweiChartView, type ZiweiProvenance } from "@/components/tools/ziwei-chart-view"
import { calculateMetaphysicsChart } from "@/lib/api"
import type { LocationResult } from "@/lib/location-search"
import type { MetaphysicsChart } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"

const pad = (value: number) => String(value).padStart(2, "0")
const localDateTimeValue = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
const TIMEZONES = ["Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore", "Asia/Tokyo", "America/Los_Angeles", "America/New_York", "Europe/London"]
const IZTRO_MIN_DATE = "1900-01-31"
const IZTRO_MAX_DATE = "2100-12-31"

type ZiweiResultSnapshot = {
  chart: IFunctionalAstrolabe
  horoscope: IFunctionalHoroscope
  horoscopeDate: string
  generatedAt: string
  provenance: ZiweiProvenance
}

type BaziResultSnapshot = {
  chart: MetaphysicsChart
  generatedAt: string
}

type LocationAutofillState = {
  previousTimezone: string
  previousLongitude: string
  appliedTimezone: string
  appliedLongitude: string
}

function isSupportedHoroscopeDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match || value < IZTRO_MIN_DATE || value > IZTRO_MAX_DATE) return false
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

export function MetaphysicsTools() {
  const { locale, toLocalePath } = useI18n()
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai")
  const [currentChart, setCurrentChart] = useState<MetaphysicsChart | null>(null)
  const [currentLoading, setCurrentLoading] = useState(true)
  const [birthTime, setBirthTime] = useState(() => localDateTimeValue(new Date(1990, 0, 1, 12, 0)))
  const [baziCalendar, setBaziCalendar] = useState<"solar" | "lunar">("solar")
  const [lunarBirthDate, setLunarBirthDate] = useState("1990-01-01")
  const [lunarBirthTime, setLunarBirthTime] = useState("12:00")
  const [baziGender, setBaziGender] = useState<"male" | "female">("male")
  const [birthPlace, setBirthPlace] = useState("")
  const [selectedBirthPlace, setSelectedBirthPlace] = useState<LocationResult | null>(null)
  const [locationAutofill, setLocationAutofill] = useState<LocationAutofillState | null>(null)
  const [isLeapMonth, setIsLeapMonth] = useState(false)
  const [hourUncertain, setHourUncertain] = useState(false)
  const [dayunAlgorithm, setDayunAlgorithm] = useState<"sect1" | "sect2">("sect2")
  const [longitude, setLongitude] = useState("")
  const [trueSolar, setTrueSolar] = useState(false)
  const [dayBoundary, setDayBoundary] = useState<"current" | "forward">("forward")
  const [birthResult, setBirthResult] = useState<BaziResultSnapshot | null>(null)
  const [birthLoading, setBirthLoading] = useState(false)
  const [gender, setGender] = useState<"男" | "女">("男")
  const [fixLeap, setFixLeap] = useState(true)
  const [ziweiCalendar, setZiweiCalendar] = useState<"solar" | "lunar">("solar")
  const [ziweiLeapMonth, setZiweiLeapMonth] = useState(false)
  const [ziweiAlgorithm, setZiweiAlgorithm] = useState<"default" | "zhongzhou">("default")
  const [ziweiAstroType, setZiweiAstroType] = useState<"heaven" | "earth" | "human">("heaven")
  const [ziweiYearDivide, setZiweiYearDivide] = useState<"normal" | "exact">("exact")
  const [horoscopeDate, setHoroscopeDate] = useState(() => localDateTimeValue(new Date()).slice(0, 10))
  const [ziweiResult, setZiweiResult] = useState<ZiweiResultSnapshot | null>(null)
  const [ziweiLoading, setZiweiLoading] = useState(false)
  const [ziweiEditorOpen, setZiweiEditorOpen] = useState(true)
  const timezoneOptions = useMemo(() => TIMEZONES.includes(timezone) ? TIMEZONES : [timezone, ...TIMEZONES], [timezone])
  const locationOverrideActive = Boolean(locationAutofill && (
    timezone !== locationAutofill.appliedTimezone || longitude !== locationAutofill.appliedLongitude
  ))

  const copy = locale === "zh" ? {
    title: "八字与紫微排盘",
    subtitle: "输入出生信息生成个人命盘，也可随时查看当前时令。",
    current: "当前时令",
    bazi: "八字排盘",
    ziwei: "紫微斗数",
    basicSettings: "基础出生信息",
    professionalSettings: "专业排盘设置",
    professionalSettingsHint: "这些设置用于明确历法与起运规则；不改变排盘事实与解释层的边界。",
    timezone: "时区",
    birth: "出生时间",
    calendar: "历法",
    solar: "公历",
    lunar: "农历",
    lunarDateFormat: "农历日期（YYYY-MM-DD）",
    leapMonth: "农历闰月",
    birthPlace: "出生地",
    birthPlaceHint: "选择城市后自动填写时区和经度；专业设置中的手动修改仍然优先。",
    hourUncertain: "出生时辰不确定",
    dayunRule: "起运算法",
    dayunRuleHint: "分钟精算按分钟确定起运；传统折算按日数与时辰换算。",
    dayunSect1: "传统折算",
    dayunSect2: "分钟精算",
    longitude: "出生地经度",
    longitudeHint: "选择城市后会自动填写；如需校准，可在这里手动调整。",
    trueSolar: "真太阳时校正（经度与均时差）",
    boundary: "晚子时换日",
    calculate: "生成我的命盘",
    useToCast: "用这个时间起卦",
    gender: "性别",
    male: "男",
    female: "女",
    loadingCurrent: "正在读取当前时令…",
    loadingResult: "正在生成命盘…",
    loadingZiwei: "正在生成紫微星盘…",
    invalidHoroscopeDate: "请输入 1900-01-31 至 2100-12-31 之间的有效运限日期。",
    ziweiBasicSettings: "紫微基础信息",
    ziweiProfessionalSettings: "紫微专业设置",
    editDetails: "修改资料",
    fixLeap: "闰月按前后半月调整",
    school: "安星方法",
    standardSchool: "通行法",
    zhongzhouSchool: "中州派",
    astroType: "星盘类型",
    heaven: "天盘",
    earth: "地盘",
    human: "人盘",
    yearDivide: "年界",
    lunarYear: "农历正月初一",
    exactYear: "立春",
    horoscopeDate: "运限日期",
    chartNote: "历法与星盘数据由确定性算法生成；旺衰、格局与断语因流派而异，应与所采用的规则体系一并核对。",
  } : {
    title: "BaZi & Zi Wei Charts",
    subtitle: "Enter birth details to generate a personal chart, or check the current calendar at a glance.",
    current: "Current Time",
    bazi: "BaZi",
    ziwei: "Zi Wei Dou Shu",
    basicSettings: "Basic birth details",
    professionalSettings: "Professional chart settings",
    professionalSettingsHint: "These settings make calendar and cycle rules explicit without mixing deterministic facts with interpretation.",
    timezone: "Time zone",
    birth: "Birth time",
    calendar: "Calendar",
    solar: "Solar",
    lunar: "Lunar",
    lunarDateFormat: "Lunar date (YYYY-MM-DD)",
    leapMonth: "Leap lunar month",
    birthPlace: "Birth place",
    birthPlaceHint: "Selecting a city fills its time zone and longitude; manual professional settings remain authoritative.",
    hourUncertain: "Birth hour uncertain",
    dayunRule: "Da Yun start rule",
    dayunRuleHint: "Minute-based calculation locates the start by minute; traditional conversion uses day and hour intervals.",
    dayunSect1: "Traditional conversion",
    dayunSect2: "Minute-based calculation",
    longitude: "Birth longitude",
    longitudeHint: "Selecting a city fills this automatically; adjust it here only when needed.",
    trueSolar: "True-solar correction (longitude and equation of time)",
    boundary: "Advance day at late Zi hour",
    calculate: "Generate my chart",
    useToCast: "Use this time to cast",
    gender: "Gender",
    male: "Male",
    female: "Female",
    loadingCurrent: "Loading current calendar…",
    loadingResult: "Generating chart…",
    loadingZiwei: "Generating Zi Wei chart…",
    invalidHoroscopeDate: "Enter a valid horoscope date from 1900-01-31 through 2100-12-31.",
    ziweiBasicSettings: "Zi Wei basic details",
    ziweiProfessionalSettings: "Zi Wei professional settings",
    editDetails: "Edit details",
    fixLeap: "Adjust the two halves of a leap month",
    school: "Star-placement school",
    standardSchool: "Standard",
    zhongzhouSchool: "Zhongzhou",
    astroType: "Chart type",
    heaven: "Heaven",
    earth: "Earth",
    human: "Human",
    yearDivide: "Year boundary",
    lunarYear: "Lunar New Year",
    exactYear: "Start of Spring",
    horoscopeDate: "Horoscope date",
    chartNote: "Calendar and chart facts are deterministic; strength, pattern, and interpretation rules vary by school and should be reviewed with the selected method.",
  }

  useEffect(() => {
    let cancelled = false
    let timer: number | undefined
    const load = async () => {
      setCurrentLoading(true)
      try {
        const chart = await calculateMetaphysicsChart({ timestamp: new Date().toISOString(), timezone, day_boundary: "forward" })
        if (!cancelled) setCurrentChart(chart)
      } catch (error) {
        if (!cancelled) toast.error((error as Error).message)
      } finally {
        if (!cancelled) {
          setCurrentLoading(false)
          timer = window.setTimeout(() => { void load() }, 60_000)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [timezone])

  const castHref = useMemo(() => {
    if (!currentChart?.calculation_timestamp) return toLocalePath("/app")
    return `${toLocalePath("/app")}?timestamp=${encodeURIComponent(currentChart.calculation_timestamp)}`
  }, [currentChart?.calculation_timestamp, toLocalePath])

  function handleBirthPlaceSelect(location: LocationResult) {
    const appliedLongitude = String(location.longitude)
    setLocationAutofill({
      previousTimezone: timezone,
      previousLongitude: longitude,
      appliedTimezone: location.timezone,
      appliedLongitude,
    })
    setBirthPlace([location.name, location.region, location.country].filter(Boolean).join(", "))
    setTimezone(location.timezone)
    setLongitude(String(location.longitude))
    setSelectedBirthPlace(location)
  }

  function handleBirthPlaceClear() {
    if (locationAutofill) {
      if (timezone === locationAutofill.appliedTimezone) setTimezone(locationAutofill.previousTimezone)
      if (longitude === locationAutofill.appliedLongitude) setLongitude(locationAutofill.previousLongitude)
    }
    setBirthPlace("")
    setSelectedBirthPlace(null)
    setLocationAutofill(null)
  }

  async function generateBazi() {
    if (baziCalendar === "solar" && (!birthTime || Number.isNaN(new Date(birthTime).getTime()))) {
      toast.error(locale === "zh" ? "请输入有效出生时间。" : "Enter a valid birth time.")
      return
    }
    if (trueSolar && !longitude) {
      toast.error(locale === "zh" ? "使用真太阳时必须填写出生地经度。" : "Longitude is required for true-solar correction.")
      return
    }
    const lunarMatch = lunarBirthDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
    const lunarTimeMatch = lunarBirthTime.match(/^(\d{1,2}):(\d{2})$/)
    if (baziCalendar === "lunar" && (!lunarMatch || !lunarTimeMatch)) {
      toast.error(locale === "zh" ? "农历日期请使用 YYYY-MM-DD，时间请使用 HH:mm。" : "Use YYYY-MM-DD for the lunar date and HH:mm for time.")
      return
    }
    setBirthLoading(true)
    try {
      const chart = await calculateMetaphysicsChart({
        timestamp: baziCalendar === "solar" ? birthTime : `${lunarBirthDate}T${hourUncertain ? "12:00" : lunarBirthTime}`,
        timezone,
        longitude: longitude ? Number(longitude) : null,
        use_true_solar_time: trueSolar,
        day_boundary: dayBoundary,
        calendar_type: baziCalendar,
        is_leap_month: baziCalendar === "lunar" && isLeapMonth,
        gender: baziGender,
        birth_place: birthPlace || null,
        hour_uncertain: hourUncertain,
        dayun_algorithm: dayunAlgorithm,
        lunar_year: lunarMatch ? Number(lunarMatch[1]) : null,
        lunar_month: lunarMatch ? Number(lunarMatch[2]) : null,
        lunar_day: lunarMatch ? Number(lunarMatch[3]) : null,
        lunar_hour: lunarTimeMatch ? (hourUncertain ? 12 : Number(lunarTimeMatch[1])) : null,
        lunar_minute: lunarTimeMatch ? (hourUncertain ? 0 : Number(lunarTimeMatch[2])) : null,
      })
      setBirthResult({ chart, generatedAt: new Date().toISOString() })
    } catch (error) {
      toast.error((error as Error).message)
    } finally {
      setBirthLoading(false)
    }
  }

  async function generateZiwei() {
    if (ziweiCalendar === "solar" && (!birthTime || Number.isNaN(new Date(birthTime).getTime()))) {
      toast.error(locale === "zh" ? "请输入有效出生时间。" : "Enter a valid birth time.")
      return
    }
    if (!isSupportedHoroscopeDate(horoscopeDate)) {
      toast.error(copy.invalidHoroscopeDate)
      return
    }
    const lunarDateMatch = lunarBirthDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
    const selectedTime = ziweiCalendar === "lunar" ? lunarBirthTime : birthTime.slice(11, 16)
    const timeMatch = selectedTime.match(/^(\d{1,2}):(\d{2})$/)
    if (ziweiCalendar === "lunar" && (!lunarDateMatch || !timeMatch)) {
      toast.error(locale === "zh" ? "农历日期请使用 YYYY-MM-DD，时间请使用 HH:mm。" : "Use YYYY-MM-DD for the lunar date and HH:mm for time.")
      return
    }
    const provenance: ZiweiProvenance = {
      algorithm: ziweiAlgorithm,
      astroType: ziweiAlgorithm === "zhongzhou" ? ziweiAstroType : "heaven",
      yearDivide: ziweiYearDivide,
      dayBoundary,
      calendar: ziweiCalendar,
      fixLeap,
      isLeapMonth: ziweiCalendar === "lunar" && ziweiLeapMonth,
    }
    setZiweiLoading(true)
    try {
      const { astro } = await import("iztro")
      const hour = timeMatch ? Number(timeMatch[1]) : new Date(birthTime).getHours()
      const timeIndex = hour === 23 ? 12 : Math.floor((hour + 1) / 2)
      const chart = astro.withOptions({
        type: ziweiCalendar,
        dateStr: ziweiCalendar === "lunar" ? lunarBirthDate : birthTime.slice(0, 10),
        timeIndex,
        gender,
        isLeapMonth: ziweiCalendar === "lunar" && ziweiLeapMonth,
        fixLeap,
        language: locale === "zh" ? "zh-CN" : "en-US",
        config: {
          algorithm: ziweiAlgorithm,
          dayDivide: dayBoundary,
          yearDivide: ziweiYearDivide,
          horoscopeDivide: ziweiYearDivide,
        },
        astroType: provenance.astroType,
      })
      const horoscope = chart.horoscope(horoscopeDate)
      setZiweiResult({
        chart,
        horoscope,
        horoscopeDate,
        generatedAt: new Date().toISOString(),
        provenance,
      })
      setZiweiEditorOpen(false)
    } catch (error) {
      toast.error((error as Error).message || (locale === "zh" ? "紫微排盘内核加载失败。" : "Zi Wei engine failed to load."))
    } finally {
      setZiweiLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-[92rem] space-y-6">
      <header className="border-b border-border/60 pb-5">
        <p className="kicker">{locale === "zh" ? "命理排盘" : "Personal charts"}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">{copy.subtitle}</p>
        <p className="mt-3 max-w-3xl text-xs leading-5 text-muted-foreground">{copy.chartNote}</p>
      </header>

      <Tabs defaultValue="current">
        <TabsList className="grid w-full grid-cols-3"><TabsTrigger value="current"><CalendarClock className="mr-2 size-4" />{copy.current}</TabsTrigger><TabsTrigger value="bazi"><Compass className="mr-2 size-4" />{copy.bazi}</TabsTrigger><TabsTrigger value="ziwei"><Sparkles className="mr-2 size-4" />{copy.ziwei}</TabsTrigger></TabsList>
        <TabsContent value="current" className="mt-4 space-y-4">
          <div aria-live="polite" aria-busy={currentLoading}>
            {currentLoading && !currentChart ? <Loading locale={locale} label={copy.loadingCurrent} /> : currentChart ? <BaziChartView chart={currentChart} locale={locale} mode="current" /> : null}
          </div>
          <Button asChild><Link href={castHref}>{copy.useToCast}</Link></Button>
        </TabsContent>
        <TabsContent value="bazi" className="mt-4 space-y-4">
          <BaziControls copy={copy} locale={locale} birthTime={birthTime} setBirthTime={setBirthTime} lunarBirthDate={lunarBirthDate} setLunarBirthDate={setLunarBirthDate} lunarBirthTime={lunarBirthTime} setLunarBirthTime={setLunarBirthTime} timezone={timezone} setTimezone={setTimezone} timezoneOptions={timezoneOptions} longitude={longitude} setLongitude={setLongitude} trueSolar={trueSolar} setTrueSolar={setTrueSolar} dayBoundary={dayBoundary} setDayBoundary={setDayBoundary} calendar={baziCalendar} setCalendar={setBaziCalendar} gender={baziGender} setGender={setBaziGender} selectedLocation={selectedBirthPlace} birthPlaceOverrideActive={locationOverrideActive} effectiveTimezone={timezone} effectiveLongitude={longitude} onBirthPlaceSelect={handleBirthPlaceSelect} onBirthPlaceClear={handleBirthPlaceClear} isLeapMonth={isLeapMonth} setIsLeapMonth={setIsLeapMonth} hourUncertain={hourUncertain} setHourUncertain={setHourUncertain} dayunAlgorithm={dayunAlgorithm} setDayunAlgorithm={setDayunAlgorithm} />
          <Button onClick={generateBazi} disabled={birthLoading}>{birthLoading ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : null}{copy.calculate}</Button>
          <div aria-live="polite" aria-busy={birthLoading}>
            {birthLoading && !birthResult ? <Loading locale={locale} label={copy.loadingResult} /> : birthResult ? <BaziChartView chart={birthResult.chart} generatedAt={birthResult.generatedAt} locale={locale} mode="birth" /> : null}
          </div>
        </TabsContent>
        <TabsContent value="ziwei" className="mt-4 space-y-4">
          {ziweiResult ? <ZiweiChartView chart={ziweiResult.chart} horoscope={ziweiResult.horoscope} horoscopeDate={ziweiResult.horoscopeDate} generatedAt={ziweiResult.generatedAt} locale={locale} provenance={ziweiResult.provenance} /> : null}
          <details id="ziwei-edit-details" data-export-exclude open={ziweiEditorOpen} onToggle={(event) => setZiweiEditorOpen(event.currentTarget.open)} className="border-t border-border/60 pt-4">
            <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{ziweiResult ? copy.editDetails : copy.ziweiBasicSettings}</summary>
            <div className="mt-4 space-y-4">
          <section aria-labelledby="ziwei-basic-title">
            <h2 id="ziwei-basic-title" className="text-sm font-semibold">{copy.ziweiBasicSettings}</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <label id="ziwei-calendar-label" className="text-sm font-medium">{copy.calendar}</label>
                <Select value={ziweiCalendar} onValueChange={(value) => setZiweiCalendar(value as "solar" | "lunar")}>
                  <SelectTrigger id="ziwei-calendar" aria-labelledby="ziwei-calendar-label"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="solar">{copy.solar}</SelectItem><SelectItem value="lunar">{copy.lunar}</SelectItem></SelectContent>
                </Select>
              </div>
              {ziweiCalendar === "solar" ? (
                <div className="space-y-2"><label htmlFor="ziwei-birth-time" className="text-sm font-medium">{copy.birth}</label><Input id="ziwei-birth-time" type="datetime-local" value={birthTime} onChange={(event) => setBirthTime(event.target.value)} /></div>
              ) : (
                <div className="grid gap-2 sm:grid-cols-[1fr_8rem] lg:col-span-2">
                  <div className="space-y-2"><label htmlFor="ziwei-lunar-date" className="text-sm font-medium">{copy.lunarDateFormat}</label><Input id="ziwei-lunar-date" value={lunarBirthDate} inputMode="numeric" placeholder="1990-01-01" onChange={(event) => setLunarBirthDate(event.target.value)} /></div>
                  <div className="space-y-2"><label htmlFor="ziwei-lunar-time" className="text-sm font-medium">{copy.birth}</label><Input id="ziwei-lunar-time" type="time" value={lunarBirthTime} onChange={(event) => setLunarBirthTime(event.target.value)} /></div>
                </div>
              )}
              <div className="space-y-2">
                <label id="ziwei-gender-label" className="text-sm font-medium">{copy.gender}</label>
                <Select value={gender} onValueChange={(value) => setGender(value as "男" | "女")}>
                  <SelectTrigger id="ziwei-gender" aria-labelledby="ziwei-gender-label"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="男">{locale === "zh" ? "男" : "Male"}</SelectItem><SelectItem value="女">{locale === "zh" ? "女" : "Female"}</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><label htmlFor="ziwei-horoscope-date" className="text-sm font-medium">{copy.horoscopeDate}</label><Input id="ziwei-horoscope-date" type="date" value={horoscopeDate} onChange={(event) => setHoroscopeDate(event.target.value)} /></div>
            </div>
          </section>

          <details className="rounded-lg border border-border/60 bg-surface px-4 py-3">
            <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{copy.ziweiProfessionalSettings}</summary>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <label id="ziwei-school-label" className="text-sm font-medium">{copy.school}</label>
                <Select value={ziweiAlgorithm} onValueChange={(value) => setZiweiAlgorithm(value as "default" | "zhongzhou")}>
                  <SelectTrigger id="ziwei-school" aria-labelledby="ziwei-school-label"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="default">{copy.standardSchool}</SelectItem><SelectItem value="zhongzhou">{copy.zhongzhouSchool}</SelectItem></SelectContent>
                </Select>
              </div>
              {ziweiAlgorithm === "zhongzhou" ? (
                <div className="space-y-2">
                  <label id="ziwei-astro-type-label" className="text-sm font-medium">{copy.astroType}</label>
                  <Select value={ziweiAstroType} onValueChange={(value) => setZiweiAstroType(value as "heaven" | "earth" | "human")}>
                    <SelectTrigger id="ziwei-astro-type" aria-labelledby="ziwei-astro-type-label"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="heaven">{copy.heaven}</SelectItem><SelectItem value="earth">{copy.earth}</SelectItem><SelectItem value="human">{copy.human}</SelectItem></SelectContent>
                  </Select>
                </div>
              ) : null}
              <div className="space-y-2">
                <label id="ziwei-year-boundary-label" className="text-sm font-medium">{copy.yearDivide}</label>
                <Select value={ziweiYearDivide} onValueChange={(value) => setZiweiYearDivide(value as "normal" | "exact")}>
                  <SelectTrigger id="ziwei-year-boundary" aria-labelledby="ziwei-year-boundary-label"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="exact">{copy.exactYear}</SelectItem><SelectItem value="normal">{copy.lunarYear}</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><label id="ziwei-fix-leap-label" htmlFor="ziwei-fix-leap" className="text-sm">{copy.fixLeap}</label><Switch id="ziwei-fix-leap" aria-labelledby="ziwei-fix-leap-label" checked={fixLeap} onCheckedChange={setFixLeap} /></div>
              {ziweiCalendar === "lunar" ? <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><label id="ziwei-leap-month-label" htmlFor="ziwei-leap-month" className="text-sm">{copy.leapMonth}</label><Switch id="ziwei-leap-month" aria-labelledby="ziwei-leap-month-label" checked={ziweiLeapMonth} onCheckedChange={setZiweiLeapMonth} /></div> : null}
              <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><label id="ziwei-day-boundary-label" htmlFor="ziwei-day-boundary" className="text-sm">{copy.boundary}</label><Switch id="ziwei-day-boundary" aria-labelledby="ziwei-day-boundary-label" checked={dayBoundary === "forward"} onCheckedChange={(checked) => setDayBoundary(checked ? "forward" : "current")} /></div>
            </div>
          </details>

          <Button onClick={generateZiwei} disabled={ziweiLoading}>{ziweiLoading ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : null}{copy.calculate}</Button>
            </div>
          </details>
          <div aria-live="polite" aria-busy={ziweiLoading}>
            {ziweiLoading ? <Loading locale={locale} label={copy.loadingZiwei} /> : null}
          </div>
        </TabsContent>
      </Tabs>
    </main>
  )
}

function Loading({ locale, label }: { locale: "en" | "zh"; label: string }) { return <div role="status" aria-live="polite" className="flex items-center justify-center gap-2 rounded-lg border border-border/60 bg-surface p-10 text-sm text-muted-foreground"><Loader2 aria-hidden="true" className="size-4 animate-spin" />{label || (locale === "zh" ? "正在加载…" : "Loading…")}</div> }
