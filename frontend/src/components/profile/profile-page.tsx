"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowRight,
  BookOpen,
  Cloud,
  Download,
  History,
  Loader2,
  LogOut,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserRound,
} from "lucide-react"
import { toast } from "sonner"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useSessionHistoryQuery } from "@/lib/queries"
import { deleteSession, fetchChatTranscript } from "@/lib/api"
import { useWorkspaceStore } from "@/lib/store"
import type { Locale } from "@/i18n/config"
import type { Messages } from "@/i18n/messages"
import type { SessionPayload, SessionSummary } from "@/types/api"

const PROFILE_COPY = {
  en: {
    identity: "Private study desk",
    signedIn: "Signed in record",
    signedOut: "Guest record",
    accountLabel: "Account",
    readingArchive: "Reading archive",
    readingArchiveBody: "Saved casts, exports, and follow-up sessions are kept as a private working record.",
    secureRecord: "Secure record",
    secureRecordBody: "Cloud history stays tied to your authenticated account and can be reopened from the reading desk.",
    savedReadings: "Saved readings",
    followups: "Follow-up ready",
    authRequired: "Sign in required",
    library: "Source library",
    workspace: "Reading desk",
    summaryLabel: "Reading brief",
    accountAccess: "Account access",
    emailAccount: "Email account",
    googleAccount: "Google account",
    useEmail: "Use email credentials",
    noRecordsTitle: "No readings synced yet",
    noRecordsBody: "Create a reading from the workspace and it will appear here as a structured record.",
  },
  zh: {
    identity: "私人读易书桌",
    signedIn: "已登录档案",
    signedOut: "游客档案",
    accountLabel: "账户",
    readingArchive: "阅读档案",
    readingArchiveBody: "这里保存已同步的起卦、导出记录与可继续追问的会话，作为长期读易笔记。",
    secureRecord: "安全记录",
    secureRecordBody: "云端历史绑定当前登录账户，可从阅读桌重新打开并继续追问。",
    savedReadings: "已存阅读",
    followups: "可追问",
    authRequired: "需要登录",
    library: "经典学习库",
    workspace: "阅读桌",
    summaryLabel: "阅读概要",
    accountAccess: "账户入口",
    emailAccount: "邮箱账户",
    googleAccount: "Google 账户",
    useEmail: "使用邮箱密码",
    noRecordsTitle: "暂无同步记录",
    noRecordsBody: "在工作台完成一次起卦后，会以结构化记录出现在这里。",
  },
} as const satisfies Record<Locale, Record<string, string>>

type ProfileCopy = (typeof PROFILE_COPY)[Locale]

type AccountSummaryPanelProps = {
  avatarUrl: string | null
  copy: ProfileCopy
  displayName: string
  email?: string | null
  isSignedIn: boolean
  messages: Messages
  followupCount: number
  sessionCount: number
  toLocalePath: (path?: string) => string
}

type CloudHistoryPanelProps = {
  copy: ProfileCopy
  continuingId: string | null
  deletingId: string | null
  exportingId: string | null
  isFetching: boolean
  isLoading: boolean
  messages: Messages
  onContinue: (session: SessionSummary) => void
  onDelete: (session: SessionSummary) => void
  onDownload: (session: SessionSummary) => void
  onRefresh: () => void
  onSignOut: () => void
  sessions: SessionSummary[]
  toLocalePath: (path?: string) => string
}

type AuthPanelProps = {
  authMode: "signIn" | "signUp"
  busy: boolean
  copy: ProfileCopy
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
  messages: Messages
  onContinue: (session: SessionSummary) => void
  onDelete: (session: SessionSummary) => void
  onDownload: (session: SessionSummary) => void
  session: SessionSummary
}

