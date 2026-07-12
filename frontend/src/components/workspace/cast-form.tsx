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
type ReadingPreset = "chart" | "standard" | "deep"

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

function formatLocalDateTime(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function getReasoningLines(modelName: string | undefined, locale: "en" | "zh") {
  const name = modelName?.toLowerCase() ?? ""
  if (name.includes("gpt-5.6")) {
    return locale === "zh"
      ? ["关闭：直接回答", "低 / 中：日常占断", "高 / 超高：复杂局势", "最大：最深推演，耗时最长"]
      : ["None: direct response", "Low / Medium: everyday readings", "High / XHigh: complex situations", "Max: deepest and slowest"]
  }
  if (name.includes("gpt-5.5")) {
    return locale === "zh"
      ? ["关闭 ≈30s", "极简 ≈40s", "低 ≈50s", "中 ≈65s", "高 ≥90s"]
      : ["None ≈30s", "Minimal ≈40s", "Low ≈50s", "Medium ≈65s", "High ≥90s"]
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

function levelLabel(level: string, locale: "en" | "zh") {
  if (locale === "en") return level === "xhigh" ? "X-high" : level.charAt(0).toUpperCase() + level.slice(1)
  return {
    none: "关闭",
    minimal: "极简",
    low: "低",
    medium: "中",
    high: "高",
    xhigh: "极高",
    max: "最大",
  }[level] ?? level
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
          ? "如果事实没有变化，更适合回到上一次卦例查看应验，而不是立刻重问。"
          : "If the facts have not changed, revisit the earlier reading before asking again.",
      suggestion:
        locale === "zh"
          ? "上一次卦例中，我现在最应该观察什么？"
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
  const defaultModel = config.ai_models.find((model) => model.name === config.default_model) ?? config.ai_models[0]
  const standardModel = config.ai_models.find((model) => model.tier === "standard") ?? defaultModel
  const deepModel = config.ai_models.find((model) => model.tier === "deep") ?? standardModel
  const resolvedModelName = config.model_aliases[form.aiModel] ?? form.aiModel

  useEffect(() => {
    if (auth.loading) return
    if (!canUseAi && form.enableAi) {
      updateForm("enableAi", false)
    }
  }, [auth.loading, canUseAi, form.enableAi, updateForm])

  const activeModel = useMemo<ModelInfo | undefined>(
    () => config.ai_models.find((model) => model.name === resolvedModelName) ?? defaultModel,
    [config.ai_models, defaultModel, resolvedModelName],
  )

  useEffect(() => {
    if (activeModel && form.aiModel !== activeModel.name) {
      updateForm("aiModel", activeModel.name)
    }
  }, [activeModel, form.aiModel, updateForm])

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
    const requestedTimestamp = new URLSearchParams(window.location.search).get("timestamp")
    const requestedDate = requestedTimestamp ? new Date(requestedTimestamp) : null
    setForm({
      topic: current.topic || preferredTopic,
      methodKey: current.methodKey || preferredMethod,
      aiModel: current.aiModel || config.default_model || config.ai_models[0]?.name || "",
      ...(requestedDate && !Number.isNaN(requestedDate.getTime())
        ? { useCurrentTime: false, customTimestamp: formatLocalDateTime(requestedDate) }
        : {}),
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
          contextLabel: "相关背景",
          contextPlaceholder: "例如：对方已经催了两次，但预算、负责人、时间表还没完全确定。",
          modeLabel: "解读方式",
          chartTitle: "仅排盘",
          chartBody: "生成卦盘、纳甲与经典依据，不调用 AI。",
          standardTitle: "标准解读",
          standardBody: "默认使用 GPT-5.6 Terra，兼顾质量与速度。",
          deepTitle: "深度解读",
          deepBody: "使用 GPT-5.6 Sol 深入判断复杂问题。",
          advanced: "时间与原始输入",
          advancedDescription: "调整起卦时间与原始六爻输入。",
          questionApply: "采用建议问题",
          ritualTitle: "六爻起卦",
          ritualBody: "用铜钱逐爻生成，或直接选择 6/7/8/9；右侧实时显示本次卦象。六爻始终自下而上。",
          coinButton: "掷一爻铜钱",
          clearLines: "清空六爻",
          lineProgress: "已生成",
          lastCoins: "上次铜钱",
          lineBuilder: "六爻构建器",
          previewTitle: "实时卦象",
          previewBody: "第 1 爻在最下方，老阴/老阳会以金色标记为动爻。",
          aiSettingsTitle: "AI 解读设置",
          aiSettingsBody: "选择深度解读后在这里直接调试，不再藏进高级设置。",
          aiOffBody: "仅排盘不会调用 AI。",
        }
      : {
          contextLabel: "Relevant context",
          contextPlaceholder: "Example: They are pushing for a fast answer, but budget, owner, and timeline are still unclear.",
          modeLabel: "Interpretation",
          chartTitle: "Chart only",
          chartBody: "Generate the chart, Najia, and classical basis without AI.",
          standardTitle: "Standard",
          standardBody: "Use GPT-5.6 Terra for balanced quality and speed.",
          deepTitle: "Deep",
          deepBody: "Use GPT-5.6 Sol for difficult divination questions.",
          advanced: "Time and raw input",
          advancedDescription: "Adjust the cast time and raw six-line input.",
          questionApply: "Use suggested question",
          ritualTitle: "Six-line cast",
          ritualBody: "Use the coin button line by line, or choose exact 6/7/8/9 values. The live hexagram updates beside the builder. Lines are bottom to top.",
          coinButton: "Toss one coin line",
          clearLines: "Clear lines",
          lineProgress: "Built",
          lastCoins: "Last coins",
          lineBuilder: "Line builder",
          previewTitle: "Live hexagram",
          previewBody: "Line 1 is at the bottom; old yin and old yang are marked as moving in gold.",
          aiSettingsTitle: "AI reading settings",
          aiSettingsBody: "Deep reading exposes the model controls here instead of hiding them behind Advanced.",
          aiOffBody: "Chart only does not call AI.",
        }

  const selectedPreset: ReadingPreset = !form.enableAi ? "chart" : activeModel?.tier === "deep" ? "deep" : "standard"
  const readingModes = [
    {
      id: "chart",
      title: copy.chartTitle,
      body: copy.chartBody,
      active: selectedPreset === "chart" && !form.enableAi,
      apply: () => {
        setForm({
          enableAi: false,
          aiReasoning: "medium",
          aiVerbosity: "medium",
        })
      },
    },
    {
      id: "standard",
      title: copy.standardTitle,
      body: copy.standardBody,
      active: selectedPreset === "standard" && form.enableAi,
      apply: () => {
        if (!canUseAi) {
          toast.error(messages.workspace.cast.aiLoginHint)
          return
        }
        setForm({
          enableAi: true,
          aiModel: standardModel?.name ?? config.default_model,
          aiReasoning: standardModel?.default_reasoning ?? standardModel?.reasoning[0] ?? null,
          aiVerbosity: standardModel?.default_verbosity ?? null,
        })
      },
    },
    {
      id: "deep",
      title: copy.deepTitle,
      body: copy.deepBody,
      active: selectedPreset === "deep" && form.enableAi,
      apply: () => {
        if (!canUseAi) {
          toast.error(messages.workspace.cast.aiLoginHint)
          return
        }
        setForm({
          enableAi: true,
          aiModel: deepModel?.name ?? standardModel?.name ?? config.default_model,
          aiReasoning: deepModel?.default_reasoning ?? deepModel?.reasoning[0] ?? null,
          aiVerbosity: deepModel?.default_verbosity ?? null,
        })
      },
    },
  ]

  const showAiControls = selectedPreset === "deep" || form.enableAi

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[88rem] px-3 sm:px-5">
      <section className="surface-card rounded-lg p-5 sm:p-6">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(25rem,0.72fr)]">
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_14rem]">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label htmlFor="reading-question" className="text-sm font-medium text-foreground">
                    {messages.workspace.cast.questionLabel}
                  </label>
                  <span className="text-xs text-muted-foreground">
                    {questionLength}/{QUESTION_LIMIT}
                  </span>
                </div>
                <Textarea
                  id="reading-question"
                  placeholder={messages.workspace.cast.questionPlaceholder}
                  value={form.userQuestion}
                  onChange={(event) => updateForm("userQuestion", event.target.value)}
                  rows={5}
                  maxLength={QUESTION_LIMIT}
                  className="min-h-[10rem] text-base leading-relaxed"
                />
              </div>

              <div className="space-y-2">
                <label id="reading-topic-label" className="text-sm font-medium text-foreground">
                  {messages.workspace.cast.topicLabel}
                </label>
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

            {questionCoaching && questionCoaching.tone !== "good" && (
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

            <details className="rounded-lg border border-border/60 bg-surface px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium text-foreground">{copy.contextLabel}</summary>
              <Textarea
                id="reading-context"
                placeholder={copy.contextPlaceholder}
                value={form.userContext}
                onChange={(event) => updateForm("userContext", event.target.value)}
                rows={3}
                maxLength={1200}
                className="mt-3 min-h-24 text-sm leading-relaxed"
              />
            </details>
          </div>

          <aside className="surface-soft space-y-4 rounded-lg p-4">
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

            <div className={cn("rounded-lg border p-4", showAiControls ? "imperial-highlight-panel" : "border-border/60 bg-surface")}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-foreground">{copy.aiSettingsTitle}</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {showAiControls ? copy.aiSettingsBody : copy.aiOffBody}
                  </p>
                  {!auth.loading && !canUseAi && showAiControls && (
                    <p className="mt-2 text-xs text-muted-foreground">
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
                  onCheckedChange={(checked) => {
                    setForm({
                      enableAi: checked,
                      aiModel: checked ? standardModel?.name ?? config.default_model : form.aiModel,
                      aiReasoning: checked ? standardModel?.default_reasoning ?? standardModel?.reasoning[0] ?? null : form.aiReasoning,
                      aiVerbosity: checked ? standardModel?.default_verbosity ?? null : form.aiVerbosity,
                    })
                  }}
                />
              </div>

              {form.enableAi && (
                <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-1">
                  <div className="space-y-2 md:col-span-2 xl:col-span-1">
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
                            {model.label}
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
                      <Select value={form.aiReasoning ?? ""} onValueChange={(value) => updateForm("aiReasoning", value)}>
                        <SelectTrigger>
                          <SelectValue placeholder={messages.workspace.cast.reasoningLabel} />
                        </SelectTrigger>
                        <SelectContent>
                          {activeModel.reasoning.map((level) => (
                            <SelectItem key={level} value={level}>
                              {levelLabel(level, locale)}
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
                      <Select value={form.aiVerbosity ?? ""} onValueChange={(value) => updateForm("aiVerbosity", value)}>
                        <SelectTrigger>
                          <SelectValue placeholder={messages.workspace.cast.verbosityLabel} />
                        </SelectTrigger>
                        <SelectContent>
                          {["low", "medium", "high"].map((level) => (
                            <SelectItem key={level} value={level}>
                              {levelLabel(level, locale)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  <div className="space-y-2 md:col-span-2 xl:col-span-1">
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
          </aside>
        </div>

        <div className="mt-6 space-y-4">
          <div className="grid gap-3 sm:grid-cols-[14rem_minmax(0,1fr)] sm:items-end">
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
            <p className="text-xs leading-5 text-muted-foreground">
              {locale === "zh" ? "选择传统起卦方式；只有手动六爻会展开逐爻构建器。" : "Choose a casting method; the line builder opens only for manual six-line input."}
            </p>
          </div>

          {form.methodKey === MANUAL_METHOD_KEY && (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(19rem,0.55fr)]">
          <div className="rounded-lg border border-border/60 bg-surface p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-foreground">{copy.ritualTitle}</p>
                <p className="mt-1 max-w-2xl text-xs leading-5 text-muted-foreground">{copy.ritualBody}</p>
              </div>
              <span className="rounded-md border border-border/60 px-2 py-1 text-xs text-muted-foreground">
                {copy.lineProgress} {currentManualValues.length}/6
              </span>
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-2">
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
            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-[0.16rem] text-muted-foreground">{copy.lineBuilder}</p>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
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
            <ol className="mt-4 grid grid-cols-6 gap-1 text-center text-xs" aria-label={messages.workspace.cast.manualLinesLabel}>
              {Array.from({ length: 6 }).map((_, index) => (
                <li key={index} className="rounded-md border border-border/50 bg-background px-1 py-1 text-muted-foreground">
                  {currentManualValues[index] ?? "·"}
                </li>
              ))}
            </ol>
          </div>

          <CastHexagramPreview
            values={currentManualValues}
            title={copy.previewTitle}
            body={copy.previewBody}
            locale={locale}
          />
          </div>
          )}
        </div>

        <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
          <Sheet>
            <SheetTrigger asChild>
              <Button type="button" variant="outline" className="rounded-md">
                {copy.advanced}
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
              <SheetHeader>
                <SheetTitle>{copy.advanced}</SheetTitle>
                <SheetDescription>{copy.advancedDescription}</SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-6">
                {form.methodKey === MANUAL_METHOD_KEY && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <label htmlFor="manual-lines-raw" className="text-sm font-medium text-foreground">
                        {messages.workspace.cast.manualLinesLabel}
                      </label>
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
              </div>
            </SheetContent>
          </Sheet>

          <Button
            type="submit"
            size="lg"
            disabled={mutation.isPending}
            className="h-11 w-full rounded-md text-sm font-semibold sm:w-72"
          >
            {mutation.isPending ? messages.workspace.cast.submitLoading : messages.workspace.cast.submitIdle}
          </Button>
        </div>
      </section>
    </form>
  )
}

function CastHexagramPreview({
  values,
  title,
  body,
  locale,
}: {
  values: number[]
  title: string
  body: string
  locale: "en" | "zh"
}) {
  const lines = Array.from({ length: 6 }, (_, index) => {
    const position = 6 - index
    const value = values[position - 1]
    return { position, value }
  })

  return (
    <div className="imperial-highlight-panel rounded-lg p-4">
      <p className="text-sm font-semibold text-foreground">{title}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{body}</p>
      <div className="mt-4 grid gap-2" aria-label={locale === "zh" ? "实时六爻预览" : "Live six-line preview"}>
        {lines.map(({ position, value }) => {
          const filled = [6, 7, 8, 9].includes(value)
          const moving = value === 6 || value === 9
          const type = value === 7 || value === 9 ? "yang" : "yin"
          return (
            <div
              key={position}
              className={cn(
                "grid min-h-9 grid-cols-[1fr_auto] items-center gap-3 rounded-md border px-2 py-1",
                filled ? "border-primary/30 bg-primary/10" : "border-border/40 bg-background/70",
              )}
            >
              <PreviewLineSvg type={type} filled={filled} moving={moving} />
              <span className={cn("w-8 text-center text-xs", moving ? "imperial-text font-semibold" : "text-muted-foreground")}>
                {filled ? value : position}
              </span>
            </div>
          )
        })}
      </div>
      <ol className="sr-only">
        {values.map((value, index) => (
          <li key={`${index}-${value}`}>
            {locale === "zh" ? `第${index + 1}爻：${value}` : `Line ${index + 1}: ${value}`}
          </li>
        ))}
      </ol>
    </div>
  )
}

function PreviewLineSvg({
  type,
  filled,
  moving,
}: {
  type: "yang" | "yin"
  filled: boolean
  moving: boolean
}) {
  const fillClass = !filled ? "fill-muted-foreground/30" : moving ? "imperial-fill" : "fill-foreground/85"
  return (
    <svg viewBox="0 0 120 18" className="h-5 w-full" role="presentation">
      {type === "yang" ? (
        <rect x="6" y="6" width="108" height="6" rx="2" className={fillClass} />
      ) : (
        <>
          <rect x="6" y="6" width="43" height="6" rx="2" className={fillClass} />
          <rect x="71" y="6" width="43" height="6" rx="2" className={fillClass} />
        </>
      )}
      {moving ? (
        <rect x="2" y="2" width="116" height="14" rx="4" className="imperial-stroke fill-transparent" strokeWidth="1" />
      ) : null}
    </svg>
  )
}
