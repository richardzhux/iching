"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  ChevronDown,
  Download,
  Loader2,
  LogOut,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
} from "lucide-react"
import { toast } from "sonner"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useMetaphysicsChartHistoryQuery, useSessionHistoryQuery } from "@/lib/queries"
import { deleteMetaphysicsChart, deleteSession, fetchChatTranscript } from "@/lib/api"
import { useWorkspaceStore } from "@/lib/store"
import type { Locale } from "@/i18n/config"
import type { Messages } from "@/i18n/messages"
import type { MetaphysicsChartSummary, SessionPayload, SessionSummary } from "@/types/api"

const PROFILE_COPY = {
  en: {
    signedIn: "Signed in",
    accountLabel: "Account",
    readingArchiveBody: "Your private home for readings and personal charts. Reopen any record without starting over.",
    retentionNote: "A 365-day cloud retention limit applies to reading records, with up to 500 saved readings per account; deleting a reading also removes its follow-up transcript.",
    secureRecord: "Secure record",
    secureRecordBody: "Saved readings stay tied to your account and can be reopened from the casting desk.",
    savedReadings: "Saved readings",
    pageTitle: "Account & readings",
    readingArchive: "Saved readings",
    savedCharts: "Personal charts",
    followups: "Follow-up ready",
    library: "Explore the 64 hexagrams",
    workspace: "Cast a reading",
    summaryLabel: "Reading brief",
    noRecordsTitle: "No saved readings yet",
    noRecordsBody: "Complete a reading and it will be saved here for review and follow-up.",
    historyErrorTitle: "Saved readings could not load",
    historyErrorBody: "Your saved readings may still be intact. Retry before treating this as an empty history.",
    chartArchive: "BaZi & Zi Wei archive",
    chartArchiveBody: "Each chart is private to this account and reopens with its original birth data, rules, and result.",
    chartArchiveEmpty: "No personal charts yet",
    chartArchiveEmptyBody: "Generate a BaZi or Zi Wei chart and it will appear here automatically.",
    chartArchiveError: "Personal charts could not load. Retry before creating a duplicate.",
    anonymous: "Anonymous chart",
    baziChart: "BaZi",
    ziweiChart: "Zi Wei",
    dayPillar: "Day pillar",
    openChart: "Open chart",
    newChart: "New chart",
    confirmDeleteChart: "Delete this private chart permanently?",
    deletedChart: "Chart deleted",
    deleteChartFailed: "Chart could not be deleted. Try again.",
  },
  zh: {
    signedIn: "已登录",
    accountLabel: "账户",
    readingArchiveBody: "集中管理你的私人卦例与个人命盘，无需重新输入即可继续查看。",
    retentionNote: "云端卦例最长保留 365 天，每个账户最多 500 条；删除卦例也会同步删除其追问文本。",
    secureRecord: "安全记录",
    secureRecordBody: "已保存卦例仅绑定当前账户，可从起卦页面重新打开并继续追问。",
    savedReadings: "已保存",
    pageTitle: "账户与卦历",
    readingArchive: "已保存卦例",
    savedCharts: "个人命盘",
    followups: "可追问",
    library: "查阅六十四卦",
    workspace: "去起一卦",
    summaryLabel: "卦例概要",
    noRecordsTitle: "暂无已保存卦例",
    noRecordsBody: "完成一次起卦后，会保存在这里，方便日后回看与追问。",
    historyErrorTitle: "已保存卦例暂时无法读取",
    historyErrorBody: "这不代表记录为空。请先重试同步，再判断是否没有历史记录。",
    chartArchive: "八字与紫微档案",
    chartArchiveBody: "每张命盘仅当前账户可见，并保留原始出生资料、排盘规则与结果。",
    chartArchiveEmpty: "暂无个人命盘",
    chartArchiveEmptyBody: "生成八字或紫微命盘后，会自动保存在这里。",
    chartArchiveError: "个人命盘暂时无法读取，请先重试，避免重复建档。",
    anonymous: "匿名命主",
    baziChart: "八字",
    ziweiChart: "紫微",
    dayPillar: "日柱",
    openChart: "打开命盘",
    newChart: "新建命盘",
    confirmDeleteChart: "确定永久删除这张私人命盘吗？",
    deletedChart: "命盘已删除",
    deleteChartFailed: "命盘删除失败，请稍后重试。",
  },
} as const satisfies Record<Locale, Record<string, string>>