function formatTimestamp(value?: string | null) {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function AccountSummaryPanel({
  avatarUrl,
  copy,
  displayName,
  email,
  followupCount,
  isSignedIn,
  messages,
  sessionCount,
  toLocalePath,
}: AccountSummaryPanelProps) {
  return (
    <aside className="space-y-4">
      <section className="rounded-lg border border-border/60 bg-surface p-5">
        <p className="kicker">{copy.accountLabel}</p>
        <div className="mt-4 flex items-start gap-3">
          {avatarUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={avatarUrl} alt={displayName} className="size-12 rounded-md object-cover ring-1 ring-border/70" />
          ) : (
            <div className="flex size-12 items-center justify-center rounded-md border border-border/60 bg-surface-elevated text-base font-semibold text-primary">
              {isSignedIn ? displayName?.[0]?.toUpperCase() : <UserRound className="size-5" />}
            </div>
          )}
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">{isSignedIn ? copy.signedIn : copy.signedOut}</p>
            <p className="mt-1 truncate text-sm text-muted-foreground">{displayName}</p>
            {email && <p className="mt-1 truncate text-xs text-muted-foreground">{email}</p>}
          </div>
        </div>
      </section>

      <section className="grid gap-2">
        <ProfileStatCard label={copy.savedReadings} value={isSignedIn ? String(sessionCount) : "-"} />
        <ProfileStatCard label={copy.followups} value={isSignedIn ? String(followupCount) : "-"} />
      </section>

      <section className="rounded-lg border border-border/60 bg-surface p-4">
        <p className="kicker">{copy.secureRecord}</p>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{copy.secureRecordBody}</p>
      </section>

      <nav className="grid gap-2">
        <Button asChild variant="outline" className="justify-between">
          <Link href={toLocalePath("/app")}>
            {copy.workspace}
            <ArrowRight className="size-4" />
          </Link>
        </Button>
        <Button asChild variant="outline" className="justify-between">
          <Link href={toLocalePath("/library")}>
            {copy.library}
            <BookOpen className="size-4" />
          </Link>
        </Button>
        <Button asChild variant="ghost" className="justify-between">
          <Link href={toLocalePath("/")}>
            {messages.common.back}
            <ArrowRight className="size-4" />
          </Link>
        </Button>
      </nav>
    </aside>
  )
}

function ProfileStatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/60 bg-surface p-4">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-foreground">{value}</p>
    </div>
  )
}

function CloudHistoryPanel({
  continuingId,
  copy,
  deletingId,
  exportingId,
  isFetching,
  isLoading,
  messages,
  onContinue,
  onDelete,
  onDownload,
  onRefresh,
  onSignOut,
  sessions,
  toLocalePath,
}: CloudHistoryPanelProps) {
  const hasSessions = sessions.length > 0

  return (
    <section className="rounded-lg border border-border/60 bg-surface p-5">
      <div className="flex flex-col gap-4 border-b border-border/60 pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="kicker">{copy.readingArchive}</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">{messages.profile.cloudHistoryTitle}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{copy.readingArchiveBody}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" disabled={isFetching} onClick={onRefresh}>
            <RefreshCw className="size-4" />
            {messages.profile.refresh}
          </Button>
          <Button type="button" variant="ghost" onClick={onSignOut}>
            <LogOut className="size-4" />
            {messages.common.signOut}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="mt-5 flex min-h-40 items-center justify-center gap-3 rounded-lg border border-border/60 bg-surface-elevated p-6 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {messages.profile.loadingSessions}
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
        <div className="mt-5 space-y-3">
          {sessions.map((session) => (
            <SessionRecordCard
              key={session.session_id}
              continuingId={continuingId}
              copy={copy}
              deletingId={deletingId}
              exportingId={exportingId}
              messages={messages}
              onContinue={onContinue}
              onDelete={onDelete}
              onDownload={onDownload}
              session={session}
            />
          ))}
        </div>
      )}
    </section>
  )
}

