"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { useAuthContext } from "@/components/providers/auth-provider"
import { MarkdownContent } from "@/components/ui/markdown-content"
import { fetchChatTranscript, sendChatMessage } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { ChatMessage, SessionPayload } from "@/types/api"
import { toast } from "sonner"

type Props = {
  session: SessionPayload
}

const modelOptions = [
  {
    id: "gpt-5-mini",
    label: "默认 · GPT-5 mini",
    description: "中等推理+篇幅，速度/成本平衡。",
  },
  {
    id: "gpt-5.1",
    label: "GPT-5.1 深度",
    description: "链式推理更强，适合高准确度场景。",
  },
]

const premiumReasoningOptions = [
  { value: "none", label: "关闭链式推理（最快）" },
  { value: "minimal", label: "Minimal" },
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
]

const verbosityOptions = [
  { value: "low", label: "简洁" },
  { value: "medium", label: "适中" },
  { value: "high", label: "详尽" },
]

const toneOptions = [
  { value: "normal", label: "标准" },
  { value: "wenyan", label: "文言" },
  { value: "modern", label: "现代" },
  { value: "academic", label: "学术" },
]

const MODELS_WITH_CONTROLS = new Set(["gpt-5-mini", "gpt-5.1"])
const CHAT_MESSAGE_LIMIT = 3000

const makeLocalId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