type ProfileCopy = (typeof PROFILE_COPY)[Locale]

type AccountSummaryPanelProps = {
  avatarUrl: string | null
  copy: ProfileCopy
  displayName: string
  email?: string | null
  messages: Messages
  followupCount: number
  chartCount: number
  sessionCount: number
  onSignOut: () => void
  toLocalePath: (path?: string) => string
}

type CloudHistoryPanelProps = {
  copy: ProfileCopy
  continuingId: string | null
  deletingId: string | null
  exportingId: string | null
  isFetching: boolean
  isLoading: boolean
  historyError: Error | null
  locale: Locale
  messages: Messages
  onContinue: (session: SessionSummary) => void
  onDelete: (session: SessionSummary) => void
  onDownload: (session: SessionSummary) => void
  onRefresh: () => void
  sessions: SessionSummary[]
  toLocalePath: (path?: string) => string
}

type ChartArchivePanelProps = {
  charts: MetaphysicsChartSummary[]
  copy: ProfileCopy
  deletingId: string | null
  isFetching: boolean
  isLoading: boolean
  locale: Locale
  loadError: Error | null
  onDelete: (chart: MetaphysicsChartSummary) => void
  onOpen: (chart: MetaphysicsChartSummary) => void
  onRefresh: () => void
  toLocalePath: (path?: string) => string
}

type AuthPanelProps = {
  authMode: "signIn" | "signUp"
  busy: boolean
  email: string
  messages: Messages
  password: string
  setAuthMode: React.Dispatch<React.SetStateAction<"signIn" | "signUp">>
  setEmail: (value: string) => void
  setPassword: (value: string) => void
  onEmailSubmit: (event: React.FormEvent<HTMLFormElement>) => void
  onGoogleSignIn: () => void
}

type SessionRecordCardProps = {
  continuingId: string | null
  deletingId: string | null
  exportingId: string | null
  copy: ProfileCopy
  locale: Locale
  messages: Messages
  onContinue: (session: SessionSummary) => void
  onDelete: (session: SessionSummary) => void
  onDownload: (session: SessionSummary) => void
  session: SessionSummary
}

function formatTimestamp(value: string | null | undefined, locale: Locale) {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString(locale === "zh" ? "zh-CN" : "en")
}

function safeAuthError(_error: unknown, messages: Messages) {
  return messages.profile.authError
}

function AccountSummaryPanel({
  avatarUrl,
  copy,
  displayName,
  email,
  followupCount,
  chartCount,
  messages,
  onSignOut,
  sessionCount,
  toLocalePath,
}: AccountSummaryPanelProps) {
  return (
    <div className="autumn-account-summary flex min-w-0 flex-col gap-3 sm:items-end">
      <div className="flex min-w-0 items-center gap-3">
        {avatarUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={avatarUrl} alt={displayName} className="size-9 shrink-0 rounded-full object-cover ring-1 ring-border/70" />
        ) : (
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full border border-border/60 bg-surface-elevated text-sm font-semibold text-primary" aria-hidden="true">
            {displayName?.[0]?.toUpperCase()}
          </div>
        )}
        <div className="min-w-0 sm:text-right">
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm sm:justify-end">
            <span className="max-w-64 truncate font-semibold text-foreground" title={email || displayName}>{displayName}</span>
            <span className="text-xs text-muted-foreground">{copy.signedIn}</span>
          </p>
          <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground sm:justify-end">
            <span>{copy.savedReadings} <strong className="font-medium text-foreground">{sessionCount}</strong></span>
            <span>{copy.savedCharts} <strong className="font-medium text-foreground">{chartCount}</strong></span>
            <span>{copy.followups} <strong className="font-medium text-foreground">{followupCount}</strong></span>
          </p>
        </div>
      </div>
      <nav className="autumn-account-links flex flex-wrap items-center gap-x-3 gap-y-2 text-xs sm:justify-end" aria-label={copy.accountLabel}>
        <Link className="inline-flex items-center gap-1 text-primary hover:underline" href={toLocalePath("/app")}>
          {copy.workspace}<ArrowRight className="size-3.5" />
        </Link>
        <Link className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground" href={toLocalePath("/library")}>
          <BookOpen className="size-3.5" />{copy.library}
        </Link>
        <Link className="text-muted-foreground hover:text-foreground" href={toLocalePath("/")}>{messages.common.back}</Link>
        <Button type="button" size="sm" variant="ghost" className="h-7 px-1 text-xs" onClick={onSignOut}>
          <LogOut className="size-3.5" />{messages.common.signOut}
        </Button>
      </nav>
    </div>
  )
}

