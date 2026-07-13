"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { Copy, Loader2, RotateCcw, Settings2, Square } from "lucide-react"
import { toast } from "sonner"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { MarkdownContent } from "@/components/ui/markdown-content"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { fetchChatTranscript, streamChatMessage } from "@/lib/api"
import { useConfigQuery } from "@/lib/queries"
import { useWorkspaceStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import type { ChatMessage, SessionPayload } from "@/types/api"

type Props = { session: SessionPayload; embedded?: boolean }
type LocalChatMessage = ChatMessage & { status?: "streaming" | "error" | "stopped" }

const CHAT_MESSAGE_LIMIT = 10000
const EMPTY_MODELS: NonNullable<ReturnType<typeof useConfigQuery>["data"]>["ai_models"] = []
const EMPTY_ALIASES: Record<string, string> = {}

const makeLocalId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

export function ChatPanel({ session, embedded = false }: Props) {
  const auth = useAuthContext()
  const { messages, locale } = useI18n()
  const configQuery = useConfigQuery()
  const [messagesState, setMessagesState] = useState<LocalChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [authMode, setAuthMode] = useState<"signIn" | "signUp">("signIn")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [authBusy, setAuthBusy] = useState(false)
  const [transcriptLoading, setTranscriptLoading] = useState(false)
  const [chatModel, setChatModel] = useState(session.ai_model ?? "")
  const [reasoning, setReasoning] = useState("medium")
  const [verbosity, setVerbosity] = useState("medium")
  const [tone, setTone] = useState(session.ai_tone ?? "normal")
  const pendingChatPrompt = useWorkspaceStore((state) => state.pendingChatPrompt)
  const setPendingChatPrompt = useWorkspaceStore((state) => state.setPendingChatPrompt)
  const listRef = useRef<HTMLDivElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const stickToBottomRef = useRef(true)
  const storageKey = useMemo(() => `iching-chat-v2-${session.session_id}`, [session.session_id])
  const modelOptions = configQuery.data?.ai_models ?? EMPTY_MODELS
  const modelAliases = configQuery.data?.model_aliases ?? EMPTY_ALIASES
  const requestedModel = modelAliases[chatModel] ?? chatModel
  const selectedChatModel = modelOptions.some((model) => model.name === requestedModel)
    ? requestedModel
    : configQuery.data?.default_model ?? modelOptions[0]?.name ?? ""
  const activeModel = modelOptions.find((model) => model.name === selectedChatModel)
  const toneOptions = messages.workspace.tones

  const reasoningLabels: Record<string, string> = {
    none: messages.workspace.chat.reasoningNone,
    minimal: messages.workspace.chat.reasoningMinimal,
    low: messages.workspace.chat.reasoningLow,
    medium: messages.workspace.chat.reasoningMedium,
    high: messages.workspace.chat.reasoningHigh,
    xhigh: locale === "zh" ? "极高" : "X-high",
    max: locale === "zh" ? "最大" : "Max",
  }
  const verbosityLabels: Record<string, string> = {
    low: messages.workspace.chat.verbosityLow,
    medium: messages.workspace.chat.verbosityMedium,
    high: messages.workspace.chat.verbosityHigh,
  }

  const totalTokens = useMemo(
    () => messagesState.reduce((sum, message) => sum + Number(message.tokens_in || 0) + Number(message.tokens_out || 0), 0),
    [messagesState],
  )

  useEffect(() => {
    setChatModel(session.ai_model ?? "")
    setReasoning(session.ai_reasoning ?? "medium")
    setVerbosity(session.ai_verbosity ?? "medium")
    setTone(session.ai_tone ?? "normal")
    setMessagesState([])
  }, [session.session_id, session.ai_model, session.ai_reasoning, session.ai_verbosity, session.ai_tone])

  useEffect(() => {
    if (typeof window === "undefined") return
    const snapshot = window.localStorage.getItem(storageKey)
    if (!snapshot) return
    try {
      const parsed = JSON.parse(snapshot) as LocalChatMessage[]
      if (parsed.length) setMessagesState(parsed.filter((item) => item.status !== "streaming"))
    } catch {
      // Ignore stale local chat cache.
    }
  }, [storageKey])

  useEffect(() => {
    if (typeof window === "undefined" || !messagesState.length) return
    window.localStorage.setItem(storageKey, JSON.stringify(messagesState))
  }, [messagesState, storageKey])

  useEffect(() => {
    if (!auth.accessToken) {
      setMessagesState((current) => current.length || !session.ai_text
        ? current
        : [{ localId: `initial-${session.session_id}`, role: "assistant", content: session.ai_text, created_at: new Date().toISOString(), model: session.ai_model }])
      return
    }
    let cancelled = false
    setTranscriptLoading(true)
    fetchChatTranscript(session.session_id, auth.accessToken)
      .then((data) => {
        if (cancelled) return
        if (data.messages.length) {
          setMessagesState(data.messages)
        } else if (session.ai_text) {
          setMessagesState([{ localId: `initial-${session.session_id}`, role: "assistant", content: session.ai_text, created_at: new Date().toISOString(), model: session.ai_model }])
        }
        if (data.followup_model) setChatModel(data.followup_model)
        if (data.ai_reasoning !== undefined && data.ai_reasoning !== null) setReasoning(data.ai_reasoning)
        if (data.ai_verbosity !== undefined && data.ai_verbosity !== null) setVerbosity(data.ai_verbosity)
        if (data.ai_tone) setTone(data.ai_tone)
      })
      .catch((error) => {
        if (!cancelled) toast.error((error as Error).message || messages.workspace.chat.loadHistoryFailed)
      })
      .finally(() => {
        if (!cancelled) setTranscriptLoading(false)
      })
    return () => { cancelled = true }
  }, [auth.accessToken, session.session_id, session.ai_text, session.ai_model, messages.workspace.chat.loadHistoryFailed])

  useEffect(() => {
    if (!activeModel) return
    if (!activeModel.reasoning.length) {
      setReasoning("")
    } else if (!activeModel.reasoning.includes(reasoning)) {
      setReasoning(activeModel.default_reasoning || activeModel.reasoning[0])
    }
    if (!activeModel.verbosity) setVerbosity("")
    else if (!verbosity) setVerbosity(activeModel.default_verbosity || "medium")
  }, [activeModel, reasoning, verbosity])

  useEffect(() => {
    if (!pendingChatPrompt) return
    setInput(pendingChatPrompt)
    setPendingChatPrompt(undefined)
  }, [pendingChatPrompt, setPendingChatPrompt])

  useEffect(() => {
    if (!listRef.current || !stickToBottomRef.current) return
    listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messagesState])

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email || !password) return toast.error(messages.workspace.chat.askAfterLoginError)
    setAuthBusy(true)
    try {
      if (authMode === "signIn") await auth.signIn(email, password)
      else await auth.signUp(email, password)
      setEmail("")
      setPassword("")
    } catch (error) {
      toast.error((error as Error).message || messages.common.unknownError)
    } finally {
      setAuthBusy(false)
    }
  }

  async function sendPrompt(prompt: string, options: { appendUser?: boolean; restart?: boolean } = {}) {
    if (!auth.accessToken || isSending) return
    const trimmed = prompt.trim()
    if (!trimmed) return
    const appendUser = options.appendUser ?? true
    const userLocalId = makeLocalId()
    const assistantLocalId = makeLocalId()
    const now = new Date().toISOString()
    const nextItems: LocalChatMessage[] = []
    if (appendUser) nextItems.push({ localId: userLocalId, role: "user", content: trimmed, created_at: now, model: selectedChatModel })
    nextItems.push({ localId: assistantLocalId, role: "assistant", content: "", created_at: now, model: selectedChatModel, reasoning, verbosity, tone, status: "streaming" })
    setMessagesState((previous) => [...previous, ...nextItems])
    setInput("")
    setIsSending(true)
    stickToBottomRef.current = true
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const result = await streamChatMessage(
        session.session_id,
        auth.accessToken,
        { message: trimmed, reasoning: activeModel?.reasoning.length ? reasoning : null, verbosity: activeModel?.verbosity ? verbosity : null, tone, model: selectedChatModel || null, restart: options.restart },
        {
          signal: controller.signal,
          onDelta: (delta) => setMessagesState((previous) => previous.map((item) => item.localId === assistantLocalId ? { ...item, content: `${item.content}${delta}` } : item)),
        },
      )
      setMessagesState((previous) => previous.map((item) => item.localId === assistantLocalId ? { ...result.assistant, localId: assistantLocalId } : item))
    } catch (error) {
      const stopped = (error as Error).name === "AbortError"
      setMessagesState((previous) => previous.map((item) => item.localId === assistantLocalId ? { ...item, content: item.content || (stopped ? (locale === "zh" ? "已停止生成。" : "Generation stopped.") : (error as Error).message), status: stopped ? "stopped" : "error" } : item))
      if (!stopped) toast.error((error as Error).message || messages.workspace.chat.chatFailed)
    } finally {
      abortRef.current = null
      setIsSending(false)
    }
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!auth.accessToken) return toast.error(messages.workspace.chat.askAfterLogin)
    void sendPrompt(input)
  }

  if (auth.loading) return <div className="surface-soft mt-4 rounded-lg p-4 text-sm text-muted-foreground">{messages.workspace.chat.authChecking}</div>

  if (!auth.accessToken) {
    return (
      <div className="surface-soft mt-4 space-y-4 rounded-lg p-4 text-sm">
        <div><p className="kicker">{messages.workspace.chat.loginToContinue}</p><p className="mt-1 text-xs text-muted-foreground">{messages.workspace.chat.loginDescription}</p></div>
        <form onSubmit={handleAuth} className="space-y-3">
          <Input type="email" placeholder={messages.common.email} value={email} onChange={(event) => setEmail(event.target.value)} />
          <Input type="password" placeholder={messages.common.password} value={password} onChange={(event) => setPassword(event.target.value)} />
          <Button type="submit" className="w-full" disabled={authBusy}>{authMode === "signIn" ? messages.common.signIn : messages.common.signUp}</Button>
        </form>
        <Button variant="outline" className="w-full" disabled={authBusy} onClick={() => auth.signInWithProvider("google")}>{messages.common.continueWithGoogle}</Button>
        <button type="button" className="text-xs text-muted-foreground underline underline-offset-2" onClick={() => setAuthMode((mode) => mode === "signIn" ? "signUp" : "signIn")}>{authMode === "signIn" ? `${messages.workspace.chat.signInPrompt} ${messages.workspace.chat.switchToSignUp}` : `${messages.workspace.chat.signUpPrompt} ${messages.workspace.chat.switchToSignIn}`}</button>
      </div>
    )
  }

  return (
    <div className={cn("surface-card flex flex-col overflow-hidden rounded-lg p-0", embedded ? "min-h-[34rem]" : "mt-4 min-h-[42rem]")}>
      <div className="border-b border-border/50 px-4 py-3 sm:px-5">
        <div className="flex items-center justify-between gap-3">
          <div><p className="kicker">{messages.workspace.chat.title}</p><p className="mt-1 text-xs text-muted-foreground">{activeModel?.label ?? selectedChatModel ?? "—"} · {reasoningLabels[reasoning] || reasoning || "—"} · {verbosityLabels[verbosity] || verbosity || "—"}</p></div>
          {isSending ? <Button type="button" variant="outline" size="sm" onClick={() => abortRef.current?.abort()}><Square className="mr-2 size-3" />{locale === "zh" ? "停止" : "Stop"}</Button> : null}
        </div>
        <details className="mt-3 rounded-md border border-border/50 bg-surface px-3 py-2">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-semibold text-foreground"><Settings2 className="size-3.5" />{locale === "zh" ? "模型与输出设置" : "Model and output settings"}</summary>
          <div className="mt-3 grid gap-2 md:grid-cols-4">
            <Select value={selectedChatModel} onValueChange={setChatModel} disabled={!modelOptions.length}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{modelOptions.map((model) => <SelectItem key={model.name} value={model.name}>{model.label}</SelectItem>)}</SelectContent></Select>
            {activeModel?.reasoning.length ? <Select value={reasoning} onValueChange={setReasoning}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{activeModel.reasoning.map((level) => <SelectItem key={level} value={level}>{reasoningLabels[level] || level}</SelectItem>)}</SelectContent></Select> : <div className="rounded-md border px-3 py-2 text-xs text-muted-foreground">{messages.workspace.cast.reasoningNoControl}</div>}
            {activeModel?.verbosity ? <Select value={verbosity} onValueChange={setVerbosity}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{["low", "medium", "high"].map((level) => <SelectItem key={level} value={level}>{verbosityLabels[level]}</SelectItem>)}</SelectContent></Select> : <div className="rounded-md border px-3 py-2 text-xs text-muted-foreground">—</div>}
            <Select value={tone} onValueChange={setTone}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{toneOptions.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}</SelectContent></Select>
          </div>
        </details>
      </div>

      <div ref={listRef} onScroll={(event) => { const element = event.currentTarget; stickToBottomRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 96 }} className="custom-scrollbar flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto bg-background/35 px-4 py-5 sm:px-6">
        {transcriptLoading && !messagesState.length ? <div className="flex items-center justify-center gap-2 py-10 text-xs text-muted-foreground"><Loader2 className="size-3 animate-spin" />{messages.workspace.chat.transcriptLoading}</div> : null}
        {!transcriptLoading && !messagesState.length ? <p className="text-center text-xs text-muted-foreground">{messages.workspace.chat.transcriptEmpty}</p> : null}
        {messagesState.map((message, index) => {
          const previousUser = [...messagesState.slice(0, index)].reverse().find((item) => item.role === "user")
          const isLastAssistant = message.role === "assistant" && !messagesState.slice(index + 1).some((item) => item.role === "assistant")
          return <ChatBubble key={message.id ?? message.localId} message={message} locale={locale} onEdit={message.role === "user" ? () => setInput(message.content) : undefined} onRetry={isLastAssistant && previousUser ? () => {
            setMessagesState((previous) => previous.filter((item) => message.id ? item.id !== message.id : item.localId !== message.localId))
            void sendPrompt(previousUser.content, { appendUser: false, restart: true })
          } : undefined} />
        })}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-border/40 px-4 py-4 sm:px-5">
        <div className="surface-soft rounded-lg border border-border/50 p-2">
          <Textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit() } }} placeholder={messages.workspace.chat.inputPlaceholder} rows={2} maxLength={CHAT_MESSAGE_LIMIT} className="min-h-20 border-0 bg-transparent shadow-none focus-visible:ring-0" />
          <div className="flex items-center justify-between gap-3 px-1 pt-2"><p className="text-xs text-muted-foreground">{totalTokens.toLocaleString()} tokens · {input.length}/{CHAT_MESSAGE_LIMIT}</p><Button type="submit" className="rounded-md px-5" disabled={isSending || !input.trim()}>{isSending ? messages.workspace.chat.sending : messages.workspace.chat.send}</Button></div>
        </div>
      </form>
    </div>
  )
}