export function ChatPanel({ session }: Props) {
  const auth = useAuthContext()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [authMode, setAuthMode] = useState<"signIn" | "signUp">("signIn")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [authBusy, setAuthBusy] = useState(false)
  const [transcriptLoading, setTranscriptLoading] = useState(false)
  const [chatModel, setChatModel] = useState<string>("gpt-5-mini")
  const [reasoning, setReasoning] = useState<string>("medium")
  const [verbosity, setVerbosity] = useState<string>("medium")
  const [tone, setTone] = useState<string>(session.ai_tone ?? "normal")
  const [showInitial, setShowInitial] = useState(false)
  const [modelHydrated, setModelHydrated] = useState(false)
  const listRef = useRef<HTMLDivElement | null>(null)
  const storageKey = useMemo(() => `iching-chat-${session.session_id}`, [session.session_id])
  const profileName = auth.displayName ?? auth.user?.email ?? "游客"
  const totalTokens = useMemo(
    () =>
      messages.reduce((sum, message) => {
        const input = Number(message.tokens_in || 0)
        const output = Number(message.tokens_out || 0)
        return sum + input + output
      }, 0),
    [messages],
  )

  useEffect(() => {
    if (typeof window === "undefined") return
    const snapshot = window.localStorage.getItem(storageKey)
    if (snapshot) {
      try {
        const parsed = JSON.parse(snapshot) as ChatMessage[]
        if (parsed.length) {
          setMessages(parsed)
          return
        }
      } catch {
        // ignore corrupted cache
      }
    }
    if (session.ai_text) {
      setMessages([
        {
          localId: `initial-${session.session_id}`,
          role: "assistant",
          content: session.ai_text,
          created_at: new Date().toISOString(),
        },
      ])
    }
  }, [storageKey, session.ai_text, session.session_id])

  useEffect(() => {
    if (typeof window === "undefined") return
    window.localStorage.setItem(storageKey, JSON.stringify(messages))
  }, [messages, storageKey])

  useEffect(() => {
    return () => {
      if (typeof window === "undefined") return
      window.localStorage.removeItem(storageKey)
    }
  }, [storageKey])

  const reasoningOptions = useMemo(
    () =>
      chatModel === "gpt-5.1"
        ? premiumReasoningOptions
        : premiumReasoningOptions.filter((option) => option.value !== "none"),
    [chatModel],
  )

  const refreshTranscript = useCallback(async () => {
    if (!auth.accessToken) return
    setTranscriptLoading(true)
    try {
      const data = await fetchChatTranscript(session.session_id, auth.accessToken)
      if (Array.isArray(data.messages) && data.messages.length) {
        setMessages(data.messages)
      }
      if (!modelHydrated && data.followup_model) {
        setChatModel(data.followup_model)
        setModelHydrated(true)
      }
    } catch (error) {
      toast.error((error as Error).message || "无法加载历史记录。")
    } finally {
      setTranscriptLoading(false)
    }
  }, [auth.accessToken, session.session_id, modelHydrated])

  useEffect(() => {
    refreshTranscript()
  }, [refreshTranscript])

  useEffect(() => {
    setModelHydrated(false)
    setChatModel("gpt-5-mini")
    setReasoning("medium")
    setVerbosity("medium")
    setTone(session.ai_tone ?? "normal")
  }, [session.session_id, session.ai_tone])

  useEffect(() => {
    if (chatModel !== "gpt-5.1" && reasoning === "none") {
      setReasoning("medium")
    }
  }, [chatModel, reasoning])

  useEffect(() => {
    if (!listRef.current) return
    listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messages])

  if (auth.loading) {
    return (
      <div className="mt-4 rounded-2xl border border-border/40 bg-foreground/[0.04] p-4 text-sm text-muted-foreground dark:border-white/10 dark:bg-white/5">
        正在检查登录状态…
      </div>
    )
  }

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email || !password) {
      toast.error("请输入邮箱与密码。")
      return
    }
    setAuthBusy(true)
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
      setAuthBusy(false)
    }
  }

  async function handleSend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!auth.accessToken) {
      toast.error("请登录后再提问。")
      return
    }
    const trimmed = input.trim()
    if (!trimmed) {
      return
    }
    const optimistic: ChatMessage = {
      localId: makeLocalId(),
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, optimistic])
    setIsSending(true)
    try {
      const result = await sendChatMessage(session.session_id, auth.accessToken, {
        message: trimmed,
        reasoning: MODELS_WITH_CONTROLS.has(chatModel) ? reasoning : null,
        verbosity: MODELS_WITH_CONTROLS.has(chatModel) ? verbosity : null,
        tone,
        model: chatModel,
      })
      setMessages((prev) => [...prev, result.assistant])
      setInput("")
      await refreshTranscript()
    } catch (error) {
      toast.error((error as Error).message || "追问失败，请稍后重试。")
      setMessages((prev) => prev.filter((item) => item.localId !== optimistic.localId))
    } finally {
      setIsSending(false)
    }
  }

  const loginPanel = (
    <div className="space-y-4 rounded-2xl border border-border/40 bg-foreground/[0.04] p-4 text-sm leading-relaxed text-foreground dark:border-white/10 dark:bg-white/5">
      <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">登录后继续追问</p>
      <form onSubmit={handleAuth} className="space-y-3">
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
        <Button type="submit" className="w-full" disabled={authBusy || auth.loading}>
          {authMode === "signIn" ? "登录" : "注册"}
        </Button>
      </form>
      <div className="flex items-center gap-3">
        <div className="h-px w-full bg-border/50 dark:bg-white/20" />
        <span className="text-[11px] uppercase tracking-[0.3rem] text-muted-foreground">或</span>
        <div className="h-px w-full bg-border/50 dark:bg-white/20" />
      </div>
      <Button
        variant="outline"
        type="button"
        className="w-full"
        disabled={authBusy || auth.loading}
        onClick={async () => {
          setAuthBusy(true)
          try {
            await auth.signInWithProvider("google")
          } catch (error) {
            toast.error((error as Error).message || "Google 登录失败。")
          } finally {
            setAuthBusy(false)
          }
        }}
      >
        使用 Google 登录
      </Button>
      <div className="text-xs text-muted-foreground">
        <button
          type="button"
          className="underline underline-offset-2"
          onClick={() => setAuthMode((mode) => (mode === "signIn" ? "signUp" : "signIn"))}
        >
          {authMode === "signIn" ? "没有账号？点击注册" : "已有账号？点击登录"}
        </button>
      </div>
      {auth.error && <p className="text-xs text-destructive">{auth.error}</p>}
    </div>
  )

  const initialBlock = session.ai_text ? (
    <div className="rounded-2xl border border-border/20 bg-foreground/[0.02] p-4 text-sm leading-relaxed text-foreground shadow-glass dark:border-white/10 dark:bg-white/5">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">AI 首次解读</p>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs font-semibold tracking-wide text-foreground hover:text-foreground"
          onClick={() => setShowInitial((value) => !value)}
          aria-expanded={showInitial}
        >
          {showInitial ? "收起" : "展开"}
        </Button>
      </div>
      {showInitial && <MarkdownContent content={session.ai_text} />}
    </div>
  ) : (
    <div className="rounded-2xl border border-dashed border-border/50 bg-foreground/[0.02] p-4 text-sm text-muted-foreground dark:border-white/15">
      该会话起卦时未启用 AI。发送首条追问后，系统会自动基于当前卦象补开 AI 上下文。
    </div>
  )

  const chatPanel = (
    <div className="rounded-2xl border border-border/40 bg-background/60 p-4 backdrop-blur-lg dark:border-white/10 dark:bg-white/5 space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {auth.avatarUrl ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={auth.avatarUrl} alt={profileName} className="size-12 rounded-full object-cover" />
            </>
          ) : (
            <div className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-lg font-semibold text-primary">
              {profileName?.[0] ?? "我"}
            </div>
          )}
          <div>
            <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">追问对话</p>
            <p className="text-sm font-semibold text-foreground">{profileName}</p>
            <p className="text-xs text-muted-foreground">{auth.user?.email}</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          type="button"
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
      <div
        ref={listRef}
        className="custom-scrollbar flex h-[32rem] flex-col space-y-3 overflow-y-auto rounded-xl border border-border/20 bg-foreground/[0.03] p-3 dark:border-white/5"
      >
        {transcriptLoading ? (
          <p className="text-center text-xs text-muted-foreground">加载历史对话中...</p>
        ) : messages.length ? (
          messages.map((message) => (
            <ChatBubble key={message.id ?? message.localId} message={message} />
          ))
        ) : (
          <p className="text-center text-xs text-muted-foreground">暂无对话，发送首条追问即可开始。</p>
        )}
      </div>
      <div className="text-right text-xs text-muted-foreground">
        累计 tokens：<span className="font-semibold">{totalTokens.toLocaleString()}</span>
      </div>
      <form
        onSubmit={handleSend}
        className="space-y-4 rounded-2xl border border-border/30 bg-background/80 p-4 dark:border-white/10 dark:bg-white/5"
      >
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">聊天模型</p>
          <div className="grid gap-3 md:grid-cols-2">
            {modelOptions.map((option) => (
              <button
                key={option.id}
                type="button"
                className={cn(
                  "rounded-2xl border px-4 py-3 text-left text-sm transition",
                  chatModel === option.id
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/60 hover:border-primary/50",
                )}
                onClick={() => setChatModel(option.id)}
              >
                <div className="font-semibold">{option.label}</div>
                <p className="text-xs text-muted-foreground">{option.description}</p>
              </button>
            ))}
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Select value={reasoning} onValueChange={(value) => setReasoning(value)}>
            <SelectTrigger>
              <SelectValue placeholder="推理力度" />
            </SelectTrigger>
            <SelectContent>
              {reasoningOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={verbosity} onValueChange={(value) => setVerbosity(value)}>
            <SelectTrigger>
              <SelectValue placeholder="输出篇幅" />
            </SelectTrigger>
            <SelectContent>
              {verbosityOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={tone} onValueChange={(value) => setTone(value)}>
            <SelectTrigger>
              <SelectValue placeholder="语气" />
            </SelectTrigger>
            <SelectContent>
              {toneOptions.map((option) => (
                <SelectItem value={option.value} key={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入追问内容..."
            rows={3}
            maxLength={CHAT_MESSAGE_LIMIT}
          />
          <p className="text-right text-xs text-muted-foreground">
            {input.length}/{CHAT_MESSAGE_LIMIT}
          </p>
        </div>
        <Button type="submit" className="w-full" disabled={isSending}>
          {isSending ? "发送中..." : "发送追问"}
        </Button>
      </form>
    </div>
  )

  return (
    <div className="mt-4 space-y-4">
      {initialBlock}
      {auth.accessToken ? chatPanel : loginPanel}
    </div>
  )
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isAssistant = message.role === "assistant"
  return (
    <div className={`flex ${isAssistant ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
          isAssistant
            ? "bg-white/80 text-foreground shadow-glass dark:bg-white/10"
            : "bg-primary text-primary-foreground shadow-glass"
        }`}
      >
        <MarkdownContent
          content={message.content}
          className={isAssistant ? "text-foreground" : "text-primary-foreground"}
        />
      </div>
    </div>
  )
}
