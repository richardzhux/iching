"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useSessionHistoryQuery } from "@/lib/queries"
import { deleteSession, fetchChatTranscript } from "@/lib/api"
import { useWorkspaceStore } from "@/lib/store"
import type { SessionPayload, SessionSummary } from "@/types/api"

function formatTimestamp(value?: string | null) {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

export default function ProfilePage() {
  const auth = useAuthContext()
  const { messages, toLocalePath } = useI18n()
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
  const profileName = auth.displayName ?? auth.user?.email ?? messages.profileMenu.guestMode
  const profileAvatar = auth.avatarUrl ?? null

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

  const hasSessions = useMemo(
    () => (historyQuery.data?.sessions.length ?? 0) > 0,
    [historyQuery.data?.sessions],
  )

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="surface-card rounded-3xl p-6 sm:p-7">
        <p className="kicker">{messages.profile.kicker}</p>
        <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            {profileAvatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={profileAvatar} alt={profileName} className="size-14 rounded-full object-cover ring-2 ring-border/70" />
            ) : (
              <div className="flex size-14 items-center justify-center rounded-full bg-primary/15 text-lg font-semibold text-primary">
                {profileName?.[0]?.toUpperCase() ?? "G"}
              </div>
            )}
            <div>
              <h1 className="text-xl font-semibold text-foreground sm:text-2xl">{messages.profile.title}</h1>
              <p className="text-sm text-muted-foreground">
                {auth.user
                  ? `${profileName} · ${auth.user.email}`
                  : messages.profile.subtitleSignedOut}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <Link href={toLocalePath("/app")}>{messages.nav.workspace}</Link>
            </Button>
            <Button asChild variant="ghost">
              <Link href={toLocalePath("/")}>{messages.common.back}</Link>
            </Button>
          </div>
        </div>
      </header>

      {auth.loading ? (
        <div className="surface-card flex min-h-[28vh] items-center justify-center gap-3 rounded-3xl p-8 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {messages.profile.authLoading}
        </div>
      ) : auth.user ? (
        <section>
          <Card className="surface-card border-border/40 text-foreground">
            <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="text-lg">{messages.profile.cloudHistoryTitle}</CardTitle>
                <CardDescription>{messages.profile.cloudHistoryDescription}</CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={historyQuery.isFetching}
                  onClick={() => historyQuery.refetch()}
                >
                  <RefreshCw className="mr-2 size-4" />
                  {messages.profile.refresh}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={async () => {
                    try {
                      await auth.signOut()
                      toast.success(messages.profileMenu.signedOutToast)
                    } catch (error) {
                      toast.error((error as Error).message || messages.common.unknownError)
                    }
                  }}
                >
                  {messages.common.signOut}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!historyQuery.isSuccess && historyQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  {messages.profile.loadingSessions}
                </div>
              ) : !hasSessions ? (
                <p className="text-sm text-muted-foreground">{messages.profile.noSessions}</p>
              ) : (
                <div className="space-y-3">
                  {historyQuery.data?.sessions.map((session) => (
                    <div key={session.session_id} className="surface-soft rounded-2xl p-4">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <p className="kicker">{messages.profile.sessionLabel}</p>
                          <p className="mt-1 text-sm font-medium text-foreground">
                            {session.topic_label ?? messages.workspace.history.noTopic} ·{" "}
                            {session.method_label ?? messages.workspace.history.noMethod} ·{" "}
                            {formatTimestamp(session.created_at)}
                          </p>
                          {(session.user_display_name || session.user_email) && (
                            <p className="mt-1 text-xs text-muted-foreground">
                              {messages.profile.userLabel}: {session.user_display_name ?? "-"} ·{" "}
                              {session.user_email ?? "-"}
                            </p>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            disabled={exportingId === session.session_id}
                            onClick={() => handleDownload(session)}
                          >
                            {exportingId === session.session_id ? messages.profile.downloading : messages.profile.download}
                          </Button>
                          {session.followup_available ? (
                            <Button
                              type="button"
                              variant="ghost"
                              disabled={continuingId === session.session_id}
                              onClick={() => handleContinue(session)}
                            >
                              {continuingId === session.session_id ? messages.profile.openingSession : messages.profile.openSession}
                            </Button>
                          ) : (
                            <Button type="button" variant="ghost" disabled>
                              {messages.profile.unavailableFollowup}
                            </Button>
                          )}
                          <Button
                            type="button"
                            variant="destructive"
                            disabled={deletingId === session.session_id}
                            onClick={() => handleDelete(session)}
                          >
                            {deletingId === session.session_id ? `${messages.common.delete}...` : messages.common.delete}
                          </Button>
                        </div>
                      </div>
                      <Textarea
                        value={session.summary_text ?? messages.profile.noSummary}
                        readOnly
                        rows={4}
                        className="mt-3 min-h-[6rem] resize-none text-sm"
                      />
                      {!session.ai_enabled && session.followup_available && (
                        <p className="mt-2 text-xs text-muted-foreground">{messages.profile.aiBootstrapHint}</p>
                      )}
                      {!session.followup_available && (
                        <p className="mt-2 text-xs text-muted-foreground">{messages.profile.noFollowupHint}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      ) : (
        <section>
          <Card className="surface-card border-border/40 text-foreground">
            <CardHeader>
              <CardTitle className="text-xl">
                {authMode === "signIn" ? messages.profile.authCardSignIn : messages.profile.authCardSignUp}
              </CardTitle>
              <CardDescription>{messages.profile.authCardDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAuthSubmit} className="space-y-3">
                <Input
                  type="email"
                  placeholder={messages.common.email}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <Input
                  type="password"
                  placeholder={messages.common.password}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <Button type="submit" className="w-full" disabled={busy}>
                  {busy
                    ? messages.profile.submitBusy
                    : authMode === "signIn"
                      ? messages.common.signIn
                      : messages.common.signUp}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true)
                    try {
                      await auth.signInWithProvider("google")
                    } catch (error) {
                      toast.error((error as Error).message || messages.common.unknownError)
                    } finally {
                      setBusy(false)
                    }
                  }}
                >
                  {messages.common.continueWithGoogle}
                </Button>
              </form>
              <div className="mt-4 text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  className="font-semibold underline underline-offset-4"
                  onClick={() => setAuthMode((mode) => (mode === "signIn" ? "signUp" : "signIn"))}
                >
                  {authMode === "signIn" ? messages.profile.switchToSignUp : messages.profile.switchToSignIn}
                </button>
              </div>
            </CardContent>
          </Card>
        </section>
      )}
    </main>
  )
}
