"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useMemo, useRef, useState } from "react"
import { CalendarClock, Check, Cloud, Compass, Loader2, Pencil, Plus, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useI18n } from "@/components/providers/i18n-provider"
import { BirthPlaceField } from "@/components/tools/birth-place-field"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BaziChartView } from "@/components/tools/bazi-chart-view"
import { BaziControls } from "@/components/tools/metaphysics-controls"
import { ZiweiChartView, type ZiweiArchiveMode, type ZiweiProvenance, type ZiweiStatisticsStatus } from "@/components/tools/ziwei-chart-view"
import { calculateMetaphysicsChart, fetchMetaphysicsChart, fetchMetaphysicsStatistics, saveMetaphysicsChart } from "@/lib/api"
import type { LocationResult } from "@/lib/location-search"
import { ZIWEI_BASELINE_ID, ziweiFeatureIds } from "@/lib/ziwei-statistics"
import type { MetaphysicsChart, MetaphysicsChartRecord, MetaphysicsChartSavePayload, MetaphysicsStatistics } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"

const pad = (value: number) => String(value).padStart(2, "0")
const localDateTimeValue = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
const IZTRO_MIN_DATE = "1900-01-31"
const IZTRO_MAX_DATE = "2100-12-31"
const TIMEZONES = ["Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore", "Asia/Tokyo", "America/Los_Angeles", "America/New_York", "Europe/London"]
const ZIWEI_STANDARD_CONFIG_ID = "ziwei-standard-v1"
const METAPHYSICS_WORKSPACE_KEY = "iching-metaphysics-workspace-v1"

const STANDARD_ZIWEI_RULES = {
  algorithm: "default",
  astroType: "heaven",
  yearDivide: "exact",
  dayBoundary: "forward",
  fixLeap: true,
} as const

type ZiweiNormalizedInput = {
  calendar: "solar" | "lunar"
  date: string
  time: string
  gender: "男" | "女"
  isLeapMonth: boolean
  horoscopeDate: string
}

type ZiweiResultSnapshot = {
  chart: IFunctionalAstrolabe
  horoscope: IFunctionalHoroscope
  horoscopeDate: string
  generatedAt: string
  provenance: ZiweiProvenance
  subjectName: string
  statistics: MetaphysicsStatistics | null
  statisticsStatus: ZiweiStatisticsStatus
  statisticsError?: string
  archiveMode: ZiweiArchiveMode
  normalizedInput?: ZiweiNormalizedInput
}

type BaziResultSnapshot = {
  chart: MetaphysicsChart
  generatedAt: string
  subjectName: string
}

type PersistedChartForm = {
  subjectName: string
  timezone: string
  birthTime: string
  baziCalendar: "solar" | "lunar"
  lunarBirthDate: string
  lunarBirthTime: string
  baziGender: "male" | "female"
  gender: "男" | "女"
  birthPlace: string
  selectedBirthPlace: LocationResult | null
  isLeapMonth: boolean
  ziweiCalendar: "solar" | "lunar"
  ziweiLeapMonth: boolean
  longitude: string
  baziTrueSolar: boolean
  baziDayBoundary: "current" | "forward"
  baziHourUncertain: boolean
  baziFoldChoice: "first" | "second" | null
  dayunAlgorithm: "sect1" | "sect2"
  horoscopeDate: string
}

type PersistedMetaphysicsWorkspace = {
  version: 1
  bazi?: {
    result: BaziResultSnapshot
    form: PersistedChartForm
    chartId: string | null
    subjectId: string | null
  }
  ziwei?: {
    normalizedInput: ZiweiNormalizedInput
    generatedAt: string
    subjectName: string
    form: PersistedChartForm
    chartId: string | null
    subjectId: string | null
  }
}

type LocationAutofillState = {
  previousTimezone: string
  previousLongitude: string
  appliedTimezone: string
  appliedLongitude: string
}

function readPersistedWorkspace(): PersistedMetaphysicsWorkspace {
  if (typeof window === "undefined") return { version: 1 }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(METAPHYSICS_WORKSPACE_KEY) ?? "null") as PersistedMetaphysicsWorkspace | null
    return parsed?.version === 1 ? parsed : { version: 1 }
  } catch {
    return { version: 1 }
  }
}

function updatePersistedWorkspace(
  type: "bazi" | "ziwei",
  value: PersistedMetaphysicsWorkspace["bazi"] | PersistedMetaphysicsWorkspace["ziwei"] | null,
) {
  if (typeof window === "undefined") return
  try {
    const workspace = readPersistedWorkspace()
    if (value) workspace[type] = value as never
    else delete workspace[type]
    if (!workspace.bazi && !workspace.ziwei) window.localStorage.removeItem(METAPHYSICS_WORKSPACE_KEY)
    else window.localStorage.setItem(METAPHYSICS_WORKSPACE_KEY, JSON.stringify(workspace))
  } catch {
    // Private browser modes and storage quotas must never block charting.
  }
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

function normalizeCalendarDate(value: string) {
  const match = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(value)
  if (!match) return null
  const month = Number(match[2])
  const day = Number(match[3])
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  return `${match[1]}-${pad(month)}-${pad(day)}`
}

function normalizeExactTime(value: string) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value)
  if (!match) return null
  const hour = Number(match[1])
  const minute = Number(match[2])
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null
  return `${pad(hour)}:${pad(minute)}`
}

function timeIndexFor(time: string) {
  const hour = Number(time.slice(0, 2))
  return hour === 23 ? 12 : Math.floor((hour + 1) / 2)
}

function standardZiweiProvenance(input: Pick<ZiweiNormalizedInput, "calendar" | "isLeapMonth">): ZiweiProvenance {
  return {
    configId: ZIWEI_STANDARD_CONFIG_ID,
    ...STANDARD_ZIWEI_RULES,
    calendar: input.calendar,
    isLeapMonth: input.calendar === "lunar" && input.isLeapMonth,
  }
}

function isStandardZiweiProvenance(provenance?: ZiweiProvenance) {
  return Boolean(
    provenance
    && provenance.algorithm === STANDARD_ZIWEI_RULES.algorithm
    && provenance.astroType === STANDARD_ZIWEI_RULES.astroType
    && provenance.yearDivide === STANDARD_ZIWEI_RULES.yearDivide
    && provenance.dayBoundary === STANDARD_ZIWEI_RULES.dayBoundary
    && provenance.fixLeap === STANDARD_ZIWEI_RULES.fixLeap,
  )
}

function normalizedZiweiInputFromRecord(record: MetaphysicsChartRecord, form: Record<string, unknown>, fallbackHoroscopeDate: string) {
  const stored = record.input_snapshot.normalized_ziwei
  const storedInput = stored && typeof stored === "object" ? stored as Record<string, unknown> : null
  const calendarValue = storedInput?.calendar ?? form.ziwei_calendar ?? record.subject.calendar_type
  const calendar = calendarValue === "lunar" ? "lunar" : calendarValue === "solar" ? "solar" : null
  if (!calendar) return null

  const subjectTimestamp = record.subject.birth_local_timestamp || ""
  const legacySolarBirth = typeof form.birth_time === "string" ? form.birth_time : subjectTimestamp
  const rawDate = storedInput?.date ?? (calendar === "lunar" ? form.lunar_birth_date : legacySolarBirth.slice(0, 10)) ?? subjectTimestamp.slice(0, 10)
  const rawTime = storedInput?.time ?? (calendar === "lunar" ? form.lunar_birth_time : typeof form.birth_time === "string" ? form.birth_time.slice(11, 16) : null) ?? subjectTimestamp.slice(11, 16)
  const date = typeof rawDate === "string" ? normalizeCalendarDate(rawDate) : null
  const time = typeof rawTime === "string" ? normalizeExactTime(rawTime) : null
  const horoscopeDateValue = storedInput?.horoscopeDate ?? form.horoscope_date ?? fallbackHoroscopeDate
  const normalizedHoroscopeDate = typeof horoscopeDateValue === "string" && isSupportedHoroscopeDate(horoscopeDateValue) ? horoscopeDateValue : null
  if (!date || !time || !normalizedHoroscopeDate) return null

  const genderValue = storedInput?.gender
  const gender = genderValue === "女" || record.subject.gender === "female" ? "女" : "男"
  const isLeapMonth = typeof storedInput?.isLeapMonth === "boolean" ? storedInput.isLeapMonth : form.ziwei_leap_month === true
  return { calendar, date, time, gender, isLeapMonth, horoscopeDate: normalizedHoroscopeDate } satisfies ZiweiNormalizedInput
}

