"use client"

import Link from "next/link"
import { useEffect, useMemo, useRef, useState } from "react"
import { CircleHelp } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useSessionMutation } from "@/lib/queries"
import { parseManualLines } from "@/lib/api"
import { trackProductEvent } from "@/lib/analytics"
import { useWorkspaceStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import type { ConfigResponse, ModelInfo, SessionRequest } from "@/types/api"
import { toast } from "sonner"

type Props = {
  config: ConfigResponse
}

const QUESTION_LIMIT = 2000
const MANUAL_METHOD_KEY = "x"

const LINE_VALUE_OPTIONS = [
  { value: 6, en: "6 · old yin", zh: "6 · 老阴" },
  { value: 7, en: "7 · young yang", zh: "7 · 少阳" },
  { value: 8, en: "8 · young yin", zh: "8 · 少阴" },
  { value: 9, en: "9 · old yang", zh: "9 · 老阳" },
] as const

const pad = (value: number) => value.toString().padStart(2, "0")

const infoButtonClass =
  "inline-flex size-8 items-center justify-center rounded-full border border-border/70 bg-surface/70 text-foreground transition hover:bg-surface-elevated"

function formatOffsetISOString(date: Date) {
  const year = date.getFullYear()
  const month = pad(date.getMonth() + 1)
  const day = pad(date.getDate())
  const hours = pad(date.getHours())
  const minutes = pad(date.getMinutes())
  const seconds = pad(date.getSeconds())
  const offsetMinutes = date.getTimezoneOffset()
  const offsetSign = offsetMinutes <= 0 ? "+" : "-"
  const offsetHours = pad(Math.floor(Math.abs(offsetMinutes) / 60))
  const offsetMins = pad(Math.abs(offsetMinutes % 60))
  return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}${offsetSign}${offsetHours}:${offsetMins}`
}

function getReasoningLines(modelName: string | undefined, locale: "en" | "zh") {
  const name = modelName?.toLowerCase() ?? ""
  if (name.includes("gpt-5.5")) {
    return locale === "zh"
      ? ["关闭 ≈30s", "极简 ≈40s", "低 ≈50s", "中 ≈65s", "高 ≥90s"]
      : ["None ≈30s", "Minimal ≈40s", "Low ≈50s", "Medium ≈65s", "High ≥90s"]
  }
  if (name.includes("gpt-5.4-mini")) {
    return locale === "zh"
      ? ["极简 ≈15s", "低 ≈20s", "中 ≈30s", "高 ≥60s"]
      : ["Minimal ≈15s", "Low ≈20s", "Medium ≈30s", "High ≥60s"]
  }
  if (name.includes("gpt-5.3-codex")) {
    return locale === "zh"
      ? ["极简 ≈25s", "低 ≈35s", "中 ≈50s", "高 ≥75s"]
      : ["Minimal ≈25s", "Low ≈35s", "Medium ≈50s", "High ≥75s"]
  }
  return locale === "zh"
    ? ["该模型不支持推理力度控制。"]
    : ["This model does not expose reasoning-depth controls."]
}

function manualLineValues(input: string) {
  return input
    .replace(/[,\s]+/g, "")
    .split("")
    .map((value) => Number(value))
    .filter((value) => [6, 7, 8, 9].includes(value))
    .slice(0, 6)
}

function coinLineValue() {
  const coins = Array.from({ length: 3 }, () => (Math.random() < 0.5 ? 2 : 3))
  return {
    coins,
    value: coins.reduce((sum, coin) => sum + coin, 0),
  }
}

function analyzeQuestion(question: string, locale: "en" | "zh") {
  const trimmed = question.trim()
  const highRisk =
    /(suicide|self[-\s]?harm|kill myself|emergency|diagnos|medical|lawsuit|court outcome|stock pick|gambl|彩票|自杀|自残|急诊|诊断|官司结果|股票|彩票|赌博)/i.test(trimmed)
  const prediction =
    /^(will|should|can|is|are|do|does|did|am i)\b/i.test(trimmed) ||
    /(will i|should i|is it|can i|会不会|要不要|能不能|是不是|是否|该不该)/i.test(trimmed)
  const repeat = /(again|same question|repeat|再占|反复|同一个问题)/i.test(trimmed)
  if (!trimmed) return null
  if (highRisk) {
    return {
      tone: "risk",
      title: locale === "zh" ? "高风险问题" : "High-risk question",
      body:
        locale === "zh"
          ? "这类问题只能用来整理观察与求助方向，不能用卦来替代专业判断。"
          : "Use this only to clarify what to observe and what support to seek; do not use a reading as the decision-maker.",
      suggestion:
        locale === "zh"
          ? "我现在应该看清哪些风险、支持与下一步求助？"
          : "What risks, support, and next steps should I clarify now?",
    }
  }
  if (repeat) {
    return {
      tone: "caution",
      title: locale === "zh" ? "避免反复起卦" : "Avoid repeat casting",
      body:
        locale === "zh"
          ? "如果事实没有变化，更适合回到上一次阅读复盘，而不是立刻重问。"
          : "If the facts have not changed, revisit the earlier reading before asking again.",
      suggestion:
        locale === "zh"
          ? "上一次阅读中，我现在最应该复盘什么？"
          : "What should I revisit from the earlier reading now?",
    }
  }
  if (prediction) {
    return {
      tone: "caution",
      title: locale === "zh" ? "建议改成理解型问题" : "Better as an inquiry question",
      body:
        locale === "zh"
          ? "易经更适合问局势、变化与应对，而不是只问会不会。"
          : "The Yi works better when the question asks what to understand, what is changing, and how to respond.",
      suggestion:
        locale === "zh"
          ? `我应该怎样理解“${trimmed.replace(/[？?]$/, "")}”这件事的局势与下一步？`
          : `What should I understand about ${trimmed.replace(/[?.!]$/, "")}, and what should I do next?`,
    }
  }
  return {
    tone: "good",
    title: locale === "zh" ? "问题质量良好" : "Question quality is good",
    body:
      locale === "zh"
        ? "这个问题已经偏向理解局势与行动边界，适合进入起卦。"
        : "This asks for understanding and action boundaries, which fits a serious reading.",
    suggestion: null,
  }
}

export function CastForm({ config }: Props) {
  const auth = useAuthContext()
  const { messages, locale, toLocalePath } = useI18n()
  const defaultsHydrated = useRef(false)
  const [lastCoinToss, setLastCoinToss] = useState<number[] | null>(null)
  const form = useWorkspaceStore((state) => state.form)
  const updateForm = useWorkspaceStore((state) => state.updateForm)
  const setForm = useWorkspaceStore((state) => state.setForm)
  const setResult = useWorkspaceStore((state) => state.setResult)
  const activeToneOption = messages.workspace.tones.find((option) => option.value === form.aiTone)
  const questionLength = form.userQuestion?.length ?? 0
  const canUseAi = Boolean(auth.user)
  const questionCoaching = useMemo(() => analyzeQuestion(form.userQuestion, locale), [form.userQuestion, locale])
  const currentManualValues = manualLineValues(form.manualLines)

  useEffect(() => {
    if (auth.loading) return
    if (!canUseAi && form.enableAi) {
      updateForm("enableAi", false)
    }
  }, [auth.loading, canUseAi, form.enableAi, updateForm])

  const activeModel = useMemo<ModelInfo | undefined>(
    () => config.ai_models.find((model) => model.name === form.aiModel),
    [config.ai_models, form.aiModel],
  )

  useEffect(() => {
    if (defaultsHydrated.current) return
    if (!config.topics.length || !config.methods.length) return

    const current = useWorkspaceStore.getState().form
    const preferredTopic =
      config.topics.find((topic) => topic.label === "事业")?.label || config.topics[0]?.label || ""
    const preferredMethod =
      config.methods.find((method) => method.label === "五十蓍草法")?.key ||
      config.methods[0]?.key ||
      ""
    setForm({
      topic: current.topic || preferredTopic,
      methodKey: current.methodKey || preferredMethod,
      aiModel: current.aiModel || config.ai_models[0]?.name || "gpt-5.5",
    })
    defaultsHydrated.current = true
  }, [config, setForm])

  useEffect(() => {
    if (!activeModel) return
    if (activeModel.reasoning.length > 0) {
      const fallback = activeModel.default_reasoning || activeModel.reasoning[0]
      if (!form.aiReasoning || !activeModel.reasoning.includes(form.aiReasoning)) {
        updateForm("aiReasoning", fallback)
      }
    } else if (form.aiReasoning) {
      updateForm("aiReasoning", null)
    }

    if (!activeModel.verbosity) {
      updateForm("aiVerbosity", null)
    } else if (!form.aiVerbosity) {
      updateForm("aiVerbosity", activeModel.default_verbosity ?? "medium")
    }
  }, [activeModel, form.aiReasoning, form.aiVerbosity, updateForm])

  const mutation = useSessionMutation({
    accessToken: auth.accessToken ?? undefined,
	    onSuccess: (payload) => {
	      setResult(payload)
	      trackProductEvent("reading_created", {
	        method: typeof payload.session_dict?.method === "string" ? payload.session_dict.method : form.methodKey,
	        ai_enabled: Boolean(form.enableAi),
	        moving_line_count: payload.hex_overview?.lines?.filter((line) => line.is_moving).length ?? 0,
	      })
	      toast.success(messages.workspace.cast.aiEnabledToast)
	    },
    onError: (error) => {
      const detail = error.message?.trim()
      const friendly =
        detail === "未知的占卜方法: "
          ? messages.workspace.cast.topicMissingMethod
          : detail || messages.workspace.cast.requestFailed
      toast.error(friendly)
    },
  })

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    let manualLines: number[] | undefined
    try {
      manualLines = parseManualLines(form.manualLines)
    } catch (error) {
      if (form.methodKey === MANUAL_METHOD_KEY) {
        const reason = (error as Error).message
        if (reason === "manual_lines_count_error") {
          toast.error(messages.workspace.cast.manualLinesCountError)
        } else if (reason === "manual_lines_value_error") {
          toast.error(messages.workspace.cast.manualLinesValueError)
        } else {
          toast.error(messages.workspace.cast.requestFailed)
        }
        return
      }
    }

    let timestamp: string | null = null

    if (form.useCurrentTime) {
      timestamp = formatOffsetISOString(new Date())
    } else {
      if (!form.customTimestamp) {
        toast.error(messages.workspace.cast.timestampRequired)
        return
      }
      const customDate = new Date(form.customTimestamp)
      if (Number.isNaN(customDate.getTime())) {
        toast.error(messages.workspace.cast.invalidTimestamp)
        return
      }
      timestamp = formatOffsetISOString(customDate)
    }

    if (!timestamp) {
      toast.error(messages.workspace.cast.parseTimestampFailed)
      return
    }

	    const payload: SessionRequest = {
      topic: form.topic,
      user_question: form.userQuestion || undefined,
      user_context: form.userContext || undefined,
      method_key: form.methodKey,
      manual_lines: manualLines,
      use_current_time: false,
      timestamp,
      enable_ai: form.enableAi,
      access_password: form.enableAi ? form.accessPassword || null : null,
      ai_model: form.aiModel,
      ai_reasoning: form.aiReasoning || null,
      ai_verbosity: form.aiVerbosity || null,
      ai_tone: form.aiTone,
	    }
	
	    trackProductEvent("start_cast_clicked", {
	      topic: form.topic,
	      method: form.methodKey,
	      ai_enabled: Boolean(form.enableAi),
	      manual_line_count: manualLines?.length ?? 0,
	    })
	    mutation.mutate(payload)
	  }

  const reasoningLines = getReasoningLines(activeModel?.name, locale)
  const appendManualLine = (value: number) => {
    const nextValues = currentManualValues.length >= 6 ? [value] : [...currentManualValues, value]
    setForm({
      methodKey: MANUAL_METHOD_KEY,
      manualLines: nextValues.join(""),
    })
  }
  const clearManualLines = () => {
    setLastCoinToss(null)
    setForm({
      methodKey: MANUAL_METHOD_KEY,
      manualLines: "",
    })
  }
  const tossCoinLine = () => {
    const result = coinLineValue()
    setLastCoinToss(result.coins)
    appendManualLine(result.value)
  }
  const copy =
    locale === "zh"
      ? {
          promptTitle: "你现在真正要判断什么？",
          promptBody: "先写清问题，再补充真正影响判断的背景；卦象、经典文本与追问会围绕同一条判断链展开。",
          contextLabel: "相关背景",
          contextPlaceholder: "例如：对方已经催了两次，但预算、负责人、时间表还没完全确定。",
          modeLabel: "阅读预设",
          quickTitle: "快速阅读",
          quickBody: "最短路径得到结论、证据和下一步。",
          deepTitle: "深度阅读",
          deepBody: "登录后启用完整 AI 解读与后续追问。",
          researchTitle: "经典研究",
          researchBody: "优先保留卦辞、动爻、纳甲与来源对照。",
          followupTitle: "仅建线程",
          followupBody: "先生成可追踪阅读，后续在同一线程补问。",
	          advanced: "高级设置",
	          advancedDescription: "起卦方法、时间、手动六爻与 AI 模型控制。",
	          questionApply: "采用建议问题",
	          ritualTitle: "起卦导引",
	          ritualBody: "用铜钱按钮逐爻生成，或直接用六爻构建器输入。六爻始终自下而上。",
	          coinButton: "掷一爻铜钱",
	          clearLines: "清空六爻",
	          lineProgress: "已生成",
	          lastCoins: "上次铜钱",
	          lineBuilder: "六爻构建器",
	        }
	      : {
          promptTitle: "What are you actually deciding?",
          promptBody: "Ask clearly, then add the context that actually changes the decision. The reading, evidence, and follow-up stay in one thread.",
          contextLabel: "Relevant context",
          contextPlaceholder: "Example: They are pushing for a fast answer, but budget, owner, and timeline are still unclear.",
          modeLabel: "Reading preset",
          quickTitle: "Quick reading",
          quickBody: "Shortest path to judgment, evidence, and next step.",
          deepTitle: "Deep reading",
          deepBody: "Enable full AI interpretation and follow-up after sign-in.",
          researchTitle: "Classical research",
          researchBody: "Keep more hexagram text, moving-line, Najia, and source comparison.",
          followupTitle: "Follow-up only",
          followupBody: "Create a trackable reading now, then continue in the same thread.",
	          advanced: "Advanced settings",
	          advancedDescription: "Casting method, time, manual lines, and AI model controls.",
	          questionApply: "Use suggested question",
	          ritualTitle: "Casting ritual",
	          ritualBody: "Use the coin button line by line, or enter exact values with the line builder. Lines are always bottom to top.",
	          coinButton: "Toss one coin line",
	          clearLines: "Clear lines",
	          lineProgress: "Built",
	          lastCoins: "Last coins",
	          lineBuilder: "Line builder",
	        }

  const readingModes = [
    {
      id: "quick",
      title: copy.quickTitle,
      body: copy.quickBody,
      active: !form.enableAi && (!form.aiVerbosity || form.aiVerbosity === "medium"),
      apply: () =>
        setForm({
          enableAi: false,
          aiReasoning: "medium",
          aiVerbosity: "medium",
        }),
    },
    {
      id: "deep",
      title: copy.deepTitle,
      body: copy.deepBody,
      active: form.enableAi,
      apply: () => {
        if (!canUseAi) {
          toast.error(messages.workspace.cast.aiLoginHint)
          return
        }
        setForm({
          enableAi: true,
          aiModel: activeModel?.name || form.aiModel || "gpt-5.5",
          aiReasoning: activeModel?.default_reasoning || form.aiReasoning || "medium",
          aiVerbosity: activeModel?.default_verbosity || form.aiVerbosity || "medium",
        })
      },
    },
    {
      id: "research",
      title: copy.researchTitle,
      body: copy.researchBody,
      active: !form.enableAi && form.aiVerbosity === "high",
      apply: () =>
        setForm({
          enableAi: false,
          aiReasoning: "medium",
          aiVerbosity: "high",
        }),
    },
    {
      id: "followup",
      title: copy.followupTitle,
      body: copy.followupBody,
      active: !form.enableAi && form.aiVerbosity === "low",
      apply: () =>
        setForm({
          enableAi: false,
          aiReasoning: "minimal",
          aiVerbosity: "low",
        }),
    },
  ]

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-5xl">
      <section className="surface-card grid gap-6 rounded-lg p-5 sm:p-6 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-5">
          <div className="flex gap-4">
            <span className="oracle-mark mt-1" aria-hidden="true">
              🔮
            </span>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">{copy.promptTitle}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{copy.promptBody}</p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_13rem]">
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
	                  <label htmlFor="reading-question" className="text-sm font-medium text-foreground">{messages.workspace.cast.questionLabel}</label>
	                  <span className="text-xs text-muted-foreground">
                    {questionLength}/{QUESTION_LIMIT}
                  </span>
                </div>
	                <Textarea
	                  id="reading-question"
	                  placeholder={messages.workspace.cast.questionPlaceholder}
                  value={form.userQuestion}
                  onChange={(event) => updateForm("userQuestion", event.target.value)}
                  rows={7}
                  maxLength={QUESTION_LIMIT}
	                  className="min-h-[12rem] text-base leading-relaxed"
	                />
	                {questionCoaching && (
	                  <div
	                    className={cn(
	                      "rounded-md border p-3 text-sm",
	                      questionCoaching.tone === "good" && "border-primary/30 bg-primary/10",
	                      questionCoaching.tone === "caution" && "imperial-highlight-panel",
	                      questionCoaching.tone === "risk" && "border-destructive/40 bg-destructive/10",
	                    )}
	                  >
	                    <p className="font-semibold text-foreground">{questionCoaching.title}</p>
	                    <p className="mt-1 leading-6 text-muted-foreground">{questionCoaching.body}</p>
	                    {questionCoaching.suggestion && (
	                      <button
	                        type="button"
	                        onClick={() => updateForm("userQuestion", questionCoaching.suggestion || "")}
	                        className="mt-2 text-xs font-semibold text-primary underline underline-offset-4"
	                      >
	                        {copy.questionApply}
	                      </button>
	                    )}
	                  </div>
	                )}
	              </div>
	              <div className="space-y-2">
	                <label htmlFor="reading-context" className="text-sm font-medium text-foreground">{copy.contextLabel}</label>
	                <Textarea
	                  id="reading-context"
	                  placeholder={copy.contextPlaceholder}
                  value={form.userContext}
                  onChange={(event) => updateForm("userContext", event.target.value)}
                  rows={3}
                  maxLength={1200}
                  className="min-h-[6rem] text-sm leading-relaxed"
                />
              </div>
            </div>

	            <div className="space-y-2">
	              <label id="reading-topic-label" className="text-sm font-medium text-foreground">{messages.workspace.cast.topicLabel}</label>
	              <Select value={form.topic} onValueChange={(value) => updateForm("topic", value)}>
	                <SelectTrigger aria-labelledby="reading-topic-label">
                  <SelectValue placeholder={messages.workspace.cast.topicLabel} />
                </SelectTrigger>
                <SelectContent>
                  {config.topics.map((topic) => (
                    <SelectItem value={topic.label} key={topic.key}>
                      {topic.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <aside className="surface-soft flex flex-col justify-between gap-5 rounded-lg p-4">
          <div className="space-y-3">
            <p className="text-sm font-semibold text-foreground">{copy.modeLabel}</p>
            <div className="grid gap-2">
              {readingModes.map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  onClick={mode.apply}
	                  className={cn(
                    "rounded-lg border p-3 text-left transition",
                    mode.active
                      ? "border-primary/60 bg-primary/10 text-foreground"
                      : "border-border/60 bg-surface/70 hover:border-primary/40",
	                  )}
	                  aria-pressed={mode.active}
	                >
                  <span className="text-sm font-semibold">{mode.title}</span>
                  <span className="mt-1 block text-xs leading-relaxed text-muted-foreground">{mode.body}</span>
                </button>
              ))}
            </div>
          </div>

	          <div className="space-y-3">
	            <div className="rounded-lg border border-border/60 bg-surface p-3">
	              <div className="flex items-start justify-between gap-3">
	                <div>
	                  <p className="text-sm font-semibold text-foreground">{copy.ritualTitle}</p>
	                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{copy.ritualBody}</p>
	                </div>
	                <span className="rounded-md border border-border/60 px-2 py-1 text-xs text-muted-foreground">
	                  {copy.lineProgress} {currentManualValues.length}/6
	                </span>
	              </div>
	              <div className="mt-3 grid gap-2 sm:grid-cols-2">
	                <Button type="button" variant="secondary" className="rounded-md" onClick={tossCoinLine}>
	                  {copy.coinButton}
	                </Button>
	                <Button type="button" variant="outline" className="rounded-md" onClick={clearManualLines}>
	                  {copy.clearLines}
	                </Button>
	              </div>
	              {lastCoinToss && (
	                <p className="mt-2 text-xs text-muted-foreground">
	                  {copy.lastCoins}: {lastCoinToss.join(" + ")} = {lastCoinToss.reduce((sum, coin) => sum + coin, 0)}
	                </p>
	              )}
	              <div className="mt-3">
	                <p className="text-xs font-semibold uppercase tracking-[0.16rem] text-muted-foreground">{copy.lineBuilder}</p>
	                <div className="mt-2 grid grid-cols-2 gap-2">
	                  {LINE_VALUE_OPTIONS.map((option) => (
	                    <button
	                      key={option.value}
	                      type="button"
	                      onClick={() => appendManualLine(option.value)}
	                      className="rounded-md border border-border/60 bg-surface-elevated px-2 py-2 text-xs font-semibold text-foreground transition hover:border-primary/50"
	                    >
	                      {locale === "zh" ? option.zh : option.en}
	                    </button>
	                  ))}
	                </div>
	              </div>
	              <ol className="mt-3 grid grid-cols-6 gap-1 text-center text-xs" aria-label={messages.workspace.cast.manualLinesLabel}>
	                {Array.from({ length: 6 }).map((_, index) => (
	                  <li key={index} className="rounded-md border border-border/50 bg-background px-1 py-1 text-muted-foreground">
	                    {currentManualValues[index] ?? "·"}
	                  </li>
	                ))}
	              </ol>
	            </div>

	            <Sheet>
              <SheetTrigger asChild>
                <Button type="button" variant="outline" className="w-full rounded-md">
                  {copy.advanced}
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
                <SheetHeader>
                  <SheetTitle>{copy.advanced}</SheetTitle>
                  <SheetDescription>{copy.advancedDescription}</SheetDescription>
                </SheetHeader>

                <div className="mt-6 space-y-6">
                  <div className="space-y-2">
                    <p className="text-sm font-medium text-foreground">{messages.workspace.cast.methodLabel}</p>
                    <Select value={form.methodKey} onValueChange={(value) => updateForm("methodKey", value)}>
                      <SelectTrigger>
                        <SelectValue placeholder={messages.workspace.cast.methodLabel} />
                      </SelectTrigger>
                      <SelectContent>
                        {config.methods.map((method) => (
                          <SelectItem key={method.key} value={method.key}>
                            {method.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

	                  {form.methodKey === MANUAL_METHOD_KEY && (
	                    <div className="space-y-2">
	                      <div className="flex items-center justify-between gap-3">
	                        <label htmlFor="manual-lines-raw" className="text-sm font-medium text-foreground">{messages.workspace.cast.manualLinesLabel}</label>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button type="button" className={infoButtonClass}>
                              <CircleHelp className="size-4" aria-hidden="true" />
                              <span className="sr-only">{messages.workspace.cast.lineInputHintAria}</span>
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs space-y-1 text-left leading-relaxed">
                            {messages.workspace.cast.lineHints.map((hint) => (
                              <p key={hint}>{hint}</p>
                            ))}
                          </TooltipContent>
                        </Tooltip>
                      </div>
	                      <Input
	                        id="manual-lines-raw"
	                        value={form.manualLines}
                        onChange={(event) => updateForm("manualLines", event.target.value)}
                        placeholder={messages.workspace.cast.manualLinesPlaceholder}
                      />
                    </div>
                  )}

                  <div className="surface-soft space-y-3 rounded-lg p-4">
                    <p className="text-sm font-medium text-foreground">{messages.workspace.cast.timeLabel}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">{messages.workspace.cast.useCurrentTime}</span>
                      <Switch
                        checked={form.useCurrentTime}
                        onCheckedChange={(checked) => updateForm("useCurrentTime", checked)}
                      />
                    </div>
                    <Input
                      type="datetime-local"
                      value={form.customTimestamp}
                      disabled={form.useCurrentTime}
                      onChange={(event) => updateForm("customTimestamp", event.target.value)}
                    />
                  </div>

                  <div className="space-y-4 border-t border-border/60 pt-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-medium text-foreground">{messages.workspace.cast.aiEnableLabel}</p>
                        {!auth.loading && !canUseAi && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            {messages.workspace.cast.aiLoginHint}{" "}
                            <Link href={toLocalePath("/profile")} className="underline underline-offset-2">
                              {messages.nav.profile}
                            </Link>
                            .
                          </p>
                        )}
                      </div>
                      <Switch
                        checked={form.enableAi}
                        disabled={auth.loading || !canUseAi}
                        onCheckedChange={(checked) => updateForm("enableAi", checked)}
                      />
                    </div>

                    {form.enableAi && (
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <p className="text-sm font-medium text-foreground">{messages.workspace.cast.accessPasswordLabel}</p>
                          <Input
                            type="password"
                            value={form.accessPassword}
                            onChange={(event) => updateForm("accessPassword", event.target.value)}
                            placeholder={messages.workspace.cast.accessPasswordPlaceholder}
                          />
                        </div>

                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-foreground">{messages.workspace.cast.modelLabel}</p>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button type="button" className={infoButtonClass}>
                                  <CircleHelp className="size-4" aria-hidden="true" />
                                  <span className="sr-only">{messages.workspace.cast.modelInfoAria}</span>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-sm space-y-1 text-left leading-relaxed">
                                {messages.workspace.cast.modelSpeedLines.map((line) => (
                                  <p key={line}>{line}</p>
                                ))}
                                <p className="pt-1 opacity-80">{messages.workspace.cast.modelQualityLine}</p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                          <Select value={form.aiModel} onValueChange={(value) => updateForm("aiModel", value)}>
                            <SelectTrigger>
                              <SelectValue placeholder={messages.workspace.cast.modelLabel} />
                            </SelectTrigger>
                            <SelectContent>
                              {config.ai_models.map((model) => (
                                <SelectItem key={model.name} value={model.name}>
                                  {model.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {!!activeModel?.reasoning.length && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-foreground">{messages.workspace.cast.reasoningLabel}</p>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className={infoButtonClass}>
                                    <CircleHelp className="size-4" aria-hidden="true" />
                                    <span className="sr-only">{messages.workspace.cast.reasoningInfoAria}</span>
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-sm space-y-1 text-left leading-relaxed">
                                  {reasoningLines.map((line) => (
                                    <p key={line}>{line}</p>
                                  ))}
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <Select
                              value={form.aiReasoning ?? ""}
                              onValueChange={(value) => updateForm("aiReasoning", value)}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder={messages.workspace.cast.reasoningLabel} />
                              </SelectTrigger>
                              <SelectContent>
                                {activeModel.reasoning.map((level) => (
                                  <SelectItem key={level} value={level}>
                                    {level}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        )}

                        {activeModel?.verbosity && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <p className="text-sm font-medium text-foreground">{messages.workspace.cast.verbosityLabel}</p>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <button type="button" className={infoButtonClass}>
                                    <CircleHelp className="size-4" aria-hidden="true" />
                                    <span className="sr-only">{messages.workspace.cast.verbosityInfoAria}</span>
                                  </button>
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs space-y-1 text-left leading-relaxed">
                                  {messages.workspace.cast.verbosityLines.map((line) => (
                                    <p key={line}>{line}</p>
                                  ))}
                                </TooltipContent>
                              </Tooltip>
                            </div>
                            <Select
                              value={form.aiVerbosity ?? ""}
                              onValueChange={(value) => updateForm("aiVerbosity", value)}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder={messages.workspace.cast.verbosityLabel} />
                              </SelectTrigger>
                              <SelectContent>
                                {["low", "medium", "high"].map((level) => (
                                  <SelectItem key={level} value={level}>
                                    {level}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        )}

                        <div className="space-y-2">
                          <p className="text-sm font-medium text-foreground">{messages.workspace.cast.toneLabel}</p>
                          <Select value={form.aiTone} onValueChange={(value) => updateForm("aiTone", value)}>
                            <SelectTrigger>
                              <SelectValue placeholder={messages.workspace.cast.toneLabel} />
                            </SelectTrigger>
                            <SelectContent>
                              {messages.workspace.tones.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                  {option.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-muted-foreground">
                            {activeToneOption?.description ?? messages.workspace.cast.toneDescriptionDefault}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </SheetContent>
            </Sheet>

            <Button
              type="submit"
              size="lg"
              disabled={mutation.isPending}
              className="h-11 w-full rounded-md text-sm font-semibold"
            >
              {mutation.isPending ? messages.workspace.cast.submitLoading : messages.workspace.cast.submitIdle}
            </Button>
          </div>
        </aside>
      </section>
    </form>
  )
}
