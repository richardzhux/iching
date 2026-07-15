"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2, Sparkles } from "lucide-react"
import type { ConsumerIdentityProfile } from "@/components/tools/consumer-identity"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

type Locale = "en" | "zh"
type ComparisonKind = "bazi" | "ziwei"

export type ComparisonInput = {
  name: string
  birthLocal: string
  gender: "male" | "female"
  timezone: string
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  kind: ComparisonKind
  locale: Locale
  currentName: string
  currentProfile: ConsumerIdentityProfile
  onCalculate: (input: ComparisonInput) => Promise<ConsumerIdentityProfile>
}

const TIMEZONES = ["Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore", "Asia/Tokyo", "America/Los_Angeles", "America/New_York", "Europe/London"]

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(maximum, Math.max(minimum, value))
}

function subjectMap(profile: ConsumerIdentityProfile) {
  return new Map(profile.subjects.map((subject) => [subject.key, subject]))
}

function interactionIndex(left: ConsumerIdentityProfile, right: ConsumerIdentityProfile) {
  const rightSubjects = subjectMap(right)
  const pairs = left.subjects.flatMap((subject) => {
    const other = rightSubjects.get(subject.key)
    return other ? [[subject.score, other.score] as const] : []
  })
  if (!pairs.length) return Math.round((left.identity.main_score + right.identity.main_score) / 2)
  const sharedPower = pairs.reduce((total, [a, b]) => total + Math.min(a, b), 0) / pairs.length
  const complement = pairs.reduce((total, [a, b]) => total + Math.min(24, Math.abs(a - b)), 0) / pairs.length
  return Math.round(clamp(42 + sharedPower * 0.5 + complement * 0.22, 50, 98))
}

function comparisonHighlights(left: ConsumerIdentityProfile, right: ConsumerIdentityProfile, locale: Locale) {
  const rightSubjects = subjectMap(right)
  const pairs = left.subjects.flatMap((subject) => {
    const other = rightSubjects.get(subject.key)
    return other ? [{ left: subject, right: other, shared: Math.min(subject.score, other.score), gap: Math.abs(subject.score - other.score) }] : []
  })
  const shared = [...pairs].sort((a, b) => b.shared - a.shared)[0]
  const complement = [...pairs].sort((a, b) => b.gap - a.gap)[0]
  return {
    shared: shared ? (locale === "zh" ? `${shared.left.label}是两人的共同强项，最容易形成默契。` : `${shared.left.label} is your strongest shared lane.`) : "",
    complement: complement ? (locale === "zh" ? `${complement.left.label}差异最明显，也最容易形成互补与拉扯。` : `${complement.left.label} carries the biggest contrast and complement.`) : "",
  }
}

