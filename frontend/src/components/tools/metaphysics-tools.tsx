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
import { calculateMetaphysicsChart } from "@/lib/api"
import type { MetaphysicsChart } from "@/types/api"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import type { IFunctionalPalace } from "iztro/lib/astro/FunctionalPalace"

const pad = (value: number) => String(value).padStart(2, "0")
const localDateTimeValue = (date: Date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
const TIMEZONES = ["Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore", "Asia/Tokyo", "America/Los_Angeles", "America/New_York", "Europe/London"]
const PALACE_POSITIONS = [[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3], [2, 3], [1, 3], [0, 3], [0, 2], [0, 1]] as const

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
  const [isLeapMonth, setIsLeapMonth] = useState(false)
  const [hourUncertain, setHourUncertain] = useState(false)
  const [dayunAlgorithm, setDayunAlgorithm] = useState<"sect1" | "sect2">("sect2")
  const [longitude, setLongitude] = useState("")
  const [trueSolar, setTrueSolar] = useState(false)
  const [dayBoundary, setDayBoundary] = useState<"current" | "forward">("forward")
  const [birthChart, setBirthChart] = useState<MetaphysicsChart | null>(null)
  const [birthLoading, setBirthLoading] = useState(false)
  const [gender, setGender] = useState<"男" | "女">("男")
  const [fixLeap, setFixLeap] = useState(true)
  const [ziweiCalendar, setZiweiCalendar] = useState<"solar" | "lunar">("solar")
  const [ziweiLeapMonth, setZiweiLeapMonth] = useState(false)
  const [ziweiAlgorithm, setZiweiAlgorithm] = useState<"default" | "zhongzhou">("default")
  const [ziweiAstroType, setZiweiAstroType] = useState<"heaven" | "earth" | "human">("heaven")
  const [ziweiYearDivide, setZiweiYearDivide] = useState<"normal" | "exact">("exact")
  const [horoscopeDate, setHoroscopeDate] = useState(() => localDateTimeValue(new Date()).slice(0, 10))
  const [ziwei, setZiwei] = useState<IFunctionalAstrolabe | null>(null)
  const [ziweiHoroscope, setZiweiHoroscope] = useState<IFunctionalHoroscope | null>(null)
  const [ziweiLoading, setZiweiLoading] = useState(false)
  const timezoneOptions = useMemo(() => TIMEZONES.includes(timezone) ? TIMEZONES : [timezone, ...TIMEZONES], [timezone])

  const copy = locale === "zh" ? {
    title: "术数工具",
    subtitle: "查看当前时令、排出生八字，并生成明确标注历法规则的紫微斗数星盘。",
    current: "当前时令",
    bazi: "八字排盘",
    ziwei: "紫微斗数",
    timezone: "时区",
    birth: "出生时间",
    calendar: "历法",
    solar: "公历",
    lunar: "农历",
    lunarDateFormat: "农历日期（YYYY-MM-DD）",
    leapMonth: "农历闰月",
    birthPlace: "出生地",
    hourUncertain: "出生时辰不确定",
    dayunRule: "起运算法",
    dayunSect1: "传统折算法（sect1）",
    dayunSect2: "分钟精算法（sect2）",
    longitude: "出生地经度",
    trueSolar: "真太阳时校正（经度与均时差）",
    boundary: "晚子时换日",
    calculate: "开始排盘",
    useToCast: "用这个时间起卦",
    gender: "性别",
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
    title: "Metaphysics Tools",
    subtitle: "Inspect the current Chinese calendar, generate a BaZi chart, and build a Zi Wei Dou Shu chart with explicit calendar rules.",
    current: "Current Time",
    bazi: "BaZi",
    ziwei: "Zi Wei Dou Shu",
    timezone: "Time zone",
    birth: "Birth time",
    calendar: "Calendar",
    solar: "Solar",
    lunar: "Lunar",
    lunarDateFormat: "Lunar date (YYYY-MM-DD)",
    leapMonth: "Leap lunar month",
    birthPlace: "Birth place",
    hourUncertain: "Birth hour uncertain",
    dayunRule: "Da Yun start rule",
    dayunSect1: "Traditional conversion (sect1)",
    dayunSect2: "Minute-based calculation (sect2)",
    longitude: "Birth longitude",
    trueSolar: "True-solar correction (longitude and equation of time)",
    boundary: "Advance day at late Zi hour",
    calculate: "Generate chart",
    useToCast: "Use this time to cast",
    gender: "Gender",
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
    const load = async () => {
      setCurrentLoading(true)
      try {
        const chart = await calculateMetaphysicsChart({ timestamp: new Date().toISOString(), timezone, day_boundary: "forward" })
        if (!cancelled) setCurrentChart(chart)
      } catch (error) {
        if (!cancelled) toast.error((error as Error).message)
      } finally {
        if (!cancelled) setCurrentLoading(false)
      }
    }
    void load()
    const timer = window.setInterval(load, 60_000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [timezone])

  const castHref = useMemo(() => {
    if (!currentChart?.calculation_timestamp) return toLocalePath("/app")
    return `${toLocalePath("/app")}?timestamp=${encodeURIComponent(currentChart.calculation_timestamp)}`
  }, [currentChart?.calculation_timestamp, toLocalePath])

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
      setBirthChart(chart)
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
    const lunarDateMatch = lunarBirthDate.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
    const selectedTime = ziweiCalendar === "lunar" ? lunarBirthTime : birthTime.slice(11, 16)
    const timeMatch = selectedTime.match(/^(\d{1,2}):(\d{2})$/)
    if (ziweiCalendar === "lunar" && (!lunarDateMatch || !timeMatch)) {
      toast.error(locale === "zh" ? "农历日期请使用 YYYY-MM-DD，时间请使用 HH:mm。" : "Use YYYY-MM-DD for the lunar date and HH:mm for time.")
      return
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
        astroType: ziweiAlgorithm === "zhongzhou" ? ziweiAstroType : "heaven",
      })
      setZiwei(chart)
      setZiweiHoroscope(chart.horoscope(horoscopeDate))
    } catch (error) {
      toast.error((error as Error).message || (locale === "zh" ? "紫微排盘内核加载失败。" : "Zi Wei engine failed to load."))
    } finally {
      setZiweiLoading(false)
    }
  }

  return (
    <main className="mx-auto max-w-[92rem] space-y-6">
      <header className="border-b border-border/60 pb-5">
        <p className="kicker">Tools</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{copy.title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-7 text-muted-foreground">{copy.subtitle}</p>
      </header>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-border/60 bg-surface p-4">
        <div className="min-w-64 space-y-2"><label className="text-sm font-medium">{copy.timezone}</label><Select value={timezone} onValueChange={setTimezone}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{timezoneOptions.map((zone) => <SelectItem key={zone} value={zone}>{zone}</SelectItem>)}</SelectContent></Select></div>
        <p className="max-w-2xl text-xs leading-5 text-muted-foreground">{copy.chartNote}</p>
      </div>

      <Tabs defaultValue="current">
        <TabsList className="grid w-full grid-cols-3"><TabsTrigger value="current"><CalendarClock className="mr-2 size-4" />{copy.current}</TabsTrigger><TabsTrigger value="bazi"><Compass className="mr-2 size-4" />{copy.bazi}</TabsTrigger><TabsTrigger value="ziwei"><Sparkles className="mr-2 size-4" />{copy.ziwei}</TabsTrigger></TabsList>
        <TabsContent value="current" className="mt-4 space-y-4">
          {currentLoading && !currentChart ? <Loading /> : currentChart ? <BaziChartView chart={currentChart} locale={locale} /> : null}
          <Button asChild><Link href={castHref}>{copy.useToCast}</Link></Button>
        </TabsContent>
        <TabsContent value="bazi" className="mt-4 space-y-4">
          <ChartControls copy={copy} birthTime={birthTime} setBirthTime={setBirthTime} lunarBirthDate={lunarBirthDate} setLunarBirthDate={setLunarBirthDate} lunarBirthTime={lunarBirthTime} setLunarBirthTime={setLunarBirthTime} longitude={longitude} setLongitude={setLongitude} trueSolar={trueSolar} setTrueSolar={setTrueSolar} dayBoundary={dayBoundary} setDayBoundary={setDayBoundary} calendar={baziCalendar} setCalendar={setBaziCalendar} gender={baziGender} setGender={setBaziGender} birthPlace={birthPlace} setBirthPlace={setBirthPlace} isLeapMonth={isLeapMonth} setIsLeapMonth={setIsLeapMonth} hourUncertain={hourUncertain} setHourUncertain={setHourUncertain} dayunAlgorithm={dayunAlgorithm} setDayunAlgorithm={setDayunAlgorithm} />
          <Button onClick={generateBazi} disabled={birthLoading}>{birthLoading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}{copy.calculate}</Button>
          {birthChart ? <BaziChartView chart={birthChart} locale={locale} /> : null}
        </TabsContent>
        <TabsContent value="ziwei" className="mt-4 space-y-4">
          <section className="grid gap-4 rounded-lg border border-border/60 bg-surface p-4 md:grid-cols-3">
            <div className="space-y-2"><label className="text-sm font-medium">{copy.calendar}</label><Select value={ziweiCalendar} onValueChange={(value) => setZiweiCalendar(value as "solar" | "lunar")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="solar">{copy.solar}</SelectItem><SelectItem value="lunar">{copy.lunar}</SelectItem></SelectContent></Select></div>
            {ziweiCalendar === "solar" ? <div className="space-y-2"><label className="text-sm font-medium">{copy.birth}</label><Input type="datetime-local" value={birthTime} onChange={(event) => setBirthTime(event.target.value)} /></div> : <div className="grid gap-2 sm:grid-cols-[1fr_8rem]"><div className="space-y-2"><label className="text-sm font-medium">{copy.lunarDateFormat}</label><Input value={lunarBirthDate} inputMode="numeric" placeholder="1990-01-01" onChange={(event) => setLunarBirthDate(event.target.value)} /></div><div className="space-y-2"><label className="text-sm font-medium">{copy.birth}</label><Input type="time" value={lunarBirthTime} onChange={(event) => setLunarBirthTime(event.target.value)} /></div></div>}
            <div className="space-y-2"><label className="text-sm font-medium">{copy.gender}</label><Select value={gender} onValueChange={(value) => setGender(value as "男" | "女")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="男">{locale === "zh" ? "男" : "Male"}</SelectItem><SelectItem value="女">{locale === "zh" ? "女" : "Female"}</SelectItem></SelectContent></Select></div>
            <div className="space-y-2"><label className="text-sm font-medium">{copy.school}</label><Select value={ziweiAlgorithm} onValueChange={(value) => setZiweiAlgorithm(value as "default" | "zhongzhou")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="default">{copy.standardSchool}</SelectItem><SelectItem value="zhongzhou">{copy.zhongzhouSchool}</SelectItem></SelectContent></Select></div>
            <div className="space-y-2"><label className="text-sm font-medium">{copy.astroType}</label><Select value={ziweiAstroType} onValueChange={(value) => setZiweiAstroType(value as "heaven" | "earth" | "human")} disabled={ziweiAlgorithm !== "zhongzhou"}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="heaven">{copy.heaven}</SelectItem><SelectItem value="earth">{copy.earth}</SelectItem><SelectItem value="human">{copy.human}</SelectItem></SelectContent></Select></div>
            <div className="space-y-2"><label className="text-sm font-medium">{copy.yearDivide}</label><Select value={ziweiYearDivide} onValueChange={(value) => setZiweiYearDivide(value as "normal" | "exact")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="exact">{copy.exactYear}</SelectItem><SelectItem value="normal">{copy.lunarYear}</SelectItem></SelectContent></Select></div>
            <div className="space-y-2"><label className="text-sm font-medium">{copy.horoscopeDate}</label><Input type="date" value={horoscopeDate} onChange={(event) => setHoroscopeDate(event.target.value)} /></div>
            <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.fixLeap}</span><Switch checked={fixLeap} onCheckedChange={setFixLeap} /></div>
            {ziweiCalendar === "lunar" ? <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.leapMonth}</span><Switch checked={ziweiLeapMonth} onCheckedChange={setZiweiLeapMonth} /></div> : null}
            <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.boundary}</span><Switch checked={dayBoundary === "forward"} onCheckedChange={(checked) => setDayBoundary(checked ? "forward" : "current")} /></div>
          </section>
          <Button onClick={generateZiwei} disabled={ziweiLoading}>{ziweiLoading ? <Loader2 className="mr-2 size-4 animate-spin" /> : null}{copy.calculate}</Button>
          {ziwei ? <ZiweiChart chart={ziwei} horoscope={ziweiHoroscope} locale={locale} /> : null}
        </TabsContent>
      </Tabs>
    </main>
  )
}

function ChartControls({ copy, birthTime, setBirthTime, lunarBirthDate, setLunarBirthDate, lunarBirthTime, setLunarBirthTime, longitude, setLongitude, trueSolar, setTrueSolar, dayBoundary, setDayBoundary, calendar, setCalendar, gender, setGender, birthPlace, setBirthPlace, isLeapMonth, setIsLeapMonth, hourUncertain, setHourUncertain, dayunAlgorithm, setDayunAlgorithm }: { copy: Record<string, string>; birthTime: string; setBirthTime: (value: string) => void; lunarBirthDate: string; setLunarBirthDate: (value: string) => void; lunarBirthTime: string; setLunarBirthTime: (value: string) => void; longitude: string; setLongitude: (value: string) => void; trueSolar: boolean; setTrueSolar: (value: boolean) => void; dayBoundary: "current" | "forward"; setDayBoundary: (value: "current" | "forward") => void; calendar: "solar" | "lunar"; setCalendar: (value: "solar" | "lunar") => void; gender: "male" | "female"; setGender: (value: "male" | "female") => void; birthPlace: string; setBirthPlace: (value: string) => void; isLeapMonth: boolean; setIsLeapMonth: (value: boolean) => void; hourUncertain: boolean; setHourUncertain: (value: boolean) => void; dayunAlgorithm: "sect1" | "sect2"; setDayunAlgorithm: (value: "sect1" | "sect2") => void }) {
  return (
    <section className="grid gap-4 rounded-lg border border-border/60 bg-surface p-4 md:grid-cols-2">
      <div className="space-y-2"><label className="text-sm font-medium">{copy.calendar}</label><Select value={calendar} onValueChange={(value) => setCalendar(value as "solar" | "lunar")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="solar">{copy.solar}</SelectItem><SelectItem value="lunar">{copy.lunar}</SelectItem></SelectContent></Select></div>
      {calendar === "solar" ? <div className="space-y-2"><label className="text-sm font-medium">{copy.birth}</label><Input type={hourUncertain ? "date" : "datetime-local"} value={hourUncertain ? birthTime.slice(0, 10) : birthTime} onChange={(event) => setBirthTime(hourUncertain ? `${event.target.value}T12:00` : event.target.value)} /></div> : <div className="grid gap-2 sm:grid-cols-[1fr_8rem]"><div className="space-y-2"><label className="text-sm font-medium">{copy.lunarDateFormat}</label><Input value={lunarBirthDate} inputMode="numeric" placeholder="1990-01-01" onChange={(event) => setLunarBirthDate(event.target.value)} /></div><div className="space-y-2"><label className="text-sm font-medium">{copy.birth}</label><Input type="time" value={hourUncertain ? "12:00" : lunarBirthTime} disabled={hourUncertain} onChange={(event) => setLunarBirthTime(event.target.value)} /></div></div>}
      <div className="space-y-2"><label className="text-sm font-medium">{copy.gender}</label><Select value={gender} onValueChange={(value) => setGender(value as "male" | "female")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="male">男 / Male</SelectItem><SelectItem value="female">女 / Female</SelectItem></SelectContent></Select></div>
      <div className="space-y-2"><label className="text-sm font-medium">{copy.birthPlace}</label><Input value={birthPlace} maxLength={120} placeholder="Shanghai / 上海" onChange={(event) => setBirthPlace(event.target.value)} /></div>
      <div className="space-y-2"><label className="text-sm font-medium">{copy.longitude}</label><Input type="number" min={-180} max={180} step="0.0001" placeholder="121.4737" value={longitude} onChange={(event) => setLongitude(event.target.value)} /></div>
      <div className="space-y-2"><label className="text-sm font-medium">{copy.dayunRule}</label><Select value={dayunAlgorithm} onValueChange={(value) => setDayunAlgorithm(value as "sect1" | "sect2")}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="sect2">{copy.dayunSect2}</SelectItem><SelectItem value="sect1">{copy.dayunSect1}</SelectItem></SelectContent></Select></div>
      <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.trueSolar}</span><Switch checked={trueSolar} onCheckedChange={setTrueSolar} /></div>
      <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.boundary}</span><Switch checked={dayBoundary === "forward"} onCheckedChange={(checked) => setDayBoundary(checked ? "forward" : "current")} /></div>
      {calendar === "lunar" ? <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.leapMonth}</span><Switch checked={isLeapMonth} onCheckedChange={setIsLeapMonth} /></div> : null}
      <div className="flex items-center justify-between rounded-md border border-border/50 px-3 py-2"><span className="text-sm">{copy.hourUncertain}</span><Switch checked={hourUncertain} onCheckedChange={setHourUncertain} /></div>
    </section>
  )
}

