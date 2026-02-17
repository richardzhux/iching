"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Loader2 } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
import { useAuthContext } from "@/components/providers/auth-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { MarkdownContent } from "@/components/ui/markdown-content"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { fetchChatTranscript, sendChatMessage } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { ChatMessage, SessionPayload } from "@/types/api"
import { toast } from "sonner"

type Props = {
  session: SessionPayload
}

const FALLBACK_CHAT_MODEL = "gpt-5-mini"
const CHAT_MESSAGE_LIMIT = 3000

const makeLocalId = () =>
  typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const normalizeChatModel = (model?: string | null) => (model === "gpt-5.1" ? "gpt-5.2" : model || FALLBACK_CHAT_MODEL)

export function ChatPanel({ session }: Props) {
  const auth = useAuthContext()
  const { messages } = useI18n()
  const [messagesState, setMessagesState] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [authMode, setAuthMode] = useState<"signIn" | "signUp">("signIn")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [authBusy, setAuthBusy] = useState(false)
  const [transcriptLoading, setTranscriptLoading] = useState(false)
  const [chatModel, setChatModel] = useState<string>(FALLBACK_CHAT_MODEL)
  const [reasoning, setReasoning] = useState<string>("medium")
  const [verbosity, setVerbosity] = useState<string>("medium")
  const [tone, setTone] = useState<string>(session.ai_tone ?? "normal")
  const [showInitial, setShowInitial] = useState(false)
  const [modelHydrated, setModelHydrated] = useState(false)
  const listRef = useRef<HTMLDivElement | null>(null)
  const storageKey = useMemo(() => `iching-chat-${session.session_id}`, [session.session_id])
  const profileName = auth.displayName ?? auth.user?.email ?? messages.profileMenu.guestMode
  const modelOptions = useMemo(
    () => [
      {
        id: "gpt-5-mini",
        label: messages.workspace.chat.modelDefaultLabel,
        description: messages.workspace.chat.modelDefaultDesc,
      },
      {
        id: "gpt-5.2",
        label: messages.workspace.chat.modelDeepLabel,
        description: messages.workspace.chat.modelDeepDesc,
      },
      {
        id: "gpt-4.1",
        label: messages.workspace.chat.modelFastLabel,
        description: messages.workspace.chat.modelFastDesc,
      },
    ],
    [messages.workspace.chat],
  )
  const modelOptionIds = useMemo(() => new Set(modelOptions.map((option) => option.id)), [modelOptions])
  const modelsWithControls = useMemo(() => new Set(["gpt-5-mini", "gpt-5.2"]), [])

  const reasoningOptions = useMemo(() => {
    const options = [
      { value: "none", label: messages.workspace.chat.reasoningNone },
      { value: "minimal", label: messages.workspace.chat.reasoningMinimal },
      { value: "low", label: messages.workspace.chat.reasoningLow },
      { value: "medium", label: messages.workspace.chat.reasoningMedium },
      { value: "high", label: messages.workspace.chat.reasoningHigh },
    ]
    return chatModel === "gpt-5.2" ? options : options.filter((option) => option.value !== "none")
  }, [chatModel, messages.workspace.chat])

  const verbosityOptions = useMemo(
    () => [
      { value: "low", label: messages.workspace.chat.verbosityLow },
      { value: "medium", label: messages.workspace.chat.verbosityMedium },
      { value: "high", label: messages.workspace.chat.verbosityHigh },
    ],
    [messages.workspace.chat],
  )

  const toneOptions = messages.workspace.tones

  const totalTokens = useMemo(
    () =>
      messagesState.reduce((sum, message) => {
        const input = Number(message.tokens_in || 0)
        const output = Number(message.tokens_out || 0)
        return sum + input + output
      }, 0),
    [messagesState],
  )

  useEffect(() => {
    if (typeof window === "undefined") return
    const snapshot = window.localStorage.getItem(storageKey)
    if (snapshot) {
      try {
        const parsed = JSON.parse(snapshot) as ChatMessage[]
        if (parsed.length) {
          setMessagesState(parsed)
          return
        }
      } catch {
        // ignore cache parse errors
      }
    }
    if (session.ai_text) {
      setMessagesState([
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
    window.localStorage.setItem(storageKey, JSON.stringify(messagesState))
  }, [messagesState, storageKey])

  useEffect(() => {
    return () => {
      if (typeof window === "undefined") return
      window.localStorage.removeItem(storageKey)
    }
  }, [storageKey])

  const refreshTranscript = useCallback(async () => {
    if (!auth.accessToken) return
    setTranscriptLoading(true)
    try {
      const data = await fetchChatTranscript(session.session_id, auth.accessToken)
      if (Array.isArray(data.messages) && data.messages.length) {
        setMessagesState(data.messages)
      }
      if (!modelHydrated && data.followup_model) {
        const normalized = normalizeChatModel(data.followup_model)
        setChatModel(modelOptionIds.has(normalized) ? normalized : FALLBACK_CHAT_MODEL)
        setModelHydrated(true)
      }
    } catch (error) {
      toast.error((error as Error).message || messages.workspace.chat.loadHistoryFailed)
    } finally {
      setTranscriptLoading(false)
    }
  }, [auth.accessToken, session.session_id, modelHydrated, modelOptionIds, messages.workspace.chat.loadHistoryFailed])

  useEffect(() => {
    refreshTranscript()
  }, [refreshTranscript])

  useEffect(() => {
    setModelHydrated(false)
    setChatModel(FALLBACK_CHAT_MODEL)
    setReasoning("medium")
    setVerbosity("medium")
    setTone(session.ai_tone ?? "normal")
  }, [session.session_id, session.ai_tone])

  useEffect(() => {
    if (chatModel !== "gpt-5.2" && reasoning === "none") {
      setReasoning("medium")
    }
  }, [chatModel, reasoning])

  useEffect(() => {
    if (!listRef.current) return
    listRef.current.scrollTop = listRef.current.scrollHeight
  }, [messagesState])

  async function handleAuth(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email || !password) {
      toast.error(messages.workspace.chat.askAfterLoginError)
      return
    }
    setAuthBusy(true)
    try {
      if (authMode === "signIn") {
        await auth.signIn(email, password)
      } else {
        await auth.signUp(email, password)
      }
      setEmail("")
      setPassword("")
    } catch (error) {
      toast.error((error as Error).message || messages.common.unknownError)
    } finally {
      setAuthBusy(false)
    }
  }

  async function handleSend(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!auth.accessToken) {
      toast.error(messages.workspace.chat.askAfterLogin)
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
      model: chatModel,
    }
    setMessagesState((prev) => [...prev, optimistic])
    setIsSending(true)
    try {
      const result = await sendChatMessage(session.session_id, auth.accessToken, {
        message: trimmed,
        reasoning: modelsWithControls.has(chatModel) ? reasoning : null,
        verbosity: modelsWithControls.has(chatModel) ? verbosity : null,
        tone,
        model: chatModel,
      })
      setMessagesState((prev) => [...prev, result.assistant])
      setInput("")
      await refreshTranscript()
    } catch (error) {
      toast.error((error as Error).message || messages.workspace.chat.chatFailed)
      setMessagesState((prev) => prev.filter((item) => item.localId !== optimistic.localId))
    } finally {
      setIsSending(false)
    }
  }

  const loginPanel = (
    <div className="surface-soft space-y-4 rounded-2xl p-4 text-sm">
      <p className="kicker">{messages.workspace.chat.loginToContinue}</p>
      <p className="text-xs text-muted-foreground">{messages.workspace.chat.loginDescription}</p>
      <form onSubmit={handleAuth} className="space-y-3">
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
        <Button type="submit" className="w-full" disabled={authBusy || auth.loading}>
          {authMode === "signIn" ? messages.common.signIn : messages.common.signUp}
        </Button>
      </form>
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
            toast.error((error as Error).message || messages.common.unknownError)
          } finally {
            setAuthBusy(false)
          }
        }}
      >
        {messages.common.continueWithGoogle}
      </Button>
      <div className="text-xs text-muted-foreground">
        <button
          type="button"
          className="underline underline-offset-2"
          onClick={() => setAuthMode((mode) => (mode === "signIn" ? "signUp" : "signIn"))}
        >
          {authMode === "signIn"
            ? `${messages.workspace.chat.signInPrompt} ${messages.workspace.chat.switchToSignUp}`
            : `${messages.workspace.chat.signUpPrompt} ${messages.workspace.chat.switchToSignIn}`}
        </button>
      </div>
      {auth.error && <p className="text-xs text-destructive">{auth.error}</p>}
    </div>
  )

  const initialBlock = session.ai_text ? (
    <div className="surface-soft rounded-2xl p-4 text-sm leading-relaxed text-foreground">
      <div className="mb-2 flex items-center justify-between">
        <p className="kicker">{messages.workspace.chat.initialReading}</p>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs font-semibold tracking-wide text-foreground hover:text-foreground"
          onClick={() => setShowInitial((value) => !value)}
          aria-expanded={showInitial}
        >
          {showInitial ? messages.workspace.chat.collapse : messages.workspace.chat.expand}
        </Button>
      </div>
      {showInitial && <MarkdownContent content={session.ai_text} />}
    </div>
  ) : (
    <div className="surface-soft rounded-2xl border border-dashed p-4 text-sm text-muted-foreground">
      {messages.workspace.chat.noInitialAi}
    </div>
  )

  const chatPanel = (
    <div className="surface-card rounded-2xl p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {auth.avatarUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={auth.avatarUrl} alt={profileName} className="size-11 rounded-full object-cover ring-2 ring-border/70" />
          ) : (
            <div className="flex size-11 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
              {profileName?.[0] ?? "U"}
            </div>
          )}
          <div>
            <p className="kicker">{messages.workspace.chat.title}</p>
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
              toast.success(messages.profileMenu.signedOutToast)
            } catch (error) {
              toast.error((error as Error).message || messages.common.unknownError)
            }
          }}
        >
          {messages.common.signOut}
        </Button>
      </div>

      <div className="space-y-2">
        <p className="kicker">{messages.workspace.chat.modelLabel}</p>
        <div className="grid gap-2 md:grid-cols-3">
          {modelOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              className={cn(
                "rounded-2xl border px-3 py-3 text-left text-sm transition",
                chatModel === option.id
                  ? "border-primary/60 bg-primary/12 text-foreground"
                  : "border-border/60 bg-surface/75 hover:border-primary/40",
              )}
              onClick={() => setChatModel(option.id)}
            >
              <div className="font-semibold">{option.label}</div>
              <p className="mt-1 text-xs text-muted-foreground">{option.description}</p>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-2 md:grid-cols-3">
        <Select value={reasoning} onValueChange={(value) => setReasoning(value)}>
          <SelectTrigger>
            <SelectValue placeholder={messages.workspace.chat.reasoningLabel} />
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
            <SelectValue placeholder={messages.workspace.chat.verbosityLabel} />
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
            <SelectValue placeholder={messages.workspace.chat.toneLabel} />
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

      <div
        ref={listRef}
        className="custom-scrollbar mt-4 flex h-[30rem] flex-col space-y-3 overflow-y-auto rounded-2xl border border-border/40 bg-surface/65 p-3"
      >
        {transcriptLoading ? (
          <div className="flex items-center justify-center gap-2 py-10 text-xs text-muted-foreground">
            <Loader2 className="size-3 animate-spin" />
            {messages.workspace.chat.transcriptLoading}
          </div>
        ) : messagesState.length ? (
          messagesState.map((message) => (
            <ChatBubble key={message.id ?? message.localId} message={message} />
          ))
        ) : (
          <p className="text-center text-xs text-muted-foreground">{messages.workspace.chat.transcriptEmpty}</p>
        )}
      </div>

      <div className="mt-2 text-right text-xs text-muted-foreground">
        {messages.workspace.chat.tokensUsed}: <span className="font-semibold">{totalTokens.toLocaleString()}</span>
      </div>

      <form onSubmit={handleSend} className="mt-3 space-y-3">
        <div className="space-y-1">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={messages.workspace.chat.inputPlaceholder}
            rows={3}
            maxLength={CHAT_MESSAGE_LIMIT}
          />
          <p className="text-right text-xs text-muted-foreground">
            {input.length}/{CHAT_MESSAGE_LIMIT}
          </p>
        </div>
        <Button type="submit" className="w-full rounded-2xl" disabled={isSending}>
          {isSending ? messages.workspace.chat.sending : messages.workspace.chat.send}
        </Button>
      </form>
    </div>
  )

  if (auth.loading) {
    return (
      <div className="surface-soft mt-4 rounded-2xl p-4 text-sm text-muted-foreground">
        {messages.workspace.chat.authChecking}
      </div>
    )
  }

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
        className={cn(
          "max-w-[86%] rounded-2xl border px-3 py-2 text-sm leading-relaxed shadow-sm",
          isAssistant
            ? "border-border/50 bg-surface text-foreground"
            : "border-primary/40 bg-primary text-primary-foreground",
        )}
      >
        <MarkdownContent
          content={message.content}
          className={isAssistant ? "text-foreground" : "text-primary-foreground"}
        />
      </div>
    </div>
  )
}
