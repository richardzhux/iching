"use client"

import { useEffect, useMemo, useState } from "react"
import { Loader2, Sparkles } from "lucide-react"
import { describeConsumerSubject, type ConsumerIdentityProfile, type ConsumerSubjectPath } from "@/components/tools/consumer-identity"
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

function subjectMap(profile: ConsumerIdentityProfile) {
  return new Map(profile.subjects.map((subject) => [subject.key, subject]))
}

function comparisonHighlights(left: ConsumerIdentityProfile, right: ConsumerIdentityProfile, locale: Locale) {
  const rightSubjects = subjectMap(right)
  const pairs = left.subjects.flatMap((subject) => {
    const other = rightSubjects.get(subject.key)
    return other ? [{ key: subject.key, left: describeConsumerSubject(subject, locale), right: describeConsumerSubject(other, locale) }] : []
  })
  const shared = pairs.filter((pair) => pair.left.title === pair.right.title)
  const differences = pairs.filter((pair) => pair.left.title !== pair.right.title)
  const sharedFingerprints = left.fingerprints.filter((fingerprint) => right.fingerprints.some((candidate) => candidate.id === fingerprint.id || candidate.title === fingerprint.title)).slice(0, 3)
  const sharedSummary = sharedFingerprints.length
    ? sharedFingerprints.map((fingerprint) => fingerprint.title).join("、")
    : shared.length
      ? shared.map((pair) => `${pair.left.label}：${pair.left.title}`).join("、")
      : ""
  const differenceSummary = differences.slice(0, 2).map((pair) => `${pair.left.label}：${pair.left.title} × ${pair.right.title}`).join("；")

  return {
    pairs,
    shared: locale === "zh"
      ? sharedSummary || "没有完全相同的主导标签，两张盘的表达方式差异更鲜明。"
      : sharedSummary || "No dominant labels match exactly, so the two charts express themselves in distinctly different ways.",
    differences: locale === "zh"
      ? differenceSummary || "主要路径较接近，差异更多体现在具体结构与生活选择中。"
      : differenceSummary || "Your main paths are similar; differences are more likely to appear in specific structures and choices.",
    complement: locale === "zh"
      ? differences.length
        ? "差异不是谁高谁低：一种路径可以补上另一种路径不常使用的视角，也可能需要更主动地理解彼此节奏。"
        : "相近的表达路径更容易建立默契，也要留意不要把相同的习惯同时放大。"
      : differences.length
        ? "Difference is not a ranking: one path can add a perspective the other uses less often, while asking for more awareness of each other's rhythm."
        : "Similar paths can build quick rapport, while also amplifying the same habits if left unchecked.",
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
        <DialogDescription>{locale === "zh" ? `从同一套${kind === "bazi" ? "八字" : "紫微"}结构中，看见共同语言、不同路径与彼此节奏；不把两个人排出高低。` : `Compare shared language, different paths, and your combined ${kind === "bazi" ? "BaZi" : "Zi Wei"} rhythm without ranking either person.`}</DialogDescription>
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
            <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">{locale === "zh" ? "这份比较描述两张命盘如何表达，不用分数评价谁更好。" : "This comparison describes how two charts express themselves without scoring who is better."}</p>
          </header>
          <div className="grid gap-px border-b border-border/55 bg-border/55 sm:grid-cols-3">
            <ComparisonInsight title={locale === "zh" ? "共同结构" : "Shared structures"} body={highlights?.shared ?? ""} />
            <ComparisonInsight title={locale === "zh" ? "差异路径" : "Different paths"} body={highlights?.differences ?? ""} />
            <ComparisonInsight title={locale === "zh" ? "互补观察" : "Complementary view"} body={highlights?.complement ?? ""} />
          </div>
          <div className="grid grid-cols-[minmax(5rem,0.7fr)_1fr_1fr] border-b border-border/55 px-4 py-3 text-xs font-semibold text-muted-foreground sm:px-6"><span>{locale === "zh" ? "主题" : "Theme"}</span><span className="text-center">{currentLabel}</span><span className="text-center">{otherLabel}</span></div>
          <div className="divide-y divide-border/55">{highlights?.pairs.map((pair) => <PathComparisonRow key={pair.key} left={pair.left} right={pair.right} />)}</div>
        </section> : null}
      </div>
    </DialogContent>
  </Dialog>
}

function ComparisonInsight({ title, body }: { title: string; body: string }) {
  return <article className="min-w-0 bg-surface px-5 py-5"><h4 className="text-sm font-semibold text-primary">{title}</h4><p className="mt-2 text-sm leading-6 text-muted-foreground">{body}</p></article>
}

function PathComparisonRow({ left, right }: { left: ConsumerSubjectPath; right: ConsumerSubjectPath }) {
  return <div className="grid grid-cols-[minmax(5rem,0.7fr)_1fr_1fr] items-start gap-3 px-4 py-4 sm:px-6">
    <strong className="text-sm">{left.label}</strong>
    <PathCell path={left} />
    <PathCell path={right} />
  </div>
}

function PathCell({ path }: { path: ConsumerSubjectPath }) {
  return <div className="min-w-0 text-center"><strong className="text-sm leading-5 text-primary sm:text-base">{path.title}</strong><p className="mt-1 line-clamp-3 text-xs leading-5 text-muted-foreground">{path.description}</p></div>
}