function ChartArchivePanel({
  charts,
  copy,
  deletingId,
  isFetching,
  isLoading,
  locale,
  loadError,
  onDelete,
  onOpen,
  onRefresh,
  toLocalePath,
}: ChartArchivePanelProps) {
  return (
    <section className="autumn-profile-archive" aria-labelledby="chart-archive-title">
      <div className="flex items-center justify-between gap-3 border-b border-border/60 py-3">
        <div>
          <h2 id="chart-archive-title" className="text-sm font-semibold text-foreground">{copy.chartArchive}</h2>
        </div>
        <Button asChild size="sm">
          <Link href={`${toLocalePath("/tools")}?tab=bazi`}>
            <Plus className="size-4" />
            {copy.newChart}
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="flex min-h-28 items-center justify-center gap-2 border-b border-border/60 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {locale === "zh" ? "正在读取命盘…" : "Loading charts…"}
        </div>
      ) : loadError ? (
        <div className="border-b border-border/60 py-5">
          <p className="text-sm text-muted-foreground">{copy.chartArchiveError}</p>
          <Button type="button" size="sm" variant="outline" className="mt-3" disabled={isFetching} onClick={onRefresh}>
            <RefreshCw className="size-4" />
            {locale === "zh" ? "重新同步" : "Retry"}
          </Button>
        </div>
      ) : charts.length === 0 ? (
        <div className="border-b border-border/60 py-6">
          <p className="font-semibold text-foreground">{copy.chartArchiveEmpty}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.chartArchiveEmptyBody}</p>
        </div>
      ) : (
        <div className="divide-y divide-border/60 border-b border-border/60">
          {charts.map((chart) => {
            const isBazi = chart.chart_type === "bazi"
            const displayName = chart.display_name?.trim() || copy.anonymous
            return (
              <article key={chart.id} className="autumn-profile-record flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
                <button type="button" className="min-w-0 flex-1 text-left outline-none focus-visible:ring-2 focus-visible:ring-primary" onClick={() => onOpen(chart)}>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary">
                      {isBazi ? <CalendarDays className="size-3.5" /> : <Sparkles className="size-3.5" />}
                      {isBazi ? copy.baziChart : copy.ziweiChart}
                    </span>
                    <span className="text-xs text-muted-foreground">{formatTimestamp(chart.updated_at, locale)}</span>
                  </div>
                  <h3 className="mt-1 truncate text-sm font-semibold text-foreground">{displayName}</h3>
                  <p className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>{chart.birth_date}</span>
                    {chart.day_pillar ? <span>{copy.dayPillar} <strong className="font-semibold text-primary">{chart.day_pillar}</strong></span> : null}
                    {chart.birth_place ? <span className="truncate">{chart.birth_place}</span> : null}
                  </p>
                </button>
                <div className="flex shrink-0 items-center gap-1">
                  <Button type="button" size="sm" variant="ghost" onClick={() => onOpen(chart)}>{copy.openChart}</Button>
                  <Button type="button" size="icon-sm" variant="ghost" aria-label={copy.confirmDeleteChart} disabled={deletingId === chart.id} onClick={() => onDelete(chart)}>
                    {deletingId === chart.id ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
                  </Button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

function CloudHistoryPanel({
  continuingId,
  copy,
  deletingId,
  exportingId,
  isFetching,
  isLoading,
  historyError,
  locale,
  messages,
  onContinue,
  onDelete,
  onDownload,
  onRefresh,
  sessions,
  toLocalePath,
}: CloudHistoryPanelProps) {
  const hasSessions = sessions.length > 0

  return (
    <section className="autumn-profile-archive" aria-labelledby="reading-archive-title">
      <div className="flex items-center justify-between gap-3 border-b border-border/60 py-3">
        <h2 id="reading-archive-title" className="text-sm font-semibold text-foreground">{copy.readingArchive}</h2>
        <Button type="button" size="sm" variant="ghost" disabled={isFetching} onClick={onRefresh}>
          <RefreshCw className={`size-3.5${isFetching ? " animate-spin" : ""}`} />
          {messages.profile.refresh}
        </Button>
      </div>

      {isLoading ? (
        <div className="mt-5 flex min-h-40 items-center justify-center gap-3 rounded-lg border border-border/60 bg-surface-elevated p-6 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {messages.profile.loadingSessions}
        </div>
      ) : historyError ? (
        <div className="imperial-highlight-panel mt-5 rounded-lg p-6">
          <p className="text-base font-semibold text-foreground">{copy.historyErrorTitle}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.historyErrorBody}</p>
          {process.env.NODE_ENV !== "production" && (
            <p className="mt-3 rounded-md border border-border/60 bg-surface px-3 py-2 text-xs text-muted-foreground">
              {historyError.message}
            </p>
          )}
          <Button type="button" variant="outline" className="mt-4" disabled={isFetching} onClick={onRefresh}>
            <RefreshCw className="size-4" />
            {messages.profile.refresh}
          </Button>
        </div>
      ) : !hasSessions ? (
        <div className="mt-5 rounded-lg border border-dashed border-border/70 bg-surface-elevated p-6">
          <p className="text-base font-semibold text-foreground">{copy.noRecordsTitle}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy.noRecordsBody}</p>
          <Button asChild className="mt-4">
            <Link href={toLocalePath("/app")}>{messages.nav.workspace}</Link>
          </Button>
        </div>
      ) : (
        <div className="divide-y divide-border/60">
          {sessions.map((session) => (
            <SessionRecordCard
              key={session.session_id}
              continuingId={continuingId}
              copy={copy}
              deletingId={deletingId}
              exportingId={exportingId}
              locale={locale}
              messages={messages}
              onContinue={onContinue}
              onDelete={onDelete}
              onDownload={onDownload}
              session={session}
            />
          ))}
        </div>
      )}
      <p className="mt-5 border-t border-border/60 pt-4 text-xs leading-5 text-muted-foreground">{copy.retentionNote}</p>
    </section>
  )
}

function SessionRecordCard({
  continuingId,
  copy,
  deletingId,
  exportingId,
  locale,
  messages,
  onContinue,
  onDelete,
  onDownload,
  session,
}: SessionRecordCardProps) {
  const isExporting = exportingId === session.session_id
  const isContinuing = continuingId === session.session_id
  const isDeleting = deletingId === session.session_id
  const recordTitle = session.summary_text?.match(/(?:^|\n)(?:问题|Question)[:：]\s*(.+)/i)?.[1]?.trim() || session.topic_label || messages.workspace.history.noTopic

  return (
    <article className="autumn-profile-record py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-foreground" title={recordTitle}>
            {recordTitle}
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>{formatTimestamp(session.created_at, locale)}</span>
            <span>{session.method_label ?? messages.workspace.history.noMethod}</span>
            {session.followup_available && <span className="text-primary">{copy.followups}</span>}
          </p>
        </div>
        <div className="autumn-record-actions flex shrink-0 items-center gap-1">
          <Button type="button" size="sm" variant="ghost" disabled={!session.followup_available || isContinuing} onClick={() => onContinue(session)} title={!session.followup_available ? messages.profile.noFollowupHint : undefined}>
            {isContinuing ? <Loader2 className="size-3.5 animate-spin" /> : <ArrowRight className="size-3.5" />}
            {isContinuing ? messages.profile.openingSession : messages.profile.openSession}
          </Button>
          <Button type="button" size="icon-sm" variant="ghost" disabled={isExporting} onClick={() => onDownload(session)} aria-label={isExporting ? messages.profile.downloading : messages.profile.download} title={messages.profile.download}>
            {isExporting ? <Loader2 className="size-3.5 animate-spin" /> : <Download className="size-3.5" />}
          </Button>
          <Button type="button" size="icon-sm" variant="ghost" className="text-muted-foreground hover:text-destructive" disabled={isDeleting} onClick={() => onDelete(session)} aria-label={messages.common.delete} title={messages.common.delete}>
            {isDeleting ? <Loader2 className="size-3.5 animate-spin" /> : <Trash2 className="size-3.5" />}
          </Button>
        </div>
      </div>
      <details className="autumn-record-details group mt-2">
        <summary className="flex w-fit cursor-pointer list-none items-center gap-1 rounded-sm text-xs text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary [&::-webkit-details-marker]:hidden">
          <ChevronDown className="size-3 transition-transform group-open:rotate-180" />{copy.summaryLabel}
        </summary>
        <div className="mt-3 border-l border-border/60 pl-3">
          <p className="whitespace-pre-wrap break-words text-sm leading-6 text-foreground/90">{session.summary_text ?? messages.profile.noSummary}</p>
          {!session.ai_enabled && session.followup_available && (
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{messages.profile.aiBootstrapHint}</p>
          )}
          {!session.followup_available && (
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{messages.profile.noFollowupHint}</p>
          )}
        </div>
      </details>
    </article>
  )
}

function AuthPanel({
  authMode,
  busy,
  email,
  messages,
  onEmailSubmit,
  onGoogleSignIn,
  password,
  setAuthMode,
  setEmail,
  setPassword,
}: AuthPanelProps) {
  return (
    <section className="autumn-study autumn-auth mx-auto w-full max-w-3xl border-y border-border/60 bg-surface p-6 sm:p-10">
      <div className="text-center">
        <p className="kicker">{messages.profile.kicker}</p>
        <h1 className="autumn-page-title">
          {authMode === "signIn" ? messages.profile.authCardSignIn : messages.profile.authCardSignUp}
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-muted-foreground">{messages.profile.authCardDescription}</p>
      </div>

      <ul className="mx-auto mt-6 grid max-w-2xl gap-3 border-y border-border/60 py-5 text-sm text-foreground sm:grid-cols-3">
        {messages.profile.authBenefits.map((benefit) => (
          <li key={benefit} className="flex items-start gap-2 px-2">
            <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
            <span>{benefit}</span>
          </li>
        ))}
      </ul>

      <div className="mx-auto mt-6 max-w-md">
        <Button type="button" className="min-h-11 w-full" disabled={busy} onClick={onGoogleSignIn}>
          {messages.common.continueWithGoogle}
        </Button>

        <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground" aria-hidden="true">
          <span className="h-px flex-1 bg-border" />
          <span>{authMode === "signIn" ? messages.common.signIn : messages.common.signUp}</span>
          <span className="h-px flex-1 bg-border" />
        </div>

        <form onSubmit={onEmailSubmit} className="space-y-4">
          <div>
            <label htmlFor="profile-email" className="mb-2 block text-sm font-medium text-foreground">
              {messages.common.email}
            </label>
            <Input id="profile-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div>
            <label htmlFor="profile-password" className="mb-2 block text-sm font-medium text-foreground">
              {messages.common.password}
            </label>
            <Input
              id="profile-password"
              type="password"
              autoComplete={authMode === "signIn" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <Button type="submit" className="min-h-11 w-full justify-between" disabled={busy}>
            {busy ? messages.profile.submitBusy : authMode === "signIn" ? messages.common.signIn : messages.common.signUp}
            <ArrowRight className="size-4" />
          </Button>
        </form>

        <button
          type="button"
          className="mt-4 min-h-11 w-full rounded-md px-3 text-sm font-semibold text-primary outline-none underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring"
          onClick={() => setAuthMode((mode) => (mode === "signIn" ? "signUp" : "signIn"))}
        >
          {authMode === "signIn" ? messages.profile.switchToSignUp : messages.profile.switchToSignIn}
        </button>
      </div>
      <p className="mx-auto mt-5 max-w-xl text-center text-xs leading-5 text-muted-foreground">{messages.profile.privacyCopy}</p>
    </section>
  )
}

export default function ProfilePage() {
  const auth = useAuthContext()
  const { locale, messages, toLocalePath } = useI18n()
  const historyQuery = useSessionHistoryQuery(auth.accessToken ?? null)
  const chartHistoryQuery = useMetaphysicsChartHistoryQuery(auth.accessToken ?? null)
  const router = useRouter()
  const setResult = useWorkspaceStore((state) => state.setResult)
  const [authMode, setAuthMode] = useState<"signIn" | "signUp">("signIn")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [exportingId, setExportingId] = useState<string | null>(null)
  const [continuingId, setContinuingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deletingChartId, setDeletingChartId] = useState<string | null>(null)
  const copy = PROFILE_COPY[locale]
  const sessions = useMemo(() => historyQuery.data?.sessions ?? [], [historyQuery.data?.sessions])
  const charts = useMemo(() => chartHistoryQuery.data?.charts ?? [], [chartHistoryQuery.data?.charts])
  const profileName = auth.displayName ?? auth.user?.email ?? messages.profileMenu.guestMode
  const profileAvatar = auth.avatarUrl ?? null
  const followupCount = useMemo(() => sessions.filter((session) => session.followup_available).length, [sessions])

  async function handleDownload(summary: SessionSummary) {
    if (!auth.accessToken) {
      toast.error(messages.workspace.chat.askAfterLogin)
      return
    }
    setExportingId(summary.session_id)
    try {
      const transcript = await fetchChatTranscript(summary.session_id, auth.accessToken)
      const snapshot = transcript.payload_snapshot
      const lines: string[] = []
      lines.push(`${messages.workspace.results.baziTimeLabel}: ${formatTimestamp(snapshot?.session_dict?.["current_time_str"] as string, locale)}`)
      lines.push("")
      if (snapshot?.summary_text) {
        lines.push(messages.workspace.results.summaryLabel)
        lines.push(snapshot.summary_text.trim())
        lines.push("")
      } else if (transcript.summary_text) {
        lines.push(messages.workspace.results.summaryLabel)
        lines.push(transcript.summary_text.trim())
        lines.push("")
      }
      if (snapshot?.hex_text) {
        lines.push(messages.workspace.history.hexLabel)
        lines.push(snapshot.hex_text.trim())
        lines.push("")
      }
      if (snapshot?.ai_text || transcript.initial_ai_text) {
        lines.push(messages.workspace.history.aiLabel)
        lines.push((snapshot?.ai_text || transcript.initial_ai_text || "").trim())
        lines.push("")
      }
      if (transcript.messages.length) {
        lines.push(messages.workspace.chat.title)
        transcript.messages.forEach((message, index) => {
          const created = message.created_at ? ` @ ${formatTimestamp(message.created_at, locale)}` : ""
          lines.push(`${index + 1}. ${message.role === "assistant" ? "AI" : messages.profile.userLabel}${created}`)
          lines.push(message.content.trim())
          lines.push("")
        })
      }
      const blob = new Blob([lines.join("\n")], {
        type: "text/plain;charset=utf-8",
      })
      triggerDownload(blob, `session-${summary.session_id}.txt`)
    } catch {
      toast.error(messages.profile.exportFailed)
    } finally {
      setExportingId(null)
    }
  }

  async function handleContinue(session: SessionSummary) {
    if (!auth.accessToken) {
      toast.error(messages.workspace.chat.askAfterLogin)
      return
    }
    setContinuingId(session.session_id)
    try {
      const transcript = await fetchChatTranscript(session.session_id, auth.accessToken)
      if (!transcript.payload_snapshot) {
        throw new Error(messages.profile.noFollowupHint)
      }
      setResult(transcript.payload_snapshot as SessionPayload)
      router.push(toLocalePath("/reading"))
    } catch {
      toast.error(messages.profile.openFailed)
    } finally {
      setContinuingId(null)
    }
  }

  async function handleDelete(session: SessionSummary) {
    if (!auth.accessToken) {
      toast.error(messages.workspace.chat.askAfterLogin)
      return
    }
    if (!confirm(messages.profile.confirmDelete)) {
      return
    }
    setDeletingId(session.session_id)
    try {
      await deleteSession(session.session_id, auth.accessToken)
      toast.success(messages.profile.deletedToast)
      historyQuery.refetch()
    } catch {
      toast.error(messages.profile.deleteFailed)
    } finally {
      setDeletingId(null)
    }
  }

  function handleOpenChart(chart: MetaphysicsChartSummary) {
    router.push(`${toLocalePath("/tools")}?tab=${chart.chart_type}&chart=${chart.id}`)
  }

  async function handleDeleteChart(chart: MetaphysicsChartSummary) {
    if (!auth.accessToken || !confirm(copy.confirmDeleteChart)) return
    setDeletingChartId(chart.id)
    try {
      await deleteMetaphysicsChart(chart.id, auth.accessToken)
      toast.success(copy.deletedChart)
      await chartHistoryQuery.refetch()
    } catch {
      toast.error(copy.deleteChartFailed)
    } finally {
      setDeletingChartId(null)
    }
  }

  function triggerDownload(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(url)
  }

  async function handleAuthSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email || !password) {
      toast.error(messages.profile.emailPasswordRequired)
      return
    }
    setBusy(true)
    try {
      if (authMode === "signIn") {
        await auth.signIn(email, password)
        toast.success(messages.profile.loginSuccess)
      } else {
        await auth.signUp(email, password)
        toast.success(messages.profile.signupSuccess)
      }
      setEmail("")
      setPassword("")
    } catch (error) {
      toast.error(safeAuthError(error, messages))
    } finally {
      setBusy(false)
    }
  }

  async function handleGoogleSignIn() {
    setBusy(true)
    try {
      await auth.signInWithProvider("google")
    } catch (error) {
      toast.error(safeAuthError(error, messages))
    } finally {
      setBusy(false)
    }
  }

  async function handleSignOut() {
    try {
      await auth.signOut()
      toast.success(messages.profileMenu.signedOutToast)
    } catch {
      toast.error(messages.profileMenu.signOutFailed)
    }
  }

  if (auth.loading) {
    return (
      <div className="mx-auto flex min-h-[28vh] w-full max-w-3xl items-center justify-center gap-3 p-8 text-sm text-muted-foreground" role="status">
        <Loader2 className="size-4 animate-spin" />
        {messages.profile.authLoading}
      </div>
    )
  }

  return auth.user ? (
    <div className="autumn-study autumn-profile mx-auto w-full max-w-7xl">
      <header className="autumn-profile-header flex flex-col gap-4 border-b border-border/60 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="autumn-profile-title shrink-0 text-2xl font-semibold tracking-tight text-foreground">{copy.pageTitle}</h1>
        <AccountSummaryPanel
          avatarUrl={profileAvatar}
          copy={copy}
          displayName={profileName}
          email={auth.user.email}
          followupCount={followupCount}
          chartCount={charts.length}
          messages={messages}
          onSignOut={handleSignOut}
          sessionCount={sessions.length}
          toLocalePath={toLocalePath}
        />
      </header>

      <Tabs defaultValue="charts" className="autumn-profile-tabs mt-3">
        <TabsList className="w-full justify-start gap-5" aria-label={copy.pageTitle}>
          <TabsTrigger value="charts" className="flex-none">
            {copy.chartArchive}<span className="text-xs tabular-nums text-muted-foreground">{charts.length}</span>
          </TabsTrigger>
          <TabsTrigger value="readings" className="flex-none">
            {copy.readingArchive}<span className="text-xs tabular-nums text-muted-foreground">{sessions.length}</span>
          </TabsTrigger>
        </TabsList>
        <TabsContent value="charts">
          <ChartArchivePanel
            charts={charts}
            copy={copy}
            deletingId={deletingChartId}
            isFetching={chartHistoryQuery.isFetching}
            isLoading={chartHistoryQuery.isLoading}
            locale={locale}
            loadError={chartHistoryQuery.error instanceof Error ? chartHistoryQuery.error : null}
            onDelete={handleDeleteChart}
            onOpen={handleOpenChart}
            onRefresh={() => chartHistoryQuery.refetch()}
            toLocalePath={toLocalePath}
          />
        </TabsContent>
        <TabsContent value="readings">
          <CloudHistoryPanel
            continuingId={continuingId}
            copy={copy}
            deletingId={deletingId}
            exportingId={exportingId}
            isFetching={historyQuery.isFetching}
            isLoading={historyQuery.isLoading}
            historyError={historyQuery.error instanceof Error ? historyQuery.error : null}
            locale={locale}
            messages={messages}
            onContinue={handleContinue}
            onDelete={handleDelete}
            onDownload={handleDownload}
            onRefresh={() => historyQuery.refetch()}
            sessions={sessions}
            toLocalePath={toLocalePath}
          />
        </TabsContent>
      </Tabs>
    </div>
  ) : (
    <AuthPanel
      authMode={authMode}
      busy={busy}
      email={email}
      messages={messages}
      onEmailSubmit={handleAuthSubmit}
      onGoogleSignIn={handleGoogleSignIn}
      password={password}
      setAuthMode={setAuthMode}
      setEmail={setEmail}
      setPassword={setPassword}
    />
  )
}