function ChatBubble({ message, locale, onEdit, onRetry }: { message: LocalChatMessage; locale: "en" | "zh"; onEdit?: () => void; onRetry?: () => void }) {
  const isAssistant = message.role === "assistant"
  return (
    <div className={cn("group flex", isAssistant ? "justify-start" : "justify-end")}>
      <div className={cn("text-sm leading-relaxed", isAssistant ? "w-full max-w-3xl border-l border-primary/35 pl-4 text-foreground" : "max-w-[82%] rounded-lg border border-primary/40 bg-primary px-3 py-2 text-primary-foreground shadow-sm")}>
        {message.content ? <MarkdownContent content={message.content} className={isAssistant ? "text-foreground" : "text-primary-foreground"} /> : <div className="flex items-center gap-2 py-1 text-muted-foreground"><Loader2 className="size-3 animate-spin" />{locale === "zh" ? "正在思考…" : "Thinking…"}</div>}
        {message.status === "error" ? <p className="mt-2 text-xs text-destructive">{locale === "zh" ? "生成失败，可重试。" : "Generation failed. Retry available."}</p> : null}
        {message.status === "stopped" ? <p className="mt-2 text-xs text-muted-foreground">{locale === "zh" ? "生成已停止。" : "Generation stopped."}</p> : null}
        <div className={cn("mt-2 flex gap-1 opacity-0 transition group-hover:opacity-100", isAssistant ? "justify-start" : "justify-end")}>
          {isAssistant && message.content ? <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => navigator.clipboard.writeText(message.content)}><Copy className="mr-1 size-3" />{locale === "zh" ? "复制" : "Copy"}</Button> : null}
          {onEdit ? <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs text-primary-foreground hover:text-foreground" onClick={onEdit}>{locale === "zh" ? "编辑重发" : "Edit"}</Button> : null}
          {onRetry && message.status !== "streaming" ? <Button type="button" variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onRetry}><RotateCcw className="mr-1 size-3" />{locale === "zh" ? "重新生成" : "Regenerate"}</Button> : null}
        </div>
      </div>
    </div>
  )
}