function BaziChartView({ chart, locale }: { chart: MetaphysicsChart; locale: "en" | "zh" }) {
  const facts = chart.calendar_facts
  return (
    <section className="space-y-4 rounded-lg border border-border/60 bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="kicker">{chart.lunar_date}</p>
          <h2 className="mt-2 text-2xl font-semibold">{chart.bazi}</h2>
          <p className="mt-1 text-xs text-muted-foreground">{new Date(facts.gregorian).toLocaleString(locale === "zh" ? "zh-CN" : "en-US")} · {chart.timezone}</p>
        </div>
        <div className="rounded-md border border-primary/30 bg-primary/10 px-3 py-2 text-sm"><span className="text-muted-foreground">{locale === "zh" ? "旬空" : "Void"}</span> <strong>{chart.xunkong}</strong></div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <Fact label={locale === "zh" ? "月建" : "Month command"} value={`${facts.month_command} · ${locale === "zh" ? "冲" : "clash"}${facts.month_clash} · ${locale === "zh" ? "合" : "combine"}${facts.month_combine}`} />
        <Fact label={locale === "zh" ? "日辰" : "Day branch"} value={`${facts.day_pillar} · ${locale === "zh" ? "冲" : "clash"}${facts.day_clash} · ${locale === "zh" ? "合" : "combine"}${facts.day_combine}`} />
        <Fact label={locale === "zh" ? "六神起点" : "Six-spirit start"} value={facts.six_spirit_start} />
        <Fact label={locale === "zh" ? "六神顺序" : "Six spirits"} value={facts.six_spirits.join(" · ")} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {chart.pillars.map((pillar) => <article key={pillar.label} className="rounded-lg border border-border/50 bg-surface-elevated p-4 text-center"><p className="text-xs text-muted-foreground">{pillar.label}{locale === "zh" ? "柱" : " Pillar"} · {pillar.ten_god}</p><p className="mt-2 text-3xl font-semibold tracking-widest">{pillar.text}</p><p className="mt-2 text-xs text-muted-foreground">{pillar.stem_element} / {pillar.branch_element} · {pillar.nayin}</p><div className="mt-3 flex flex-wrap justify-center gap-1">{pillar.hidden_stems.map((item) => <span key={item.stem} className="rounded border border-border/50 px-2 py-1 text-[0.65rem]">{item.stem} {item.ten_god}</span>)}</div></article>)}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-md border border-border/50 p-4"><p className="text-sm font-semibold">{locale === "zh" ? "五行计数" : "Five elements"}</p><div className="mt-3 grid grid-cols-5 gap-2 text-center">{Object.entries(chart.element_counts).map(([element, count]) => <div key={element}><p className="text-lg font-semibold">{count}</p><p className="text-xs text-muted-foreground">{element}</p></div>)}</div></div>
        <div className="rounded-md border border-border/50 p-4"><p className="text-sm font-semibold">{locale === "zh" ? "节气" : "Solar terms"}</p><p className="mt-2 text-sm">{chart.previous_solar_term?.name} → {chart.next_solar_term?.name}</p>{chart.next_solar_term ? <SolarTermCountdown key={chart.next_solar_term.timestamp} timestamp={chart.next_solar_term.timestamp} locale={locale} /> : <p className="mt-1 text-xs text-muted-foreground">—</p>}</div>
      </div>
      {chart.birth_profile.hour_uncertain ? <HourCandidates candidates={chart.birth_profile.hour_candidates} locale={locale} /> : null}
      <DayunPanel chart={chart} locale={locale} />
      <p className="text-[0.65rem] leading-5 text-muted-foreground">{Object.values(chart.birth_profile.engines).join(" · ")} · {locale === "zh" ? "历法事实与大运算法分层展示；格局、旺衰与断语不在此工具中自动定论。" : "Calendar facts and Da Yun rules are shown separately; this tool does not declare a single strength or pattern interpretation."}</p>
    </section>
  )
}