function SessionRecordCard({
  continuingId,
  copy,
  deletingId,
  exportingId,
  messages,
  onContinue,
  onDelete,
  onDownload,
  session,
}: SessionRecordCardProps) {
  const isExporting = exportingId === session.session_id
  const isContinuing = continuingId === session.session_id
  const isDeleting = deletingId === session.session_id

  return (
    <article className="rounded-lg border border-border/60 bg-surface-elevated p-4">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-md border border-border/60 bg-surface px-2 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {messages.profile.sessionLabel}
            </span>
            <span className="rounded-md border border-border/60 bg-surface px-2 py-1 text-[11px] text-muted-foreground">
              {formatTimestamp(session.created_at)}
            </span>
            {session.followup_available && (
              <span className="rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-[11px] font-semibold text-primary">
                {copy.followups}
              </span>
            )}
          </div>
          <h3 className="mt-3 text-base font-semibold text-foreground">
            {session.topic_label ?? messages.workspace.history.noTopic}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {session.method_label ?? messages.workspace.history.noMethod}
          </p>
          {(session.user_display_name || session.user_email) && (
            <p className="mt-2 text-xs text-muted-foreground">
              {messages.profile.userLabel}: {session.user_display_name ?? "-"} · {session.user_email ?? "-"}
            </p>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <Button type="button" size="sm" variant="outline" disabled={isExporting} onClick={() => onDownload(session)}>
            <Download className="size-4" />
            {isExporting ? messages.profile.downloading : messages.profile.download}
          </Button>
          {session.followup_available ? (
            <Button type="button" size="sm" variant="ghost" disabled={isContinuing} onClick={() => onContinue(session)}>
              <MessageSquare className="size-4" />
              {isContinuing ? messages.profile.openingSession : messages.profile.openSession}
            </Button>
          ) : (
            <Button type="button" size="sm" variant="ghost" disabled>
              <MessageSquare className="size-4" />
              {messages.profile.unavailableFollowup}
            </Button>
          )}
          <Button type="button" size="icon-sm" variant="destructive" disabled={isDeleting} onClick={() => onDelete(session)} aria-label={messages.common.delete}>
            {isDeleting ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
          </Button>
        </div>
      </div>

      <div className="mt-4 rounded-md border border-border/50 bg-surface p-3">
        <p className="kicker">{copy.summaryLabel}</p>
        <p className="mt-3 max-h-28 overflow-y-auto whitespace-pre-wrap text-sm leading-6 text-foreground/90">
          {session.summary_text ?? messages.profile.noSummary}
        </p>
      </div>

      {!session.ai_enabled && session.followup_available && (
        <p className="mt-3 text-xs leading-5 text-muted-foreground">{messages.profile.aiBootstrapHint}</p>
      )}
      {!session.followup_available && (
        <p className="mt-3 text-xs leading-5 text-muted-foreground">{messages.profile.noFollowupHint}</p>
      )}
    </article>
  )
}

function AuthPanel({
  authMode,
  busy,
  copy,
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
    <section className="rounded-lg border border-border/60 bg-surface p-5">
      <div className="border-b border-border/60 pb-5">
        <p className="kicker">{copy.accountAccess}</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-foreground">
          {authMode === "signIn" ? messages.profile.authCardSignIn : messages.profile.authCardSignUp}
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{messages.profile.authCardDescription}</p>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_16rem]">
        <form onSubmit={onEmailSubmit} className="space-y-3">
          <p className="text-sm font-semibold text-foreground">{copy.emailAccount}</p>
          <Input type="email" placeholder={messages.common.email} value={email} onChange={(event) => setEmail(event.target.value)} />
          <Input
            type="password"
            placeholder={messages.common.password}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button type="submit" className="w-full justify-between" disabled={busy}>
            {busy ? messages.profile.submitBusy : authMode === "signIn" ? messages.common.signIn : messages.common.signUp}
            <ArrowRight className="size-4" />
          </Button>
          <Button type="button" variant="outline" className="w-full" disabled={busy} onClick={onGoogleSignIn}>
            {messages.common.continueWithGoogle}
          </Button>
        </form>

        <aside className="rounded-lg border border-border/60 bg-surface-elevated p-4">
          <div className="flex size-10 items-center justify-center rounded-md border border-border/60 bg-surface text-primary">
            <ShieldCheck className="size-5" />
          </div>
          <p className="mt-4 text-sm font-semibold text-foreground">{copy.googleAccount}</p>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{messages.profile.subtitleSignedOut}</p>
          <button
            type="button"
            className="mt-4 text-sm font-semibold text-primary underline-offset-4 hover:underline"
            onClick={() => setAuthMode((mode) => (mode === "signIn" ? "signUp" : "signIn"))}
          >
            {authMode === "signIn" ? messages.profile.switchToSignUp : messages.profile.switchToSignIn}
          </button>
        </aside>
      </div>
    </section>
  )
}

export default function ProfilePage() {
  const auth = useAuthContext()
  const { locale, messages, toLocalePath } = useI18n()
  const historyQuery = useSessionHistoryQuery(auth.accessToken ?? null)
  const router = useRouter()
  const setResult = useWorkspaceStore((state) => state.setResult)
  const [authMode, setAuthMode] = useState<"signIn" | "signUp">("signIn")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [busy, setBusy] = useState(false)
  const [exportingId, setExportingId] = useState<string | null>(null)
  const [continuingId, setContinuingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const copy = PROFILE_COPY[locale]
  const sessions = useMemo(() => historyQuery.data?.sessions ?? [], [historyQuery.data?.sessions])
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
      lines.push(`${messages.workspace.results.baziTimeLabel}: ${formatTimestamp(snapshot?.session_dict?.["current_time_str"] as string)}`)
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
          const created = message.created_at ? ` @ ${formatTimestamp(message.created_at)}` : ""
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
      router.push(toLocalePath("/app"))
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
      toast.error((error as Error).message || messages.common.unknownError)
    } finally {
      setBusy(false)
    }
  }

  async function handleGoogleSignIn() {
    setBusy(true)
    try {
      await auth.signInWithProvider("google")
    } catch (error) {
      toast.error((error as Error).message || messages.common.unknownError)
    } finally {
      setBusy(false)
    }
  }

  async function handleSignOut() {
    try {
      await auth.signOut()
      toast.success(messages.profileMenu.signedOutToast)
    } catch (error) {
      toast.error((error as Error).message || messages.common.unknownError)
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-6">
      <header className="grid gap-6 rounded-lg border border-border/60 bg-surface p-6 lg:grid-cols-[1fr_18rem] lg:items-end">
        <div>
          <p className="kicker">{messages.profile.kicker}</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-foreground">{messages.profile.title}</h1>
          <p className="mt-3 max-w-3xl text-base leading-7 text-muted-foreground">
            {auth.user ? copy.readingArchiveBody : messages.profile.subtitleSignedOut}
          </p>
        </div>
        <div className="rounded-lg border border-border/60 bg-surface-elevated p-4">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border border-border/60 bg-surface text-primary">
              {auth.user ? <Cloud className="size-5" /> : <History className="size-5" />}
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">{copy.identity}</p>
              <p className="text-xs text-muted-foreground">{auth.user ? profileName : copy.authRequired}</p>
            </div>
          </div>
        </div>
      </header>

      {auth.loading ? (
        <div className="flex min-h-[28vh] items-center justify-center gap-3 rounded-lg border border-border/60 bg-surface p-8 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {messages.profile.authLoading}
        </div>
      ) : (
        <section className="grid gap-6 lg:grid-cols-[18rem_1fr]">
          <AccountSummaryPanel
            avatarUrl={profileAvatar}
            copy={copy}
            displayName={profileName}
            email={auth.user?.email}
            followupCount={followupCount}
            isSignedIn={Boolean(auth.user)}
            messages={messages}
            sessionCount={sessions.length}
            toLocalePath={toLocalePath}
          />
          {auth.user ? (
            <CloudHistoryPanel
              continuingId={continuingId}
              copy={copy}
              deletingId={deletingId}
              exportingId={exportingId}
              isFetching={historyQuery.isFetching}
              isLoading={historyQuery.isLoading}
              messages={messages}
              onContinue={handleContinue}
              onDelete={handleDelete}
              onDownload={handleDownload}
              onRefresh={() => historyQuery.refetch()}
              onSignOut={handleSignOut}
              sessions={sessions}
              toLocalePath={toLocalePath}
            />
          ) : (
            <AuthPanel
              authMode={authMode}
              busy={busy}
              copy={copy}
              email={email}
              messages={messages}
              onEmailSubmit={handleAuthSubmit}
              onGoogleSignIn={handleGoogleSignIn}
              password={password}
              setAuthMode={setAuthMode}
              setEmail={setEmail}
              setPassword={setPassword}
            />
          )}
        </section>
      )}
    </div>
  )
}