async function instantiateStandardZiwei(input: ZiweiNormalizedInput, locale: "en" | "zh") {
  const { astro } = await import("iztro")
  const options = {
    type: input.calendar,
    dateStr: input.date,
    timeIndex: timeIndexFor(input.time),
    gender: input.gender,
    isLeapMonth: input.calendar === "lunar" && input.isLeapMonth,
    fixLeap: STANDARD_ZIWEI_RULES.fixLeap,
    config: {
      algorithm: STANDARD_ZIWEI_RULES.algorithm,
      dayDivide: STANDARD_ZIWEI_RULES.dayBoundary,
      yearDivide: STANDARD_ZIWEI_RULES.yearDivide,
      horoscopeDivide: STANDARD_ZIWEI_RULES.yearDivide,
    },
    astroType: STANDARD_ZIWEI_RULES.astroType,
  } as const
  const chart = astro.withOptions({ ...options, language: locale === "zh" ? "zh-CN" : "en-US" })
  const statisticsChart = locale === "zh" ? chart : astro.withOptions({ ...options, language: "zh-CN" })
  return { chart, horoscope: chart.horoscope(input.horoscopeDate), statisticsChart }
}

export function MetaphysicsTools() {
  const { locale, toLocalePath } = useI18n()
  const auth = useAuthContext()
  const router = useRouter()
  const loadedChartRef = useRef<string | null>(null)
  const [activeTab, setActiveTab] = useState<"current" | "bazi" | "ziwei">("current")
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai")
  const [currentChart, setCurrentChart] = useState<MetaphysicsChart | null>(null)
  const [currentLoading, setCurrentLoading] = useState(true)
  const [birthTime, setBirthTime] = useState(() => localDateTimeValue(new Date(1990, 0, 1, 12, 0)))
  const [baziSubjectName, setBaziSubjectName] = useState("")
  const [baziCalendar, setBaziCalendar] = useState<"solar" | "lunar">("solar")
  const [lunarBirthDate, setLunarBirthDate] = useState("1990-01-01")
  const [lunarBirthTime, setLunarBirthTime] = useState("12:00")
  const [baziGender, setBaziGender] = useState<"male" | "female">("male")
  const [birthPlace, setBirthPlace] = useState("")
  const [selectedBirthPlace, setSelectedBirthPlace] = useState<LocationResult | null>(null)
  const [locationAutofill, setLocationAutofill] = useState<LocationAutofillState | null>(null)
  const [isLeapMonth, setIsLeapMonth] = useState(false)
  const [longitude, setLongitude] = useState("")
  const [baziTrueSolar, setBaziTrueSolar] = useState(false)
  const [baziDayBoundary, setBaziDayBoundary] = useState<"current" | "forward">("forward")
  const [baziHourUncertain, setBaziHourUncertain] = useState(false)
  const [baziFoldChoice, setBaziFoldChoice] = useState<"first" | "second" | null>(null)
  const [baziAmbiguousTime, setBaziAmbiguousTime] = useState(false)
  const [dayunAlgorithm, setDayunAlgorithm] = useState<"sect1" | "sect2">("sect2")
  const [birthResult, setBirthResult] = useState<BaziResultSnapshot | null>(null)
  const [incompleteBaziRecord, setIncompleteBaziRecord] = useState<{ subjectName: string; birthTimestamp: string } | null>(null)
  const [birthLoading, setBirthLoading] = useState(false)
  const [baziEditorOpen, setBaziEditorOpen] = useState(true)
  const [gender, setGender] = useState<"男" | "女">("男")
  const [ziweiCalendar, setZiweiCalendar] = useState<"solar" | "lunar">("solar")
  const [ziweiLeapMonth, setZiweiLeapMonth] = useState(false)
  const [horoscopeDate, setHoroscopeDate] = useState(() => localDateTimeValue(new Date()).slice(0, 10))
  const [ziweiResult, setZiweiResult] = useState<ZiweiResultSnapshot | null>(null)
  const [ziweiLoading, setZiweiLoading] = useState(false)
  const [ziweiEditorOpen, setZiweiEditorOpen] = useState(true)
  const [activeBaziSubjectId, setActiveBaziSubjectId] = useState<string | null>(null)
  const [activeZiweiSubjectId, setActiveZiweiSubjectId] = useState<string | null>(null)
  const [activeBaziChartId, setActiveBaziChartId] = useState<string | null>(null)
  const [activeZiweiChartId, setActiveZiweiChartId] = useState<string | null>(null)
  const [savingType, setSavingType] = useState<"bazi" | "ziwei" | null>(null)
  const [ziweiPeriodSavePending, setZiweiPeriodSavePending] = useState(false)
  const [ziweiPeriodSaveError, setZiweiPeriodSaveError] = useState(false)
  const ziweiPeriodSaveVersionRef = useRef(0)
  const ziweiPeriodSaveQueueRef = useRef<Promise<void>>(Promise.resolve())
  const timezoneOptions = useMemo(() => TIMEZONES.includes(timezone) ? TIMEZONES : [timezone, ...TIMEZONES], [timezone])
  const locationOverrideActive = Boolean(locationAutofill && (
    timezone !== locationAutofill.appliedTimezone || longitude !== locationAutofill.appliedLongitude
  ))

  const copy = locale === "zh" ? {
    subjectName: "命主称呼",
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
    chartNote: "按出生地时间与精确节气排盘，并结合传统命理规则与历法统计进行分析。",
    newChart: "新建命盘",
    savedCloud: "已自动保存到我的档案",
    savingCloud: "正在保存…",
    loginToSave: "登录后自动保存并可随时打开",
    saveFailed: "命盘已生成，但云端保存失败，请稍后重试。",
    loadedChart: "已打开私人命盘档案。",
    exactTimeRequired: "准确时间可看到完整四柱与运限；时间不确定时也可先查看稳定结构。",
    standardRules: "统一排盘规则",
    standardRulesBody: "通行法 · 天盘 · 立春年界及运限年界 · 晚子时换日 · 闰月修正开启",
  } : {
    subjectName: "Chart name",
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
    chartNote: "Calculated from local birth time and exact solar terms, then interpreted with traditional rules and calendar statistics.",
    newChart: "New chart",
    savedCloud: "Automatically saved to My Charts",
    savingCloud: "Saving…",
    loginToSave: "Sign in to save and reopen this chart",
    saveFailed: "The chart was generated, but cloud saving failed. Try again later.",
    loadedChart: "Private chart opened.",
    exactTimeRequired: "An exact time unlocks the full chart and periods; uncertain times can still show stable structures.",
    standardRules: "Standard chart rules",
    standardRulesBody: "Standard algorithm · Heaven chart · Start-of-Spring year and horoscope boundaries · late Zi advances the day · leap-month adjustment on",
  }

  function persistedForm(): PersistedChartForm {
    return {
      subjectName: baziSubjectName,
      timezone,
      birthTime,
      baziCalendar,
      lunarBirthDate,
      lunarBirthTime,
      baziGender,
      gender,
      birthPlace,
      selectedBirthPlace,
      isLeapMonth,
      ziweiCalendar,
      ziweiLeapMonth,
      longitude,
      baziTrueSolar,
      baziDayBoundary,
      baziHourUncertain,
      baziFoldChoice,
      dayunAlgorithm,
      horoscopeDate,
    }
  }

  function applyPersistedForm(form: PersistedChartForm) {
    setBaziSubjectName(form.subjectName)
    setTimezone(form.timezone)
    setBirthTime(form.birthTime)
    setBaziCalendar(form.baziCalendar)
    setLunarBirthDate(form.lunarBirthDate)
    setLunarBirthTime(form.lunarBirthTime)
    setBaziGender(form.baziGender)
    setGender(form.gender)
    setBirthPlace(form.birthPlace)
    setSelectedBirthPlace(form.selectedBirthPlace)
    setIsLeapMonth(form.isLeapMonth)
    setZiweiCalendar(form.ziweiCalendar)
    setZiweiLeapMonth(form.ziweiLeapMonth)
    setLongitude(form.longitude)
    setBaziTrueSolar(form.baziTrueSolar)
    setBaziDayBoundary(form.baziDayBoundary)
    setBaziHourUncertain(form.baziHourUncertain ?? false)
    setBaziFoldChoice(form.baziFoldChoice ?? null)
    setDayunAlgorithm(form.dayunAlgorithm)
    setHoroscopeDate(form.horoscopeDate)
    setLocationAutofill(null)
  }

  function persistBaziWorkspace(result: BaziResultSnapshot, chartId = activeBaziChartId, subjectId = activeBaziSubjectId) {
    updatePersistedWorkspace("bazi", { result, form: persistedForm(), chartId, subjectId })
  }

  function persistZiweiWorkspace(
    normalizedInput: ZiweiNormalizedInput,
    generatedAt: string,
    subjectName: string,
    chartId = activeZiweiChartId,
    subjectId = activeZiweiSubjectId,
  ) {
    updatePersistedWorkspace("ziwei", { normalizedInput, generatedAt, subjectName, form: persistedForm(), chartId, subjectId })
  }

  useEffect(() => {
    if (typeof window === "undefined" || new URLSearchParams(window.location.search).has("chart")) return
    const workspace = readPersistedWorkspace()
    const savedBazi = workspace.bazi
    if (savedBazi && (savedBazi.result?.chart?.derived_schema_version ?? 0) >= 3) {
      setBirthResult(savedBazi.result)
      setActiveBaziChartId(savedBazi.chartId)
      setActiveBaziSubjectId(savedBazi.subjectId)
      setBaziEditorOpen(false)
    }
    if (workspace.ziwei?.normalizedInput) {
      const saved = workspace.ziwei
      setActiveZiweiChartId(saved.chartId)
      setActiveZiweiSubjectId(saved.subjectId)
      setZiweiEditorOpen(false)
      void instantiateStandardZiwei(saved.normalizedInput, locale).then(({ chart, horoscope, statisticsChart }) => {
        setZiweiResult({
          chart,
          horoscope,
          horoscopeDate: saved.normalizedInput.horoscopeDate,
          generatedAt: saved.generatedAt,
          provenance: standardZiweiProvenance(saved.normalizedInput),
          subjectName: saved.subjectName,
          statistics: null,
          statisticsStatus: "loading",
          archiveMode: "standard",
          normalizedInput: saved.normalizedInput,
        })
        requestZiweiStatistics(statisticsChart, saved.generatedAt)
      }).catch(() => {
        updatePersistedWorkspace("ziwei", null)
      })
    }
    const requestedTab = new URLSearchParams(window.location.search).get("tab")
    const selected = requestedTab === "ziwei" ? workspace.ziwei : requestedTab === "bazi" ? workspace.bazi : null
    if (selected?.form) applyPersistedForm(selected.form)
  // Restore once per page load. Locale-specific Zi Wei reconstruction is intentionally fixed to the mounted locale.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

  useEffect(() => {
    if (typeof window === "undefined") return
    const params = new URLSearchParams(window.location.search)
    const requestedTab = params.get("tab")
    if (requestedTab === "bazi" || requestedTab === "ziwei" || requestedTab === "current") {
      setActiveTab(requestedTab)
    }
    const chartId = params.get("chart")
    if (!chartId || auth.loading || loadedChartRef.current === chartId) return
    if (!auth.accessToken) {
      toast.info(copy.loginToSave)
      return
    }
    loadedChartRef.current = chartId
    void fetchMetaphysicsChart(chartId, auth.accessToken)
      .then(async (record) => {
        await hydrateSavedChart(record)
        toast.success(copy.loadedChart)
      })
      .catch((error) => {
        loadedChartRef.current = null
        toast.error((error as Error).message)
      })
  // `copy` and the hydrator are intentionally omitted so a locale render cannot refetch the same record.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.accessToken, auth.loading])

  const castHref = useMemo(() => {
    if (!currentChart?.calculation_timestamp) return toLocalePath("/app")
    return `${toLocalePath("/app")}?timestamp=${encodeURIComponent(currentChart.calculation_timestamp)}`
  }, [currentChart?.calculation_timestamp, toLocalePath])

  function requestZiweiStatistics(statisticsChart: IFunctionalAstrolabe, generatedAt: string) {
    void fetchMetaphysicsStatistics({
      chart_type: "ziwei",
      baseline_id: ZIWEI_BASELINE_ID,
      feature_ids: ziweiFeatureIds(statisticsChart),
    }).then((statistics) => {
      if (statistics.status && statistics.status !== "available") {
        setZiweiResult((current) => current?.generatedAt === generatedAt
          ? {
              ...current,
              statistics: null,
              statisticsStatus: "unavailable",
              statisticsError: statistics.unavailable_reason ?? (locale === "zh" ? "当前规则版本没有可用的频率样本。" : "No frequency sample is available for the current rules version."),
            }
          : current)
        return
      }
      setZiweiResult((current) => current?.generatedAt === generatedAt
        ? { ...current, statistics, statisticsStatus: "ready", statisticsError: undefined }
        : current)
    }).catch(() => {
      setZiweiResult((current) => current?.generatedAt === generatedAt
        ? {
            ...current,
            statistics: null,
            statisticsStatus: "unavailable",
            statisticsError: locale === "zh" ? "频率样本暂时不可用，命盘与运限仍可正常查看。" : "Frequency samples are temporarily unavailable. The chart and periods remain available.",
          }
        : current)
    })
  }

  async function hydrateSavedChart(record: MetaphysicsChartRecord) {
    ziweiPeriodSaveVersionRef.current += 1
    setSavingType(null)
    const form = (record.input_snapshot.form ?? {}) as Record<string, unknown>
    const subjectName = record.subject.display_name ?? ""
    setBaziSubjectName(subjectName)
    setTimezone(record.subject.timezone)
    setBirthPlace(record.subject.birth_place ?? "")
    setLongitude(record.subject.longitude == null ? "" : String(record.subject.longitude))
    setBaziCalendar(record.subject.calendar_type)
    setBaziGender(record.subject.gender ?? "male")
    setGender(record.subject.gender === "female" ? "女" : "男")
    if (typeof form.birth_time === "string") setBirthTime(form.birth_time)
    if (typeof form.lunar_birth_date === "string") setLunarBirthDate(form.lunar_birth_date)
    if (typeof form.lunar_birth_time === "string") setLunarBirthTime(form.lunar_birth_time)
    if (typeof form.true_solar === "boolean") setBaziTrueSolar(form.true_solar)
    if (typeof form.hour_uncertain === "boolean") setBaziHourUncertain(form.hour_uncertain)
    if (form.fold_choice === "first" || form.fold_choice === "second") setBaziFoldChoice(form.fold_choice)
    if (form.day_boundary === "current" || form.day_boundary === "forward") setBaziDayBoundary(form.day_boundary)
    if (form.dayun_algorithm === "sect1" || form.dayun_algorithm === "sect2") setDayunAlgorithm(form.dayun_algorithm)
    if (typeof form.is_leap_month === "boolean") setIsLeapMonth(form.is_leap_month)
    if (form.ziwei_calendar === "solar" || form.ziwei_calendar === "lunar") setZiweiCalendar(form.ziwei_calendar)
    if (typeof form.ziwei_leap_month === "boolean") setZiweiLeapMonth(form.ziwei_leap_month)
    if (typeof form.horoscope_date === "string") setHoroscopeDate(form.horoscope_date)
    const restoredForm: PersistedChartForm = {
      ...persistedForm(),
      subjectName,
      timezone: record.subject.timezone,
      birthTime: typeof form.birth_time === "string" ? form.birth_time : record.subject.birth_local_timestamp,
      baziCalendar: record.subject.calendar_type,
      lunarBirthDate: typeof form.lunar_birth_date === "string" ? form.lunar_birth_date : lunarBirthDate,
      lunarBirthTime: typeof form.lunar_birth_time === "string" ? form.lunar_birth_time : lunarBirthTime,
      baziGender: record.subject.gender ?? "male",
      gender: record.subject.gender === "female" ? "女" : "男",
      birthPlace: record.subject.birth_place ?? "",
      isLeapMonth: form.is_leap_month === true,
      ziweiCalendar: form.ziwei_calendar === "lunar" ? "lunar" : "solar",
      ziweiLeapMonth: form.ziwei_leap_month === true,
      longitude: record.subject.longitude == null ? "" : String(record.subject.longitude),
      baziTrueSolar: form.true_solar === true,
      baziDayBoundary: form.day_boundary === "current" ? "current" : "forward",
      baziHourUncertain: form.hour_uncertain === true,
      baziFoldChoice: form.fold_choice === "second" ? "second" : form.fold_choice === "first" ? "first" : null,
      dayunAlgorithm: form.dayun_algorithm === "sect1" ? "sect1" : "sect2",
      horoscopeDate: typeof form.horoscope_date === "string" ? form.horoscope_date : horoscopeDate,
    }
    const savedLocation = form.selected_location
    if (savedLocation && typeof savedLocation === "object") {
      setSelectedBirthPlace(savedLocation as LocationResult)
    } else if (record.subject.latitude != null && record.subject.longitude != null) {
      setSelectedBirthPlace({
        id: record.subject.location_id ?? `saved:${record.subject.id}`,
        name: record.subject.birth_place ?? (subjectName || (locale === "zh" ? "已保存地点" : "Saved place")),
        region: "",
        country: "",
        latitude: record.subject.latitude,
        longitude: record.subject.longitude,
        timezone: record.subject.timezone,
      })
    }

    if (record.chart_type === "bazi") {
      const snapshot = record.result_snapshot as { chart?: MetaphysicsChart; generated_at?: string; subject_name?: string }
      if (!snapshot.chart) throw new Error(locale === "zh" ? "八字命盘快照不完整。" : "The BaZi snapshot is incomplete.")
      let chart = snapshot.chart
      const calculationRequest = record.input_snapshot.calculation_request as Parameters<typeof calculateMetaphysicsChart>[0] | undefined
      if ((chart.derived_schema_version ?? 0) < 4 || !chart.shen_sha || !chart.statistics || !chart.period_layers || !chart.structure || !chart.theme_profiles || (chart.birth_profile?.hour_uncertain && !chart.birth_profile?.stability)) {
        if (!calculationRequest && chart.birth_profile?.hour_uncertain) {
          setBirthResult(null)
          setIncompleteBaziRecord({ subjectName: snapshot.subject_name ?? subjectName, birthTimestamp: record.subject.birth_local_timestamp })
          setActiveBaziSubjectId(record.subject_id)
          setActiveBaziChartId(record.id)
          setBaziEditorOpen(true)
          setActiveTab("bazi")
          return
        }
        if (!calculationRequest) throw new Error(locale === "zh" ? "旧命盘缺少可重算的原始参数。" : "This legacy chart lacks the original calculation inputs.")
        chart = await calculateMetaphysicsChart({ ...calculationRequest, reference_timestamp: new Date().toISOString(), include_period_details: false })
        toast.info(locale === "zh" ? "已按新版规则临时补算；原档案仍保留旧结果，重新保存后升级。" : "Recomputed with the new rules for this view. The stored legacy result remains unchanged until you save again.")
      } else if (calculationRequest) {
        chart = await calculateMetaphysicsChart({ ...calculationRequest, reference_timestamp: new Date().toISOString(), include_period_details: false })
      }
      setBirthResult({ chart, generatedAt: snapshot.generated_at ?? record.updated_at, subjectName: snapshot.subject_name ?? subjectName })
      setIncompleteBaziRecord(null)
      setActiveBaziSubjectId(record.subject_id)
      setActiveBaziChartId(record.id)
      setBaziEditorOpen(false)
      setActiveTab("bazi")
      updatePersistedWorkspace("bazi", {
        result: { chart, generatedAt: snapshot.generated_at ?? record.updated_at, subjectName: snapshot.subject_name ?? subjectName },
        form: restoredForm,
        chartId: record.id,
        subjectId: record.subject_id,
      })
    } else {
      const snapshot = record.result_snapshot as {
        chart?: IFunctionalAstrolabe
        horoscope?: IFunctionalHoroscope
        horoscope_date?: string
        generated_at?: string
        provenance?: ZiweiProvenance
        subject_name?: string
        statistics?: MetaphysicsStatistics
      }
      const storedProvenance = snapshot.provenance ?? (record.input_snapshot.provenance as ZiweiProvenance | undefined)
      const fallbackProvenance: ZiweiProvenance = {
        algorithm: form.ziwei_algorithm === "zhongzhou" ? "zhongzhou" : "default",
        astroType: form.ziwei_astro_type === "earth" || form.ziwei_astro_type === "human" ? form.ziwei_astro_type : "heaven",
        yearDivide: form.ziwei_year_divide === "normal" ? "normal" : "exact",
        dayBoundary: form.day_boundary === "current" ? "current" : "forward",
        calendar: record.subject.calendar_type,
        fixLeap: form.fix_leap !== false,
        isLeapMonth: form.ziwei_leap_month === true,
      }
      const provenance = storedProvenance ?? fallbackProvenance
      const savedHoroscopeDate = snapshot.horoscope_date ?? record.birth_date
      const hasStoredNormalizedInput = Boolean(record.input_snapshot.normalized_ziwei && typeof record.input_snapshot.normalized_ziwei === "object")
      const normalizedInput = normalizedZiweiInputFromRecord(record, form, savedHoroscopeDate)
      const generatedAt = snapshot.generated_at ?? record.updated_at

      if (normalizedInput) {
        setZiweiCalendar(normalizedInput.calendar)
        setZiweiLeapMonth(normalizedInput.isLeapMonth)
        setGender(normalizedInput.gender)
        setHoroscopeDate(normalizedInput.horoscopeDate)
        if (normalizedInput.calendar === "solar") setBirthTime(`${normalizedInput.date}T${normalizedInput.time}`)
        else {
          setLunarBirthDate(normalizedInput.date)
          setLunarBirthTime(normalizedInput.time)
        }
      }

      if (isStandardZiweiProvenance(provenance) && hasStoredNormalizedInput && normalizedInput) {
        const { chart, horoscope, statisticsChart } = await instantiateStandardZiwei(normalizedInput, locale)
        setZiweiResult({
          chart,
          horoscope,
          horoscopeDate: normalizedInput.horoscopeDate,
          generatedAt,
          provenance: standardZiweiProvenance(normalizedInput),
          subjectName: snapshot.subject_name ?? subjectName,
          statistics: null,
          statisticsStatus: "loading",
          archiveMode: "standard",
          normalizedInput,
        })
        requestZiweiStatistics(statisticsChart, generatedAt)
      } else {
        if (!snapshot.chart || !snapshot.horoscope) throw new Error(locale === "zh" ? "紫微命盘快照不完整。" : "The Zi Wei snapshot is incomplete.")
        const archiveMode: ZiweiArchiveMode = !isStandardZiweiProvenance(provenance) ? "legacy-nonstandard" : "legacy-static"
        setZiweiResult({
          chart: snapshot.chart,
          horoscope: snapshot.horoscope,
          horoscopeDate: savedHoroscopeDate,
          generatedAt,
          provenance,
          subjectName: snapshot.subject_name ?? subjectName,
          statistics: null,
          statisticsStatus: "unavailable",
          statisticsError: locale === "zh" ? "旧档案以静态快照保留，未重新计算频率样本。" : "This legacy archive is preserved as a static snapshot; frequency samples were not recalculated.",
          archiveMode,
          normalizedInput: normalizedInput ?? undefined,
        })
      }
      setActiveZiweiSubjectId(record.subject_id)
      setActiveZiweiChartId(record.id)
      setZiweiPeriodSavePending(false)
      setZiweiPeriodSaveError(false)
      setZiweiEditorOpen(false)
      setActiveTab("ziwei")
      if (normalizedInput && isStandardZiweiProvenance(provenance)) {
        updatePersistedWorkspace("ziwei", {
          normalizedInput,
          generatedAt,
          subjectName: snapshot.subject_name ?? subjectName,
          form: restoredForm,
          chartId: record.id,
          subjectId: record.subject_id,
        })
      }
    }
  }

  function formSnapshot() {
    return {
      birth_time: birthTime,
      lunar_birth_date: lunarBirthDate,
      lunar_birth_time: lunarBirthTime,
      true_solar: baziTrueSolar,
      day_boundary: baziDayBoundary,
      is_leap_month: isLeapMonth,
      hour_uncertain: baziHourUncertain,
      fold_choice: baziFoldChoice,
      dayun_algorithm: dayunAlgorithm,
      selected_location: selectedBirthPlace,
      fix_leap: STANDARD_ZIWEI_RULES.fixLeap,
      ziwei_calendar: ziweiCalendar,
      ziwei_leap_month: ziweiLeapMonth,
      ziwei_algorithm: STANDARD_ZIWEI_RULES.algorithm,
      ziwei_astro_type: STANDARD_ZIWEI_RULES.astroType,
      ziwei_year_divide: STANDARD_ZIWEI_RULES.yearDivide,
      horoscope_date: horoscopeDate,
    }
  }

  function subjectPayload(chartType: "bazi" | "ziwei", calendarType: "solar" | "lunar", subjectGender: "male" | "female") {
    const localTimestamp = calendarType === "solar"
      ? birthTime
      : `${lunarBirthDate}T${lunarBirthTime}`
    return {
      id: chartType === "bazi" ? activeBaziSubjectId : activeZiweiSubjectId,
      display_name: baziSubjectName.trim() || null,
      birth_local_timestamp: localTimestamp,
      timezone,
      calendar_type: calendarType,
      gender: subjectGender,
      birth_place: birthPlace || null,
      location_id: selectedBirthPlace?.id ?? null,
      latitude: selectedBirthPlace?.latitude ?? null,
      longitude: longitude ? Number(longitude) : selectedBirthPlace?.longitude ?? null,
    } satisfies MetaphysicsChartSavePayload["subject"]
  }

  async function persistGeneratedChart(payload: MetaphysicsChartSavePayload, options?: { isCurrent?: () => boolean }) {
    const isCurrent = options?.isCurrent ?? (() => true)
    if (!auth.accessToken || !isCurrent()) return null
    setSavingType(payload.chart_type)
    try {
      const record = await saveMetaphysicsChart(payload, auth.accessToken)
      if (!isCurrent()) return null
      if (record.chart_type === "bazi") {
        setActiveBaziSubjectId(record.subject_id)
        setActiveBaziChartId(record.id)
      } else {
        setActiveZiweiSubjectId(record.subject_id)
        setActiveZiweiChartId(record.id)
      }
      loadedChartRef.current = record.id
      router.replace(`${toLocalePath("/tools")}?tab=${record.chart_type}&chart=${record.id}`, { scroll: false })
      return record
    } catch {
      if (isCurrent()) toast.error(copy.saveFailed)
      return null
    } finally {
      if (isCurrent()) setSavingType(null)
    }
  }

  function startNewChart(chartType: "bazi" | "ziwei") {
    ziweiPeriodSaveVersionRef.current += 1
    if (chartType === "bazi") {
      setBirthResult(null)
      setIncompleteBaziRecord(null)
      setActiveBaziSubjectId(null)
      setActiveBaziChartId(null)
      setBaziEditorOpen(true)
    } else {
      setZiweiResult(null)
      setActiveZiweiSubjectId(null)
      setActiveZiweiChartId(null)
      setZiweiEditorOpen(true)
    }
    updatePersistedWorkspace(chartType, null)
    setZiweiPeriodSavePending(false)
    setZiweiPeriodSaveError(false)
    setSavingType(null)
    setBaziSubjectName("")
    setBirthTime(localDateTimeValue(new Date(1990, 0, 1, 12, 0)))
    setLunarBirthDate("1990-01-01")
    setLunarBirthTime("12:00")
    setBaziHourUncertain(false)
    setBaziFoldChoice(null)
    setBaziAmbiguousTime(false)
    setBirthPlace("")
    setSelectedBirthPlace(null)
    setLocationAutofill(null)
    loadedChartRef.current = null
    router.replace(`${toLocalePath("/tools")}?tab=${chartType}`, { scroll: false })
    window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" })
  }

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

  async function generateBazi(foldOverride?: "first" | "second") {
    const solarDate = normalizeCalendarDate(birthTime.slice(0, 10))
    const solarTime = baziHourUncertain ? "12:00" : normalizeExactTime(birthTime.slice(11, 16))
    if (baziCalendar === "solar" && (!solarDate || !solarTime)) {
      toast.error(locale === "zh" ? "请输入有效出生日期。" : "Enter a valid birth date.")
      return
    }
    const lunarMatch = lunarBirthDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
    const lunarExactTime = baziHourUncertain ? "12:00" : normalizeExactTime(lunarBirthTime)
    const lunarTimeMatch = lunarExactTime?.match(/^(\d{2}):(\d{2})$/)
    if (baziCalendar === "lunar" && (!lunarMatch || !lunarTimeMatch)) {
      toast.error(locale === "zh" ? "农历日期请使用 YYYY-MM-DD，并填写准确到分钟的出生时间。" : "Use YYYY-MM-DD for the lunar date and provide an exact birth time to the minute.")
      return
    }
    setBaziAmbiguousTime(false)
    setBirthLoading(true)
    try {
      const calculationRequest = {
        timestamp: baziCalendar === "solar" ? `${solarDate}T${solarTime}` : `${lunarBirthDate}T${lunarExactTime}`,
        timezone,
        longitude: longitude ? Number(longitude) : null,
        use_true_solar_time: baziTrueSolar,
        day_boundary: baziDayBoundary,
        calendar_type: baziCalendar,
        is_leap_month: baziCalendar === "lunar" && isLeapMonth,
        gender: baziGender,
        birth_place: birthPlace || null,
        hour_uncertain: baziHourUncertain,
        dayun_algorithm: dayunAlgorithm,
        lunar_year: lunarMatch ? Number(lunarMatch[1]) : null,
        lunar_month: lunarMatch ? Number(lunarMatch[2]) : null,
        lunar_day: lunarMatch ? Number(lunarMatch[3]) : null,
        lunar_hour: lunarTimeMatch ? Number(lunarTimeMatch[1]) : null,
        lunar_minute: lunarTimeMatch ? Number(lunarTimeMatch[2]) : null,
        fold_choice: foldOverride ?? baziFoldChoice,
      } as const
      const chart = await calculateMetaphysicsChart(calculationRequest)
      const subjectName = baziSubjectName.trim()
      const nextBirthResult = { chart, generatedAt: new Date().toISOString(), subjectName }
      const generatedAt = nextBirthResult.generatedAt
      setBirthResult(nextBirthResult)
      setIncompleteBaziRecord(null)
      setBaziEditorOpen(false)
      persistBaziWorkspace(nextBirthResult)
      const saved = await persistGeneratedChart({
        id: activeBaziChartId,
        chart_type: "bazi",
        subject: subjectPayload("bazi", baziCalendar, baziGender),
        title: subjectName ? `${subjectName} · 八字` : null,
        birth_date: (chart.birth_profile.converted_solar_date ?? chart.calculation_timestamp).slice(0, 10),
        day_pillar: chart.calendar_facts.day_pillar,
        input_snapshot: { form: formSnapshot(), calculation_request: calculationRequest },
        result_snapshot: { chart, generated_at: generatedAt, subject_name: subjectName, derived_schema_version: 5, baseline_id: chart.statistics.baseline.id },
        engine_name: "canonical-calendar",
        engine_version: "1+sxtwl-2.0.7+lunar-python-1.4.8",
        rules_version: `${chart.rules_version}:${baziDayBoundary}:${dayunAlgorithm}`,
        schema_version: 5,
      })
      if (saved) persistBaziWorkspace(nextBirthResult, saved.id, saved.subject_id)
    } catch (error) {
      const message = (error as Error).message
      if (message.includes("出现了两次") || message.toLowerCase().includes("appears twice")) {
        setBaziAmbiguousTime(true)
        toast.info(locale === "zh" ? "这个当地时间出现过两次，请确认是哪一次。" : "This local time occurred twice. Choose which occurrence applies.")
      } else {
        toast.error(message)
      }
    } finally {
      setBirthLoading(false)
    }
  }

  async function generateZiwei() {
    if (!isSupportedHoroscopeDate(horoscopeDate)) {
      toast.error(copy.invalidHoroscopeDate)
      return
    }
    const date = normalizeCalendarDate(ziweiCalendar === "lunar" ? lunarBirthDate : birthTime.slice(0, 10))
    const time = normalizeExactTime(ziweiCalendar === "lunar" ? lunarBirthTime : birthTime.slice(11, 16))
    if (!date || !time) {
      toast.error(locale === "zh" ? "请输入有效日期和准确到分钟的出生时间。" : "Enter a valid date and exact birth time to the minute.")
      return
    }
    const normalizedInput: ZiweiNormalizedInput = {
      calendar: ziweiCalendar,
      date,
      time,
      gender,
      isLeapMonth: ziweiCalendar === "lunar" && ziweiLeapMonth,
      horoscopeDate,
    }
    const provenance = standardZiweiProvenance(normalizedInput)
    ziweiPeriodSaveVersionRef.current += 1
    setZiweiPeriodSavePending(false)
    setZiweiPeriodSaveError(false)
    setZiweiLoading(true)
    try {
      const { chart, horoscope, statisticsChart } = await instantiateStandardZiwei(normalizedInput, locale)
      const generatedAt = new Date().toISOString()
      const subjectName = baziSubjectName.trim()
      setZiweiResult({
        chart,
        horoscope,
        horoscopeDate,
        generatedAt,
        provenance,
        subjectName,
        statistics: null,
        statisticsStatus: "loading",
        archiveMode: "standard",
        normalizedInput,
      })
      setZiweiEditorOpen(false)
      persistZiweiWorkspace(normalizedInput, generatedAt, subjectName)
      requestZiweiStatistics(statisticsChart, generatedAt)
      await ziweiPeriodSaveQueueRef.current
      const saved = await persistGeneratedChart({
        id: activeZiweiChartId,
        chart_type: "ziwei",
        subject: subjectPayload("ziwei", ziweiCalendar, gender === "女" ? "female" : "male"),
        title: subjectName ? `${subjectName} · 紫微` : null,
        birth_date: chart.solarDate.slice(0, 10),
        day_pillar: chart.rawDates.chineseDate.daily.join(""),
        input_snapshot: { form: formSnapshot(), provenance, normalized_ziwei: normalizedInput },
        result_snapshot: { chart, horoscope, horoscope_date: horoscopeDate, generated_at: generatedAt, provenance, subject_name: subjectName, statistics_status: "deferred", derived_schema_version: 3, baseline_id: ZIWEI_BASELINE_ID },
        engine_name: "iztro",
        engine_version: "2.5.8",
        rules_version: "ziwei-v2.1:default:heaven:exact:forward",
        schema_version: 3,
      })
      if (saved) persistZiweiWorkspace(normalizedInput, generatedAt, subjectName, saved.id, saved.subject_id)
    } catch (error) {
      toast.error((error as Error).message || (locale === "zh" ? "紫微排盘内核加载失败。" : "Zi Wei engine failed to load."))
    } finally {
      setZiweiLoading(false)
    }
  }

  function changeZiweiHoroscopeDate(nextDate: string) {
    if (!ziweiResult || ziweiResult.archiveMode !== "standard") return
    if (!isSupportedHoroscopeDate(nextDate)) {
      toast.error(copy.invalidHoroscopeDate)
      return
    }
    try {
      const horoscope = ziweiResult.chart.horoscope(nextDate)
      const normalizedInput = ziweiResult.normalizedInput
        ? { ...ziweiResult.normalizedInput, horoscopeDate: nextDate }
        : undefined
      setHoroscopeDate(nextDate)
      setZiweiResult((current) => current?.archiveMode === "standard"
        ? {
            ...current,
            horoscope,
            horoscopeDate: nextDate,
            normalizedInput,
          }
        : current)
      if (normalizedInput) {
        persistZiweiWorkspace(normalizedInput, ziweiResult.generatedAt, ziweiResult.subjectName)
      }
      if (activeZiweiChartId && normalizedInput) {
        const currentResult = ziweiResult
        const saveVersion = ++ziweiPeriodSaveVersionRef.current
        const payload: MetaphysicsChartSavePayload = {
          id: activeZiweiChartId,
          chart_type: "ziwei",
          subject: subjectPayload("ziwei", normalizedInput.calendar, normalizedInput.gender === "女" ? "female" : "male"),
          title: currentResult.subjectName ? `${currentResult.subjectName} · 紫微` : null,
          birth_date: currentResult.chart.solarDate.slice(0, 10),
          day_pillar: currentResult.chart.rawDates.chineseDate.daily.join(""),
          input_snapshot: { form: { ...formSnapshot(), horoscope_date: nextDate }, provenance: currentResult.provenance, normalized_ziwei: normalizedInput },
          result_snapshot: { chart: currentResult.chart, horoscope, horoscope_date: nextDate, generated_at: currentResult.generatedAt, provenance: currentResult.provenance, subject_name: currentResult.subjectName, statistics: currentResult.statistics, derived_schema_version: 3, baseline_id: ZIWEI_BASELINE_ID },
          engine_name: "iztro",
          engine_version: "2.5.8",
          rules_version: "ziwei-v2.1:default:heaven:exact:forward",
          schema_version: 3,
        }
        setZiweiPeriodSavePending(true)
        setZiweiPeriodSaveError(false)
        ziweiPeriodSaveQueueRef.current = ziweiPeriodSaveQueueRef.current.then(async () => {
          if (saveVersion !== ziweiPeriodSaveVersionRef.current) return
          const saved = await persistGeneratedChart(payload, {
            isCurrent: () => saveVersion === ziweiPeriodSaveVersionRef.current,
          })
          if (saveVersion === ziweiPeriodSaveVersionRef.current) {
            setZiweiPeriodSavePending(false)
            setZiweiPeriodSaveError(!saved)
          }
        })
      }
    } catch {
      toast.error(copy.invalidHoroscopeDate)
    }
  }

  function createStandardZiweiCopy() {
    const normalizedInput = ziweiResult?.normalizedInput
    if (normalizedInput) {
      setZiweiCalendar(normalizedInput.calendar)
      setZiweiLeapMonth(normalizedInput.isLeapMonth)
      setGender(normalizedInput.gender)
      setHoroscopeDate(normalizedInput.horoscopeDate)
      if (normalizedInput.calendar === "solar") setBirthTime(`${normalizedInput.date}T${normalizedInput.time}`)
      else {
        setLunarBirthDate(normalizedInput.date)
        setLunarBirthTime(normalizedInput.time)
      }
    }
    setZiweiResult(null)
    updatePersistedWorkspace("ziwei", null)
    setActiveZiweiSubjectId(null)
    setActiveZiweiChartId(null)
    setZiweiEditorOpen(true)
    loadedChartRef.current = null
    router.replace(`${toLocalePath("/tools")}?tab=ziwei`, { scroll: false })
    window.setTimeout(() => document.getElementById("ziwei-edit-details")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0)
  }

  return (
    <main className="mx-auto max-w-[92rem] space-y-6">
      <header className="border-b border-border/60 pb-5">
        <p className="kicker">{locale === "zh" ? "命理排盘" : "Personal charts"}</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">{copy.subtitle}</p>
        <p className="mt-3 max-w-3xl text-xs leading-5 text-muted-foreground">{copy.chartNote}</p>
      </header>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "current" | "bazi" | "ziwei")}>
        <TabsList className="grid w-full grid-cols-3"><TabsTrigger value="current"><CalendarClock className="mr-2 size-4" />{copy.current}</TabsTrigger><TabsTrigger value="bazi"><Compass className="mr-2 size-4" />{copy.bazi}</TabsTrigger><TabsTrigger value="ziwei"><Sparkles className="mr-2 size-4" />{copy.ziwei}</TabsTrigger></TabsList>
        <TabsContent value="current" className="mt-4 space-y-4">
          <div aria-live="polite" aria-busy={currentLoading}>
            {currentLoading && !currentChart ? <Loading locale={locale} label={copy.loadingCurrent} /> : currentChart ? <BaziChartView chart={currentChart} locale={locale} mode="current" /> : null}
          </div>
          <Button asChild><Link href={castHref}>{copy.useToCast}</Link></Button>
        </TabsContent>
        <TabsContent value="bazi" className="mt-4 space-y-4">
          {incompleteBaziRecord ? <aside className="rounded-xl border border-border/60 bg-surface p-4"><h2 className="text-sm font-semibold">{locale === "zh" ? "这份旧档案缺少准确时辰" : "This legacy record lacks an exact birth hour"}</h2><p className="mt-2 text-sm leading-6 text-muted-foreground">{incompleteBaziRecord.subjectName || (locale === "zh" ? "匿名命主" : "Anonymous")} · {incompleteBaziRecord.birthTimestamp}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{locale === "zh" ? "完整四柱、运限、神煞和统计暂不展示。请在下方补充准确出生时间后重新生成。" : "The full chart, periods, Shen Sha, and statistics are withheld. Add an exact birth time below to recalculate."}</p></aside> : null}
          {birthResult ? (
            <>
              <ChartPersistenceBar copy={copy} isSaving={savingType === "bazi"} isSaved={Boolean(activeBaziChartId)} isAuthenticated={Boolean(auth.user)} onEdit={() => { const saved = readPersistedWorkspace().bazi; if (saved) applyPersistedForm(saved.form); setBaziEditorOpen(true) }} onNew={() => startNewChart("bazi")} />
              <BaziChartView chart={birthResult.chart} generatedAt={birthResult.generatedAt} subjectName={birthResult.subjectName} locale={locale} mode="birth" />
            </>
          ) : null}
          <details data-export-exclude open={baziEditorOpen} onToggle={(event) => setBaziEditorOpen(event.currentTarget.open)} className="border-t border-border/60 pt-4">
            <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{birthResult ? copy.editDetails : copy.basicSettings}</summary>
            <div className="mt-4 space-y-4">
              <p className="text-xs leading-5 text-muted-foreground">{copy.exactTimeRequired}</p>
              <BaziControls copy={copy} locale={locale} subjectName={baziSubjectName} setSubjectName={setBaziSubjectName} birthTime={birthTime} setBirthTime={setBirthTime} lunarBirthDate={lunarBirthDate} setLunarBirthDate={setLunarBirthDate} lunarBirthTime={lunarBirthTime} setLunarBirthTime={setLunarBirthTime} timezone={timezone} setTimezone={setTimezone} timezoneOptions={timezoneOptions} longitude={longitude} setLongitude={setLongitude} trueSolar={baziTrueSolar} setTrueSolar={setBaziTrueSolar} dayBoundary={baziDayBoundary} setDayBoundary={setBaziDayBoundary} calendar={baziCalendar} setCalendar={setBaziCalendar} gender={baziGender} setGender={setBaziGender} hourUncertain={baziHourUncertain} setHourUncertain={setBaziHourUncertain} selectedLocation={selectedBirthPlace} birthPlaceOverrideActive={locationOverrideActive} effectiveTimezone={timezone} effectiveLongitude={longitude} onBirthPlaceSelect={handleBirthPlaceSelect} onBirthPlaceClear={handleBirthPlaceClear} isLeapMonth={isLeapMonth} setIsLeapMonth={setIsLeapMonth} dayunAlgorithm={dayunAlgorithm} setDayunAlgorithm={setDayunAlgorithm} />
              {baziAmbiguousTime ? <div className="rounded-xl border border-amber-500/30 bg-amber-500/[0.06] p-4"><p className="text-sm font-semibold">{locale === "zh" ? "这个当地时间因夏令时出现过两次" : "This local time occurred twice during daylight-saving time"}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">{locale === "zh" ? "请按出生记录选择第一次或第二次出现的时间。" : "Choose the first or second occurrence shown on the birth record."}</p><div className="mt-3 flex flex-wrap gap-2"><Button type="button" variant="outline" onClick={() => { setBaziFoldChoice("first"); setBaziAmbiguousTime(false); void generateBazi("first") }}>{locale === "zh" ? "第一个时间" : "First occurrence"}</Button><Button type="button" variant="outline" onClick={() => { setBaziFoldChoice("second"); setBaziAmbiguousTime(false); void generateBazi("second") }}>{locale === "zh" ? "第二个时间" : "Second occurrence"}</Button></div></div> : null}
              <Button onClick={() => void generateBazi()} disabled={birthLoading}>{birthLoading ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : null}{copy.calculate}</Button>
            </div>
          </details>
          <div aria-live="polite" aria-busy={birthLoading}>
            {birthLoading && !birthResult ? <Loading locale={locale} label={copy.loadingResult} /> : null}
          </div>
        </TabsContent>
        <TabsContent value="ziwei" className="mt-4 space-y-4">
          {ziweiResult ? <ChartPersistenceBar copy={copy} isSaving={savingType === "ziwei" || ziweiPeriodSavePending} isSaved={Boolean(activeZiweiChartId) && !ziweiPeriodSaveError} saveError={ziweiPeriodSaveError} isAuthenticated={Boolean(auth.user)} onEdit={ziweiResult.archiveMode === "standard" ? () => { const saved = readPersistedWorkspace().ziwei; if (saved) applyPersistedForm(saved.form); setZiweiEditorOpen(true) } : undefined} onNew={() => startNewChart("ziwei")} /> : null}
          {ziweiResult ? <ZiweiChartView chart={ziweiResult.chart} horoscope={ziweiResult.horoscope} horoscopeDate={ziweiResult.horoscopeDate} generatedAt={ziweiResult.generatedAt} locale={locale} provenance={ziweiResult.provenance} subjectName={ziweiResult.subjectName} statistics={ziweiResult.statistics} statisticsStatus={ziweiResult.statisticsStatus} statisticsError={ziweiResult.statisticsError} archiveMode={ziweiResult.archiveMode} onHoroscopeDateChange={changeZiweiHoroscopeDate} onCreateStandardCopy={createStandardZiweiCopy} /> : null}
          {!ziweiResult || ziweiResult.archiveMode === "standard" ? <details id="ziwei-edit-details" data-export-exclude open={ziweiEditorOpen} onToggle={(event) => setZiweiEditorOpen(event.currentTarget.open)} className="border-t border-border/60 pt-4">
            <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{ziweiResult ? copy.editDetails : copy.ziweiBasicSettings}</summary>
            <div className="mt-4 space-y-4">
          <section aria-labelledby="ziwei-basic-title">
            <div className="flex flex-wrap items-end justify-between gap-2"><div><h2 id="ziwei-basic-title" className="text-sm font-semibold">{copy.ziweiBasicSettings}</h2><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "准确出生时辰用于安定十二宫与完整运限。" : "An exact birth hour places the twelve palaces and unlocks full period layers."}</p></div><p className="max-w-2xl text-xs leading-5 text-muted-foreground"><strong className="text-foreground">{copy.standardRules}:</strong> {copy.standardRulesBody}</p></div>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2">
                <label htmlFor="ziwei-subject-name" className="text-sm font-medium">{copy.subjectName}</label>
                <Input id="ziwei-subject-name" value={baziSubjectName} maxLength={40} autoComplete="name" placeholder={locale === "zh" ? "选填，留空显示匿名命主" : "Optional; blank displays Anonymous"} onChange={(event) => setBaziSubjectName(event.target.value)} />
              </div>
              <div className="space-y-2">
                <label id="ziwei-calendar-label" className="text-sm font-medium">{copy.calendar}</label>
                <Select value={ziweiCalendar} onValueChange={(value) => setZiweiCalendar(value as "solar" | "lunar")}>
                  <SelectTrigger id="ziwei-calendar" aria-labelledby="ziwei-calendar-label"><SelectValue /></SelectTrigger>
                  <SelectContent><SelectItem value="solar">{copy.solar}</SelectItem><SelectItem value="lunar">{copy.lunar}</SelectItem></SelectContent>
                </Select>
              </div>
              {ziweiCalendar === "solar" ? (
                <div className="space-y-2"><label htmlFor="ziwei-birth-time" className="text-sm font-medium">{copy.birth}</label><Input id="ziwei-birth-time" type="datetime-local" value={birthTime} onChange={(event) => setBirthTime(event.target.value)} required /></div>
              ) : (
                <div className="grid gap-2 sm:grid-cols-[1fr_8rem] lg:col-span-2">
                  <div className="space-y-2"><label htmlFor="ziwei-lunar-date" className="text-sm font-medium">{copy.lunarDateFormat}</label><Input id="ziwei-lunar-date" value={lunarBirthDate} inputMode="numeric" placeholder="1990-01-01" onChange={(event) => setLunarBirthDate(event.target.value)} required /></div>
                  <div className="space-y-2"><label htmlFor="ziwei-lunar-time" className="text-sm font-medium">{copy.birth}</label><Input id="ziwei-lunar-time" type="time" value={lunarBirthTime} onChange={(event) => setLunarBirthTime(event.target.value)} required /></div>
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
              {ziweiCalendar === "lunar" ? <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><label id="ziwei-leap-month-label" htmlFor="ziwei-leap-month" className="text-sm">{copy.leapMonth}</label><Switch id="ziwei-leap-month" aria-labelledby="ziwei-leap-month-label" checked={ziweiLeapMonth} onCheckedChange={setZiweiLeapMonth} /></div> : null}
              <div className="md:col-span-2 lg:col-span-4"><BirthPlaceField locale={locale} selectedLocation={selectedBirthPlace} overrideActive={locationOverrideActive} effectiveTimezone={timezone} effectiveLongitude={longitude} onSelect={handleBirthPlaceSelect} onClear={handleBirthPlaceClear} /></div>
            </div>
          </section>

          <Button onClick={generateZiwei} disabled={ziweiLoading}>{ziweiLoading ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : null}{copy.calculate}</Button>
            </div>
          </details> : null}
          <div aria-live="polite" aria-busy={ziweiLoading}>
            {ziweiLoading ? <Loading locale={locale} label={copy.loadingZiwei} /> : null}
          </div>
        </TabsContent>
      </Tabs>
    </main>
  )
}

function ChartPersistenceBar({ copy, isSaving, isSaved, saveError = false, isAuthenticated, onEdit, onNew }: {
  copy: { newChart: string; editDetails: string; savedCloud: string; savingCloud: string; loginToSave: string; saveFailed: string }
  isSaving: boolean
  isSaved: boolean
  saveError?: boolean
  isAuthenticated: boolean
  onEdit?: () => void
  onNew: () => void
}) {
  const status = isSaving ? copy.savingCloud : saveError ? copy.saveFailed : isSaved ? copy.savedCloud : copy.loginToSave
  return (
    <div data-export-exclude className="flex flex-col gap-3 border-y border-border/60 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        {isSaving ? <Loader2 className="size-3.5 animate-spin text-primary" /> : isSaved ? <Check className="size-3.5 text-primary" /> : <Cloud className="size-3.5" />}
        {status}
      </p>
      <div className="flex flex-wrap gap-2">
        {onEdit ? <Button type="button" size="sm" variant="ghost" onClick={onEdit}>
          <Pencil className="size-4" />
          {copy.editDetails}
        </Button> : null}
        <Button type="button" size="sm" variant="outline" onClick={onNew}>
          <Plus className="size-4" />
          {copy.newChart}
        </Button>
      </div>
      {!isAuthenticated ? <span className="sr-only">{copy.loginToSave}</span> : null}
    </div>
  )
}

function Loading({ locale, label }: { locale: "en" | "zh"; label: string }) { return <div role="status" aria-live="polite" className="flex items-center justify-center gap-2 rounded-lg border border-border/60 bg-surface p-10 text-sm text-muted-foreground"><Loader2 aria-hidden="true" className="size-4 animate-spin" />{label || (locale === "zh" ? "正在加载…" : "Loading…")}</div> }