function HourCandidates({ candidates, locale }: { candidates: MetaphysicsChart["birth_profile"]["hour_candidates"]; locale: "en" | "zh" }) {
  return <section className="rounded-md border border-border/50 p-4"><h3 className="text-sm font-semibold">{locale === "zh" ? "可能时柱" : "Possible hour pillars"}</h3><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? "时辰未定，因此不输出伪精确大运；晚子时单列以保留换日差异。" : "Da Yun is withheld while the birth hour is unknown; late Zi is listed separately because it can change the day pillar."}</p><div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-7">{candidates.map((candidate) => <div key={candidate.label} className="rounded border border-border/50 px-2 py-2 text-center"><p className="text-xs text-muted-foreground">{candidate.label}</p><p className="mt-1 font-semibold">{candidate.pillar}</p></div>)}</div></section>
}

function DayunPanel({ chart, locale }: { chart: MetaphysicsChart; locale: "en" | "zh" }) {
  const dayun = chart.birth_profile.dayun
  if (dayun.status === "not_requested") return null
  if (dayun.status === "requires_hour") return <section className="rounded-md border border-border/50 p-4"><h3 className="text-sm font-semibold">{locale === "zh" ? "大运" : "Da Yun"}</h3><p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? dayun.note : "The birth hour is uncertain, so the app withholds a falsely precise Da Yun start time and cycle schedule."}</p></section>
  return <section className="rounded-md border border-border/50 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="text-sm font-semibold">{locale === "zh" ? "大运" : "Da Yun"}</h3><p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? `${dayun.direction === "forward" ? "顺排" : "逆排"} · ${dayun.algorithm_note}` : `${dayun.direction === "forward" ? "Forward" : "Reverse"} · ${dayun.algorithm_note}`}</p></div>{dayun.start ? <p className="text-xs text-muted-foreground">{locale === "zh" ? "起运" : "Starts"}: {dayun.start.years}{locale === "zh" ? "年" : "y"} {dayun.start.months}{locale === "zh" ? "月" : "m"} {dayun.start.days}{locale === "zh" ? "日" : "d"} · {dayun.start.solar_date}</p> : null}</div>{dayun.crosscheck_matches === false ? <p className="mt-3 rounded border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">{locale === "zh" ? "两套历法引擎的四柱未完全一致，请先核对时区、真太阳时和换日规则。" : "The two calendar engines do not fully agree. Verify timezone, true-solar correction, and day-boundary rules."}</p> : null}<div className="mt-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-5">{dayun.cycles.map((cycle) => <article key={`${cycle.index}-${cycle.start_year}`} className="rounded border border-border/50 bg-surface-elevated px-3 py-3"><p className="font-semibold">{cycle.label}</p><p className="mt-1 text-xs text-muted-foreground">{cycle.start_age}–{cycle.end_age} {locale === "zh" ? "岁" : "years"}</p><p className="text-xs text-muted-foreground">{cycle.start_year}–{cycle.end_year}</p></article>)}</div></section>
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="rounded-md border border-border/50 bg-surface-elevated px-3 py-2"><p className="text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value}</p></div>
}

