"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2, RefreshCw } from "lucide-react"
import { toast } from "sonner"
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
  if (!value) return "时间未知"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

export default function ProfilePage() {
  const auth = useAuthContext()
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
  const profileName = auth.displayName ?? auth.user?.email ?? "游客"
  const profileAvatar = auth.avatarUrl ?? null

  async function handleDownload(summary: SessionSummary) {
    if (!auth.accessToken) {
      toast.error("请登录后再导出。")
      return
    }
    setExportingId(summary.session_id)
    try {
      const transcript = await fetchChatTranscript(summary.session_id, auth.accessToken)
      const snapshot = transcript.payload_snapshot
      const lines: string[] = []
      lines.push(`时间: ${formatTimestamp(snapshot?.session_dict?.["current_time_str"] as string)}`)
      lines.push("")
      if (snapshot?.summary_text) {
        lines.push("【概要】")
        lines.push(snapshot.summary_text.trim())
        lines.push("")
      } else if (transcript.summary_text) {
        lines.push("【概要】")
        lines.push(transcript.summary_text.trim())
        lines.push("")
      }
      if (snapshot?.hex_text) {
        lines.push("【卦辞】")
        lines.push(snapshot.hex_text.trim())
        lines.push("")
      }
      if (snapshot?.ai_text || transcript.initial_ai_text) {
        lines.push("【AI 解读】")
        lines.push((snapshot?.ai_text || transcript.initial_ai_text || "").trim())
        lines.push("")
      }
      if (transcript.messages.length) {
        lines.push("【追问对话】")
        transcript.messages.forEach((message, index) => {
          const created = message.created_at ? ` @ ${formatTimestamp(message.created_at)}` : ""
          lines.push(`${index + 1}. ${message.role === "assistant" ? "AI" : "用户"}${created}`)
          lines.push(message.content.trim())
          lines.push("")
        })
      }
      const blob = new Blob([lines.join("\n")], {
        type: "text/plain;charset=utf-8",
      })
      triggerDownload(blob, `session-${summary.session_id}.txt`)
    } catch (error) {
      toast.error((error as Error).message || "导出失败，请稍后重试。")
    } finally {
      setExportingId(null)
    }
  }

  async function handleContinue(session: SessionSummary) {
    if (!auth.accessToken) {
      toast.error("请登录后再操作。")
      return
    }
    setContinuingId(session.session_id)
    try {
      const transcript = await fetchChatTranscript(session.session_id, auth.accessToken)
      if (!transcript.payload_snapshot) {
        throw new Error("无法加载完整会话，请重新起卦。")
      }
      setResult(transcript.payload_snapshot as SessionPayload)
      router.push("/app")
    } catch (error) {
      toast.error((error as Error).message || "无法加载会话，请稍后重试。")
    } finally {
      setContinuingId(null)
    }
  }

  async function handleDelete(session: SessionSummary) {
    if (!auth.accessToken) {
      toast.error("请登录后再操作。")
      return
    }
    if (!confirm("确定要删除该会话及其聊天记录吗？此操作无法撤销。")) {
      return
    }
    setDeletingId(session.session_id)
    try {
      await deleteSession(session.session_id, auth.accessToken)
      toast.success("会话已删除。")
      historyQuery.refetch()
    } catch (error) {
      toast.error((error as Error).message || "删除失败，请稍后再试。")
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
      toast.error("请输入邮箱与密码。")
      return
    }
    setBusy(true)
    try {
      if (authMode === "signIn") {
        await auth.signIn(email, password)
        toast.success("登录成功。")
      } else {
        await auth.signUp(email, password)
        toast.success("注册成功，请查收验证邮件。")
      }
      setEmail("")
      setPassword("")
    } catch (error) {
      toast.error((error as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const hasSessions = useMemo(() => (historyQuery.data?.sessions.length ?? 0) > 0, [historyQuery.data?.sessions])

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-6 py-16 lg:px-12">
      <header className="flex flex-col gap-4 text-foreground">
        <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">个人中心</p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            {profileAvatar ? (
              <>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={profileAvatar} alt={profileName} className="size-16 rounded-full object-cover" />
              </>
            ) : auth.user ? (
              <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-xl font-semibold text-primary">
                {profileName?.[0] ?? "访"}
              </div>
            ) : null}
            <div>
              <h1 className="text-2xl font-semibold leading-tight">管理账户与历史记录</h1>
              <p className="text-sm text-muted-foreground">
                {auth.user ? `${profileName} · ${auth.user.email}` : "登录后，所有占卜都会同步到云端，支持跨设备查看、导出与 AI 追问。"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="outline">
              <Link href="/app">返回工作台</Link>
            </Button>
            <Button asChild variant="ghost">
              <Link href="/">返回主页</Link>
            </Button>
          </div>
        </div>
      </header>

      {auth.loading ? (
        <div className="flex min-h-[40vh] items-center justify-center gap-3 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          正在加载登录状态…
        </div>
      ) : auth.user ? (
        <section className="space-y-6">
          <Card className="glass-panel border-transparent text-foreground">
            <CardHeader className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle className="text-xl">云端历史记录</CardTitle>
                <CardDescription>显示所有云端会话，最新记录在前，可随时导出备份。</CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={historyQuery.isFetching}
                  onClick={() => historyQuery.refetch()}
                >
                  <RefreshCw className="mr-2 size-4" />
                  刷新
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={async () => {
                    try {
                      await auth.signOut()
                      toast.success("已退出登录。")
                    } catch (error) {
                      toast.error((error as Error).message)
                    }
                  }}
                >
                  退出登录
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!historyQuery.isSuccess && historyQuery.isLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  正在加载历史记录…
                </div>
              ) : !hasSessions ? (
                <p className="text-sm text-muted-foreground">
                  暂无云端记录。前往工作台运行一次占卜即可自动写入。
                </p>
              ) : (
                <div className="space-y-4">
                  {historyQuery.data?.sessions.map((session) => (
                    <div
                      key={session.session_id}
                      className="rounded-2xl border border-border/70 bg-background/70 p-4 text-sm shadow-glass dark:border-white/20 dark:bg-white/5"
                    >
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <div>
                          <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">会话</p>
                          <p className="font-semibold text-foreground">
                            {session.topic_label ?? "未填写"} · {session.method_label ?? "未知方法"} ·{" "}
                            {formatTimestamp(session.created_at)}
                          </p>
                          {(session.user_display_name || session.user_email) && (
                            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                              {session.user_avatar_url ? (
                                <>
                                  {/* eslint-disable-next-line @next/next/no-img-element */}
                                  <img
                                    src={session.user_avatar_url}
                                    alt={session.user_display_name ?? session.user_email ?? "用户头像"}
                                    className="size-8 rounded-full object-cover"
                                  />
                                </>
                              ) : null}
                              <span>
                                用户：{session.user_display_name ?? "未知"} · {session.user_email ?? "无邮箱"}
                              </span>
                            </div>
                          )}
                        </div>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          disabled={exportingId === session.session_id}
                            onClick={() => handleDownload(session)}
                          >
                            {exportingId === session.session_id ? (
                              <>
                                <Loader2 className="mr-2 size-4 animate-spin" />
                                正在导出…
                              </>
                            ) : (
                              "下载记录"
                          )}
                        </Button>
                        {session.ai_enabled ? (
                          <Button
                            type="button"
                            variant="ghost"
                            disabled={continuingId === session.session_id}
                            onClick={() => handleContinue(session)}
                          >
                            {continuingId === session.session_id ? "载入中..." : "继续追问"}
                          </Button>
                        ) : (
                          <Button type="button" variant="ghost" disabled>
                            无法追问
                          </Button>
                        )}
                        <Button
                          type="button"
                          variant="destructive"
                          disabled={deletingId === session.session_id}
                          onClick={() => handleDelete(session)}
                        >
                          {deletingId === session.session_id ? "删除中..." : "删除"}
                        </Button>
                      </div>
                      </div>
                      <Textarea
                        value={session.summary_text ?? "（暂无概要）"}
                        readOnly
                        rows={4}
                        className="mt-3 min-h-[6rem] resize-none text-sm"
                      />
                      {!session.ai_enabled && (
                        <p className="mt-2 text-xs text-muted-foreground">
                          未启用 AI，仅保留占卜概要。如需追问，请在下一次起卦时开启 AI 分析。
                        </p>
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
          <Card className="glass-panel border-transparent text-foreground">
            <CardHeader>
              <CardTitle className="text-xl">{authMode === "signIn" ? "登录账户" : "注册新账户"}</CardTitle>
              <CardDescription>
                登录后解锁 AI 分析、云端历史与跨设备同步。如果尚未拥有账号，可快速注册。
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAuthSubmit} className="space-y-4">
                <Input
                  type="email"
                  placeholder="邮箱"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                <Input
                  type="password"
                  placeholder="密码"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <Button type="submit" className="w-full" disabled={busy}>
                  {busy ? "提交中..." : authMode === "signIn" ? "登录" : "注册"}
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
                      toast.error((error as Error).message || "Google 登录失败。")
                    } finally {
                      setBusy(false)
                    }
                  }}
                >
                  使用 Google 登录
                </Button>
              </form>
              <div className="mt-4 text-center text-sm text-muted-foreground">
                <button
                  type="button"
                  className="font-semibold underline underline-offset-4"
                  onClick={() => setAuthMode((mode) => (mode === "signIn" ? "signUp" : "signIn"))}
                >
                  {authMode === "signIn" ? "没有账号？点击注册" : "已有账号？点击登录"}
                </button>
              </div>
            </CardContent>
          </Card>
        </section>
      )}
    </main>
  )
}