export function MetaphysicsComparisonDialog({ open, onOpenChange, kind, locale, currentName, currentProfile, onCalculate }: Props) {
  const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai"
  const [name, setName] = useState("")
  const [birthLocal, setBirthLocal] = useState("1990-01-01T12:00")
  const [gender, setGender] = useState<"male" | "female">("male")
  const [timezone, setTimezone] = useState(browserTimezone)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [otherProfile, setOtherProfile] = useState<ConsumerIdentityProfile | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
  }, [open])

  const highlights = useMemo(() => otherProfile ? comparisonHighlights(currentProfile, otherProfile, locale) : null, [currentProfile, locale, otherProfile])
  const index = otherProfile ? interactionIndex(currentProfile, otherProfile) : null
  const currentLabel = currentName || (locale === "zh" ? "我" : "Me")
  const otherLabel = name.trim() || (locale === "zh" ? "TA" : "Them")
  const timezoneOptions = TIMEZONES.includes(timezone) ? TIMEZONES : [timezone, ...TIMEZONES]

  async function calculate() {
    if (!birthLocal) return
    setLoading(true)
    setError(null)
    try {
      setOtherProfile(await onCalculate({ name: name.trim(), birthLocal, gender, timezone }))
    } catch (cause) {
      setError((cause as Error).message || (locale === "zh" ? "生成比较失败，请重试。" : "Comparison could not be generated."))
    } finally {
      setLoading(false)
    }
  }

  return <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-h-[92dvh] max-w-4xl overflow-y-auto p-0 sm:max-w-4xl">
      <DialogHeader className="border-b border-border/60 px-5 py-5 text-left sm:px-7">
        <DialogTitle className="text-2xl">{locale === "zh" ? "双人命盘比较" : "Compare two charts"}</DialogTitle>
        <DialogDescription>{locale === "zh" ? `用同一套${kind === "bazi" ? "八字" : "紫微"}指数，看见共同强项、互补张力与两人的结构组合。` : `Compare shared strengths, contrasts, and your combined ${kind === "bazi" ? "BaZi" : "Zi Wei"} signature.`}</DialogDescription>
      </DialogHeader>

      <div className="space-y-6 px-5 py-6 sm:px-7">
        <section className="grid gap-4 rounded-2xl bg-muted/35 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2"><label htmlFor="compare-name" className="text-sm font-semibold">{locale === "zh" ? "对方称呼" : "Name"}</label><Input id="compare-name" value={name} onChange={(event) => setName(event.target.value)} placeholder={locale === "zh" ? "选填" : "Optional"} /></div>
          <div className="space-y-2 sm:col-span-2 lg:col-span-1"><label htmlFor="compare-birth" className="text-sm font-semibold">{locale === "zh" ? "出生时间" : "Birth time"}</label><Input id="compare-birth" type="datetime-local" value={birthLocal} onChange={(event) => setBirthLocal(event.target.value)} /></div>
          <div className="space-y-2"><label id="compare-gender-label" className="text-sm font-semibold">{locale === "zh" ? "性别" : "Gender"}</label><Select value={gender} onValueChange={(value) => setGender(value as "male" | "female")}><SelectTrigger aria-labelledby="compare-gender-label"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="male">{locale === "zh" ? "男" : "Male"}</SelectItem><SelectItem value="female">{locale === "zh" ? "女" : "Female"}</SelectItem></SelectContent></Select></div>
          <div className="space-y-2"><label id="compare-timezone-label" className="text-sm font-semibold">{locale === "zh" ? "出生地时区" : "Birth timezone"}</label><Select value={timezone} onValueChange={setTimezone}><SelectTrigger aria-labelledby="compare-timezone-label"><SelectValue /></SelectTrigger><SelectContent>{timezoneOptions.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>
          <div className="flex items-end sm:col-span-2 lg:col-span-4"><Button type="button" className="w-full sm:w-auto" onClick={() => void calculate()} disabled={loading || !birthLocal}>{loading ? <Loader2 aria-hidden="true" className="mr-2 size-4 animate-spin" /> : <Sparkles aria-hidden="true" className="mr-2 size-4" />}{locale === "zh" ? "生成双人比较" : "Generate comparison"}</Button></div>
          {error ? <p role="alert" className="text-sm text-destructive sm:col-span-2 lg:col-span-4">{error}</p> : null}
        </section>

        {otherProfile ? <section className="overflow-hidden rounded-3xl border border-primary/25 bg-surface">
          <header className="imperial-highlight-panel border-0 border-b border-primary/20 px-5 py-6 shadow-none sm:px-7">
            <p className="kicker">{locale === "zh" ? "双人结构" : "TWO-CHART DYNAMIC"}</p>
            <h3 className="mt-2 text-2xl font-semibold sm:text-3xl">{currentProfile.identity.archetype_title} × {otherProfile.identity.archetype_title}</h3>
            <div className="mt-5 flex flex-wrap items-end justify-between gap-5"><div><p className="text-sm text-muted-foreground">{locale === "zh" ? "互动指数" : "Interaction index"}</p><p className="mt-1 text-6xl font-semibold tabular-nums text-primary">{index}</p></div><div className="max-w-xl space-y-2 text-sm leading-6"><p>{highlights?.shared}</p><p>{highlights?.complement}</p></div></div>
          </header>
          <div className="grid grid-cols-[minmax(5rem,0.7fr)_1fr_1fr] border-b border-border/55 px-4 py-3 text-xs font-semibold text-muted-foreground sm:px-6"><span>{locale === "zh" ? "主题" : "Theme"}</span><span className="text-center">{currentLabel}</span><span className="text-center">{otherLabel}</span></div>
          <div className="divide-y divide-border/55">{currentProfile.subjects.map((subject) => {
            const other = subjectMap(otherProfile).get(subject.key)
            if (!other) return null
            return <div key={subject.key} className="grid grid-cols-[minmax(5rem,0.7fr)_1fr_1fr] items-center gap-3 px-4 py-4 sm:px-6"><strong className="text-sm">{subject.label}</strong><ScoreBar value={subject.score} /><ScoreBar value={other.score} /></div>
          })}</div>
        </section> : null}
      </div>
    </DialogContent>
  </Dialog>
}

function ScoreBar({ value }: { value: number }) {
  return <div className="min-w-0 text-center"><strong className="text-xl tabular-nums text-primary">{Math.round(value)}</strong><div className="mx-auto mt-2 h-1.5 max-w-36 overflow-hidden rounded-full bg-muted"><span className="block h-full rounded-full bg-primary" style={{ width: `${clamp(value, 0, 100)}%` }} /></div></div>
}