function SolarTermCountdown({ timestamp, locale }: { timestamp: string; locale: "en" | "zh" }) {
  const [remaining, setRemaining] = useState(() => Math.max(0, new Date(timestamp).getTime() - Date.now()))
  useEffect(() => {
    const timer = window.setInterval(() => setRemaining(Math.max(0, new Date(timestamp).getTime() - Date.now())), 1000)
    return () => window.clearInterval(timer)
  }, [timestamp])
  const seconds = Math.floor(remaining / 1000)
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  return <p className="mt-1 text-xs text-muted-foreground">{locale === "zh" ? `还有 ${days} 天 ${hours} 时 ${minutes} 分 ${rest} 秒` : `${days}d ${hours}h ${minutes}m ${rest}s remaining`}</p>
}

function ZiweiChart({ chart, horoscope, locale }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope | null; locale: "en" | "zh" }) {
  return <section className="space-y-4 rounded-lg border border-border/60 bg-surface p-3 sm:p-5">{horoscope ? <HoroscopeSummary horoscope={horoscope} locale={locale} /> : null}<div className="grid min-h-[52rem] grid-cols-4 grid-rows-4 gap-1 sm:gap-2">{chart.palaces.slice(0, 12).map((palace, index) => <PalaceCell key={`${palace.name}-${palace.earthlyBranch}`} palace={palace} position={PALACE_POSITIONS[index]} />)}<div className="col-start-2 col-end-4 row-start-2 row-end-4 flex flex-col items-center justify-center rounded-md border border-primary/30 bg-primary/8 p-4 text-center"><p className="text-2xl font-semibold">{chart.fiveElementsClass}</p><p className="mt-2 text-sm">{chart.chineseDate}</p><p className="mt-1 text-xs text-muted-foreground">{chart.lunarDate} · {chart.time} {chart.timeRange}</p><div className="mt-4 grid grid-cols-2 gap-4 text-sm"><div><p className="text-xs text-muted-foreground">{locale === "zh" ? "命主" : "Soul"}</p><p className="font-semibold">{chart.soul}</p></div><div><p className="text-xs text-muted-foreground">{locale === "zh" ? "身主" : "Body"}</p><p className="font-semibold">{chart.body}</p></div></div><p className="mt-4 text-[0.65rem] text-muted-foreground">iztro 2.5.8 · MIT</p></div></div><p className="text-[0.65rem] leading-5 text-muted-foreground">{locale === "zh" ? "星曜、四化与运限由 iztro 确定性排盘；流派设置已显式列出，解释层不混入排盘事实。" : "Stars, mutagens, and horoscope periods are deterministically generated by iztro; school settings remain explicit and separate from interpretation."}</p></section>
}

function HoroscopeSummary({ horoscope, locale }: { horoscope: IFunctionalHoroscope; locale: "en" | "zh" }) {
  const mutagenLabels = locale === "zh" ? ["禄", "权", "科", "忌"] : ["Prosperity", "Power", "Merit", "Obstacle"]
  return <section className="grid gap-3 rounded-md border border-border/50 bg-surface-elevated p-4 md:grid-cols-2"><div><p className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "大限" : "Decadal period"}</p><p className="mt-1 font-semibold">{horoscope.decadal.name} · {horoscope.decadal.heavenlyStem}{horoscope.decadal.earthlyBranch}</p><p className="mt-1 text-xs text-muted-foreground">{horoscope.solarDate} · {horoscope.lunarDate}</p></div><div><p className="text-xs font-semibold text-muted-foreground">{locale === "zh" ? "流年" : "Annual period"}</p><p className="mt-1 font-semibold">{horoscope.yearly.name} · {horoscope.yearly.heavenlyStem}{horoscope.yearly.earthlyBranch}</p><div className="mt-2 flex flex-wrap gap-1">{horoscope.yearly.mutagen.map((star, index) => <span key={`${star}-${index}`} className="rounded border border-primary/30 bg-primary/10 px-2 py-1 text-xs">{mutagenLabels[index]} · {star}</span>)}</div></div></section>
}

function PalaceCell({ palace, position }: { palace: IFunctionalPalace; position: readonly [number, number] }) {
  const stars = [...palace.majorStars, ...palace.minorStars]
  return <article style={{ gridColumnStart: position[0] + 1, gridRowStart: position[1] + 1 }} className="min-w-0 rounded-md border border-border/60 bg-surface-elevated p-2 sm:p-3"><div className="flex items-start justify-between gap-1"><p className="text-sm font-semibold">{palace.name}{palace.isBodyPalace ? " · 身" : ""}</p><span className="text-xs text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></div><div className="mt-2 flex flex-wrap gap-1">{stars.length ? stars.map((star, index) => <span key={`${star.name}-${index}`} className={cnStar(star.type)}>{star.name}{star.mutagen ? ` · 化${star.mutagen}` : ""}{star.brightness ? ` · ${star.brightness}` : ""}</span>) : <span className="text-xs text-muted-foreground">空宫</span>}</div>{palace.adjectiveStars.length ? <p className="mt-2 line-clamp-2 text-[0.65rem] leading-4 text-muted-foreground">{palace.adjectiveStars.map((star) => star.name).join(" · ")}</p> : null}<p className="mt-2 text-[0.65rem] text-muted-foreground">{palace.changsheng12}{palace.decadal?.range ? ` · ${palace.decadal.range[0]}–${palace.decadal.range[1]}` : ""}</p></article>
}

function cnStar(type?: string) { return `rounded px-1.5 py-0.5 text-[0.65rem] ${type === "major" ? "bg-primary/15 font-semibold text-primary" : "border border-border/50 text-foreground"}` }
function Loading() { return <div className="flex items-center justify-center gap-2 rounded-lg border border-border/60 bg-surface p-10 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Loading…</div> }
