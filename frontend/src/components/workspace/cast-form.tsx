"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react"
import { ArrowRight, CircleHelp, Settings2 } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
import { AutumnFrame } from "@/components/autumn/autumn-frame"
import { useAutumnMotion } from "@/components/autumn/autumn-motion"
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
import { parseManualLines, prepareCasting } from "@/lib/api"
import { YarrowRitual } from "./yarrow-ritual"
import { MeihuaCalculation } from "./meihua-calculation"
import { CastingMethodPicker, ManualLineEditor, MeihuaSteps } from "./casting-controls"
import { trackProductEvent } from "@/lib/analytics"
import { resolveReadingIntent } from "@/lib/reading-intents"
import { useWorkspaceStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import type { CastingPreview, ConfigResponse, ModelInfo, SessionRequest } from "@/types/api"
import { toast } from "sonner"

type Props = {
  config: ConfigResponse
}

const QUESTION_LIMIT = 2000
const MANUAL_METHOD_KEY = "x"
const COIN_METHOD_KEY = "c"
type ReadingPreset = "chart" | "standard" | "deep"

const pad = (value: number) => value.toString().padStart(2, "0")

const infoButtonClass =
  "inline-flex size-8 items-center justify-center rounded-full border border-border/70 bg-surface/70 text-foreground transition hover:bg-surface-elevated"

function subscribeToStoreHydration(onStoreChange: () => void) {
  const unsubscribeFromStart = useWorkspaceStore.persist.onHydrate(onStoreChange)
  const unsubscribeFromFinish = useWorkspaceStore.persist.onFinishHydration(onStoreChange)
  return () => {
    unsubscribeFromStart()
    unsubscribeFromFinish()
  }
}

function getStoreHydrationSnapshot() {
  return useWorkspaceStore.persist.hasHydrated()
}

function getServerHydrationSnapshot() {
  return false
}

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
      ? ["关闭：直接回答", "低 / 中：日常占断", "高 / 极高：复杂局势，通常耗时更长"]
      : ["None: direct response", "Low / Medium: everyday readings", "High / X-high: complex situations and usually slower"]
  }
  if (name.includes("gpt-5.3-codex")) {
    return locale === "zh"
      ? ["极简 / 低：快速结构化回答", "中 / 高：更完整的技术或流程推演"]
      : ["Minimal / Low: faster structured answers", "Medium / High: fuller technical or procedural reasoning"]
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
  if (prediction && !/^(what|how|which|where|when|why)\b/i.test(trimmed)) {
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
  const router = useRouter()
  const defaultsHydrated = useRef(false)
  const storeHydrated = useSyncExternalStore(
    subscribeToStoreHydration,
    getStoreHydrationSnapshot,
    getServerHydrationSnapshot,
  )
  const { paused } = useAutumnMotion()
  const [isTossing, setIsTossing] = useState(false)
  const [tossId, setTossId] = useState(0)
  const tossing = useRef(false)
  const tossTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const operation = useRef(0)
  const preparedCastRef = useRef<CastingPreview | null>(null)
  const [preparedCast, setPreparedCast] = useState<CastingPreview | null>(null)
  const meihuaStepRef = useRef(0)
  const [meihuaStep, setMeihuaStep] = useState(0)
  const [ritualPhase, setRitualPhase] = useState(0)
  const [remainingStalks, setRemainingStalks] = useState(49)
  const [yarrowPhase, setYarrowPhase] = useState(0)
  const [yarrowLine, setYarrowLine] = useState(0)
  useEffect(() => () => { operation.current++; if (tossTimer.current) clearTimeout(tossTimer.current) }, [])
  const [lastCoinToss, setLastCoinToss] = useState<number[] | null>(null)
  const form = useWorkspaceStore((state) => state.form)
  const updateForm = useWorkspaceStore((state) => state.updateForm)
  const setForm = useWorkspaceStore((state) => state.setForm)
  const setResult = useWorkspaceStore((state) => state.setResult)
  const activeToneOption = messages.workspace.tones.find((option) => option.value === form.aiTone)
  const questionLength = form.userQuestion?.length ?? 0
  const canUseAi = Boolean(auth.user)
  const questionCoaching = useMemo(() => analyzeQuestion(form.userQuestion, locale), [form.userQuestion, locale])
  const currentManualValues = form.methodKey === MANUAL_METHOD_KEY
    ? form.manualLines.replace(/[,\s]+/g, "").split("").slice(0, 6).map((value) => [6, 7, 8, 9].includes(Number(value)) ? Number(value) : 0)
    : manualLineValues(form.manualLines)
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
    if (!storeHydrated) return
    if (defaultsHydrated.current) return
    if (!config.topics.length || !config.methods.length) return

    const current = useWorkspaceStore.getState().form
    const preferredTopic =
      config.topics.find((topic) => topic.label === "事业")?.label || config.topics[0]?.label || ""
    const preferredMethod =
      config.methods.find((method) => method.label === "三枚铜钱法")?.key ||
      config.methods.find((method) => method.key === COIN_METHOD_KEY)?.key ||
      config.methods[0]?.key ||
      ""
    const searchParams = new URLSearchParams(window.location.search)
    const requestedIntent = resolveReadingIntent(searchParams.get("topic"), locale, config.topics)
    const persistedTopic = config.topics.some((topic) => topic.label === current.topic) ? current.topic : ""
    const explicitQuestion = searchParams.get("question")?.trim().slice(0, QUESTION_LIMIT) || ""
    const draftedQuestion = current.userQuestion?.trim() ? current.userQuestion : ""
    const requestedTimestamp = searchParams.get("timestamp")
    const requestedDate = requestedTimestamp ? new Date(requestedTimestamp) : null
    setForm({
      topic: requestedIntent?.topic || persistedTopic || preferredTopic,
      userQuestion: explicitQuestion || draftedQuestion || requestedIntent?.questionHint || "",
      methodKey: config.methods.some((method) => method.key === searchParams.get("method")) ? searchParams.get("method")! : current.methodKey || preferredMethod,
      aiModel: current.aiModel || config.default_model || config.ai_models[0]?.name || "",
      ...(requestedDate && !Number.isNaN(requestedDate.getTime())
        ? {
            useCurrentTime: false,
            customTimestamp: formatLocalDateTime(requestedDate),
            presetTimestamp: requestedTimestamp!,
            castingTimezone: searchParams.get("timezone") || undefined,
            meihuaMode: "traditional",
            manualLines: "", castingTimestamp: undefined,
          }
        : current.presetTimestamp
          ? { useCurrentTime: true, presetTimestamp: undefined, castingTimezone: undefined, castingTimestamp: undefined, manualLines: "" }
          : !current.manualLines
            ? { castingTimestamp: undefined }
            : {}),
    })
    defaultsHydrated.current = true
  }, [config, locale, setForm, storeHydrated])

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
	      router.push(toLocalePath("/reading"))
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
    if (tossing.current || mutation.isPending) return

    let manualLines: number[] | undefined
    try {
      manualLines = parseManualLines(form.manualLines)
    } catch (error) {
      const reason = (error as Error).message
      if (reason === "manual_lines_count_error") toast.error(messages.workspace.cast.manualLinesCountError)
      else if (reason === "manual_lines_value_error") toast.error(messages.workspace.cast.manualLinesValueError)
      else toast.error(messages.workspace.cast.requestFailed)
      return
    }

    let timestamp: string
    try {
      timestamp = castingTime()
    } catch (error) {
      toast.error((error as Error).message)
      return
    }

	    const payload: SessionRequest = {
      topic: form.topic,
      user_question: form.userQuestion || undefined,
      user_context: form.userContext || undefined,
      method_key: form.methodKey,
      meihua_mode: form.meihuaMode ?? "traditional",
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
  function castingTime() {
    const current = useWorkspaceStore.getState().form
    if (current.castingTimestamp) return current.castingTimestamp
    if (!current.useCurrentTime && current.presetTimestamp) return current.presetTimestamp
    const date = current.useCurrentTime ? new Date() : new Date(current.customTimestamp)
    if (Number.isNaN(date.getTime())) throw new Error(messages.workspace.cast.invalidTimestamp)
    return formatOffsetISOString(date)
  }
  function clearManualLines() {
    if (tossing.current || mutation.isPending) return
    operation.current++
    setLastCoinToss(null)
    preparedCastRef.current = null
    setPreparedCast(null)
    meihuaStepRef.current = 0
    setMeihuaStep(0)
    setRitualPhase(0)
    setYarrowPhase(0)
    setYarrowLine(0)
    setRemainingStalks(49)
    setForm({ manualLines: "", castingTimestamp: undefined })
  }
  function changeMethod(methodKey: string) {
    if (tossing.current || mutation.isPending || methodKey === form.methodKey) return
    clearManualLines()
    updateForm("methodKey", methodKey)
  }
  function changeCastingTime(values: { useCurrentTime?: boolean; customTimestamp?: string }) {
    if (tossing.current || mutation.isPending) return
    clearManualLines()
    setForm({ ...values, presetTimestamp: undefined, castingTimezone: undefined })
  }
  function editManualLine(index: number, value?: number) {
    if (tossing.current || mutation.isPending) return
    const raw = useWorkspaceStore.getState().form.manualLines
    const values = Array.from({ length: 6 }, (_, i) => Number(raw[i]) || 0)
    values[index] = value ?? (values[index] === 7 ? 8 : values[index] === 9 ? 6 : values[index] === 6 ? 9 : 7)
    updateForm("manualLines", values.join(""))
  }
  function tossCoinLine(allRemaining = false) {
    const current = useWorkspaceStore.getState().form
    if (tossing.current || mutation.isPending || current.methodKey !== COIN_METHOD_KEY || manualLineValues(current.manualLines).length >= 6) return
    try { setForm({ castingTimestamp: castingTime() }) } catch (error) { toast.error((error as Error).message); return }
    tossing.current = true
    setIsTossing(true)
    const result = coinLineValue()
    setLastCoinToss(result.coins)
    setTossId((value) => value + 1)
    tossTimer.current = setTimeout(() => {
      const values = manualLineValues(useWorkspaceStore.getState().form.manualLines)
      const next = [...values, result.value].slice(0, 6)
      setForm({ manualLines: next.join("") })
      tossing.current = false
      setIsTossing(false)
      if (allRemaining && next.length < 6) tossCoinLine(true)
    }, paused ? 40 : allRemaining && manualLineValues(current.manualLines).length < 5 ? 380 : 1280)
  }
  async function castRitual(allRemaining = false) {
    const current = useWorkspaceStore.getState().form
    const method = current.methodKey
    if (tossing.current || mutation.isPending || !["s", "m"].includes(method) || manualLineValues(current.manualLines).length >= 6) return
    tossing.current = true
    setIsTossing(true)
    const token = ++operation.current
    try {
      const timestamp = castingTime()
      const cast = preparedCastRef.current ?? await prepareCasting(method as "s" | "m", timestamp, current.meihuaMode ?? "traditional", current.castingTimezone)
      if (token !== operation.current) return
      preparedCastRef.current = cast
      setPreparedCast(cast)
      setForm({ castingTimestamp: cast.timestamp })
      setTossId((value) => value + 1)
      const finish = (continueCasting: boolean) => {
        tossing.current = false
        setIsTossing(false)
        if (allRemaining && continueCasting) void castRitual(true)
      }
      if (method === "s") {
        const index = manualLineValues(current.manualLines).length
        const trace = cast.yarrow_trace[index]
        setYarrowLine(index)
        setRemainingStalks(49)
        const change = (tick: number) => {
          if (token !== operation.current) return
          const changeIndex = Math.floor(tick / 4)
          const phase = tick % 4
          setRitualPhase(changeIndex + 1)
          setYarrowPhase(phase)
          setRemainingStalks(phase === 3 ? trace[changeIndex].after : trace[changeIndex].before - (phase >= 1 ? 1 : 0))
          tossTimer.current = setTimeout(() => {
            if (tick < 11) change(tick + 1)
            else {
              const values = [...manualLineValues(useWorkspaceStore.getState().form.manualLines), cast.lines[index]]
              updateForm("manualLines", values.join(""))
              finish(values.length < 6)
            }
          }, paused ? 15 : allRemaining ? 90 : 650)
        }
        change(0)
      } else {
        const next = meihuaStepRef.current + 1
        setRitualPhase(next)
        tossTimer.current = setTimeout(() => {
          if (token !== operation.current) return
          meihuaStepRef.current = next
          setMeihuaStep(next)
          if (next === 3) updateForm("manualLines", cast.lines.join(""))
          finish(next < 3)
        }, paused ? 40 : allRemaining && next < 3 ? 420 : 1000)
      }
    } catch (error) {
      if (token !== operation.current) return
      tossing.current = false
      setIsTossing(false)
      toast.error((error as Error).message || messages.workspace.cast.requestFailed)
    }
  }
  const copy =
    locale === "zh"
      ? {
          contextLabel: "相关背景",
          contextPlaceholder: "例如：对方已经催了两次，但预算、负责人、时间表还没完全确定。",
          chartTitle: "仅排盘",
          chartBody: "生成卦盘、纳甲与经典依据，不调用 AI。",
          standardTitle: "标准解读",
          standardBody: "默认使用 GPT-5.6 Terra，兼顾质量与速度。",
          deepTitle: "深度解读",
          deepBody: "使用 GPT-5.6 Sol 深入判断复杂问题。",
          advanced: "时间与原始输入",
          advancedDescription: "调整起卦时间与原始六爻输入。",
          questionApply: "采用建议问题",
          aiSettingsTitle: "AI 解读设置",
          aiSettingsBody: "按需要调整模型、推理力度、输出篇幅与语气。",
        }
      : {
          contextLabel: "Relevant context",
          contextPlaceholder: "Example: They are pushing for a fast answer, but budget, owner, and timeline are still unclear.",
          chartTitle: "Chart only",
          chartBody: "Generate the chart, Najia, and classical basis without AI.",
          standardTitle: "Standard",
          standardBody: "Use GPT-5.6 Terra for balanced quality and speed.",
          deepTitle: "Deep",
          deepBody: "Use GPT-5.6 Sol for difficult divination questions.",
          advanced: "Time and raw input",
          advancedDescription: "Adjust the cast time and raw six-line input.",
          questionApply: "Use suggested question",
          aiSettingsTitle: "AI reading settings",
          aiSettingsBody: "Adjust the model, reasoning, response length, and tone when needed.",
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
  const activeReadingMode = readingModes.find((mode) => mode.active) ?? readingModes[0]

  const showAiControls = selectedPreset === "deep" || form.enableAi
  const activeMethodDescription =
    form.methodKey === COIN_METHOD_KEY
      ? messages.workspace.cast.methodCoinDescription
      : form.methodKey === "s"
        ? messages.workspace.cast.methodYarrowDescription
        : form.methodKey === "m"
          ? messages.workspace.cast.methodMeihuaDescription
          : form.methodKey === MANUAL_METHOD_KEY
            ? messages.workspace.cast.methodManualDescription
            : messages.workspace.cast.methodUnknownDescription

  const isCoinMethod = form.methodKey === COIN_METHOD_KEY
  const isYarrowMethod = form.methodKey === "s"
  const isMeihuaMethod = form.methodKey === "m"
  const isManualMethod = form.methodKey === MANUAL_METHOD_KEY
  const lineCount = currentManualValues.filter((value) => value >= 6 && value <= 9).length
  const complete = lineCount === 6
  const methodName = locale === "zh" ? config.methods.find((method) => method.key === form.methodKey)?.label : ({ c: "Three coins", s: "Yarrow stalks", m: "Plum blossom", x: "Your own cast" }[form.methodKey] ?? form.methodKey)
  const displayValues = isMeihuaMethod && preparedCast && !complete && meihuaStep > 0
    ? preparedCast.lines.map((value, index) => meihuaStep === 1 && index < 3 ? 0 : value === 6 ? 8 : value === 9 ? 7 : value)
    : currentManualValues
  const visibleMeihuaStep = complete ? 3 : meihuaStep
  const trigramIndex = (lines: number[]) => ["111", "011", "101", "001", "110", "010", "100", "000"].indexOf([...lines].reverse().map((line) => line % 2).join("")) + 1
  const upperTrigram = preparedCast?.upper_trigram ?? (complete ? trigramIndex(currentManualValues.slice(3)) : null)
  const lowerTrigram = preparedCast?.lower_trigram ?? (complete ? trigramIndex(currentManualValues.slice(0, 3)) : null)
  const changingLine = preparedCast?.changing_line ?? (complete ? currentManualValues.findIndex((value) => value === 6 || value === 9) + 1 : null)
  const actionLabel = isCoinMethod
    ? (locale === "zh" ? `掷第 ${lineCount + 1} 爻` : `Cast line ${lineCount + 1}`)
    : isYarrowMethod
      ? (locale === "zh" ? `揲蓍 · 起第 ${lineCount + 1} 爻` : `Gather stalks · line ${lineCount + 1}`)
      : (locale === "zh" ? ["取上卦", "取下卦", "定动爻"][meihuaStep] : ["Reveal the upper trigram", "Reveal the lower trigram", "Reveal the changing line"][meihuaStep])
  const ritualStatus = isYarrowMethod
    ? (locale === "zh" ? `${["蓍草待分", "第一变", "第二变", "第三变"][ritualPhase]} · ${remainingStalks} 策` : `${ritualPhase ? `Change ${ritualPhase}` : "Stalks gathered"} · ${remainingStalks} stalks`)
    : isMeihuaMethod
      ? (locale === "zh" ? ["以时取象", "上卦初现", "上下成象", "动爻已定"][visibleMeihuaStep] : ["A moment becomes a sign", "Upper trigram revealed", "Two trigrams, one figure", "The changing line is set"][visibleMeihuaStep])
      : ""

  return (
    <form onSubmit={handleSubmit} className="autumn-cast-form">
      <AutumnFrame className="autumn-casting" values={displayValues} coins={lastCoinToss} toss={tossId} showCoins={isCoinMethod} sceneContent={isYarrowMethod ? <YarrowRitual locale={locale} change={preparedCast?.yarrow_trace[yarrowLine]?.[ritualPhase - 1] ?? null} phase={yarrowPhase} changeNumber={ritualPhase} values={currentManualValues} remaining={remainingStalks} /> : undefined} showCompass={isMeihuaMethod} ritualPhase={isMeihuaMethod ? Math.max(ritualPhase, visibleMeihuaStep) : ritualPhase} upperTrigram={upperTrigram} lowerTrigram={lowerTrigram} onToss={isCoinMethod && !complete ? () => tossCoinLine() : undefined} onLineSelect={isManualMethod ? (position) => editManualLine(position - 1) : undefined} caption={complete ? (locale === "zh" ? "六爻已成 · 静观其变" : "Six lines complete · a moment to reflect") : null} sceneOverlay={ritualStatus && !isYarrowMethod ? <div className="autumn-ritual-status"><span>{methodName}</span><strong role="status" aria-live="polite">{ritualStatus}</strong></div> : undefined}>
        <fieldset disabled={mutation.isPending || isTossing} className="min-w-0">
          <div className="autumn-question-copy">
          <h1 className="autumn-title" lang="zh">一念之间</h1>
          <p className="autumn-eyebrow">{locale === "zh" ? "以一念，观万象" : "A moment of change"}</p>

          <label htmlFor="reading-question" className="autumn-question-label">{locale === "zh" ? "此刻，你想理解什么？" : "What would you like to understand?"}</label>
          <textarea id="reading-question" className="autumn-textarea" value={form.userQuestion} onChange={(event) => updateForm("userQuestion", event.target.value)} maxLength={QUESTION_LIMIT} rows={4} placeholder={locale === "zh" ? "我该如何理解眼前的变化……" : "What should I understand about this change…"} />
          <span className="sr-only">{questionLength}/{QUESTION_LIMIT}</span>
          <details className="autumn-context">
            <summary>{locale === "zh" ? "补充一点背景" : "Add a little context"}</summary>
            <Textarea id="reading-context" aria-label={copy.contextLabel} value={form.userContext} onChange={(event) => updateForm("userContext", event.target.value)} rows={3} maxLength={1200} placeholder={copy.contextPlaceholder} className="mt-3" />
          </details>
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


          <p className="sr-only">{activeMethodDescription}</p>
          <CastingMethodPicker locale={locale} value={form.methodKey} available={config.methods.map((method) => method.key)} onChange={changeMethod} />
          <a href="#casting-scene" className="autumn-mobile-cast-jump">{isCoinMethod ? (locale === "zh" ? "准备好，让铜钱落下" : "Ready? Bring your question to the coins") : (locale === "zh" ? "继续起卦" : "Continue to the hexagram")}<ArrowRight size={14} aria-hidden="true" /></a>
          </div>
          <div className="autumn-cast-controls">
          {isManualMethod && <ManualLineEditor locale={locale} values={currentManualValues} raw={form.manualLines} onLineChange={editManualLine} onRawChange={(value) => updateForm("manualLines", value)} />}
          {isMeihuaMethod && <div className="meihua-method-choice">
            <label htmlFor="meihua-mode">{locale === "zh" ? "时间起卦法" : "Time calculation"}</label>
            <select id="meihua-mode" value={form.meihuaMode ?? "traditional"} onChange={(event) => { clearManualLines(); updateForm("meihuaMode", event.target.value as "traditional" | "original") }}>
              <option value="traditional">{locale === "zh" ? "传统农历时辰法" : "Traditional lunar / hour branch"}</option>
              <option value="original">{locale === "zh" ? "项目原始分钟法" : "Original project / minute formula"}</option>
            </select>
            <p>{locale === "zh" ? ((form.meihuaMode ?? "traditional") === "traditional" ? "取年支、农历月日与时支；同日同一时辰，所得卦相同。" : "恢复最早版本的公历取数公式；同一分钟所得卦相同。") : ((form.meihuaMode ?? "traditional") === "traditional" ? "Year branch, lunar date and hour branch. The same date and hour branch produce the same cast." : "The project's original Gregorian formula. The same minute produces the same cast.")}</p>
            <label htmlFor="meihua-current-time" className="flex items-center justify-between gap-3">
              <span>{messages.workspace.cast.useCurrentTime}</span>
              <Switch id="meihua-current-time" checked={form.useCurrentTime} onCheckedChange={(checked) => changeCastingTime({ useCurrentTime: checked, ...(!checked ? { customTimestamp: formatLocalDateTime(new Date()) } : {}) })} />
            </label>
            {!form.useCurrentTime && <>
              <label htmlFor="meihua-custom-time">{locale === "zh" ? "自定时间（本机时区）" : "Custom time (device timezone)"}</label>
              <Input id="meihua-custom-time" type="datetime-local" value={form.customTimestamp} onChange={(event) => changeCastingTime({ customTimestamp: event.target.value })} />
            </>}
            <p className="meihua-clock">{locale === "zh" ? (form.castingTimestamp ? "本卦已锁定时间：" : form.useCurrentTime ? "时间来源：本机当前时间 · " : "时间来源：自定时间 · ") : (form.castingTimestamp ? "Locked cast time: " : form.useCurrentTime ? "Time source: device clock · " : "Time source: custom · ")}{form.castingTimestamp || (!form.useCurrentTime ? form.presetTimestamp || form.customTimestamp : (locale === "zh" ? "点击取上卦时锁定" : "Set when you reveal the upper trigram"))}{form.castingTimezone ? ` · ${form.castingTimezone}` : ""}</p>
          </div>}
          {isMeihuaMethod && <><MeihuaSteps locale={locale} step={visibleMeihuaStep} upper={upperTrigram} lower={lowerTrigram} moving={changingLine} /><ol className="sr-only" aria-label={locale === "zh" ? "卦象六爻，自下而上" : "Hexagram lines, bottom to top"}>{displayValues.map((value, index) => <li key={index}>{index + 1}: {value || "—"}</li>)}</ol></>}
          {isMeihuaMethod && preparedCast && <MeihuaCalculation cast={preparedCast} locale={locale} />}
          {!isManualMethod && !complete
            ? <button type="button" className="autumn-primary" disabled={isTossing} onClick={() => isCoinMethod ? tossCoinLine() : void castRitual()}>{isTossing ? (locale === "zh" ? "静待成象…" : "Let the figure take shape…") : actionLabel}<ArrowRight size={15} aria-hidden="true" /></button>
            : <button type="submit" className="autumn-primary" disabled={!complete || mutation.isPending}>{mutation.isPending ? messages.workspace.cast.submitLoading : (locale === "zh" ? "解读此卦" : "Read this hexagram")}<ArrowRight size={15} aria-hidden="true" /></button>}
          <div className="autumn-actions-row">
            {!isManualMethod && !complete ? <button type="button" className="autumn-link" onClick={() => isCoinMethod ? tossCoinLine(true) : void castRitual(true)}>{locale === "zh" ? "快速完成余下步骤" : "Complete the remaining steps"}</button> : <span className="autumn-link">{activeReadingMode.title}</span>}
            {(lineCount > 0 || meihuaStep > 0) && <button type="button" className="autumn-link" onClick={clearManualLines}>{locale === "zh" ? "重新起卦" : "Start over"}</button>}
          </div>
          {!isMeihuaMethod && !isManualMethod && <div className="autumn-cast-progress">
            <div className="flex items-center justify-between text-[11px] text-muted-foreground"><span>{locale === "zh" ? "自下而上，一爻一念" : "From the bottom, one line at a time"}</span><span role="status" aria-live="polite">{lineCount} / 6</span></div>
            <ol className="autumn-line-values" aria-label={locale === "zh" ? "六爻，自下而上" : "Six lines, from bottom to top"}>{Array.from({ length: 6 }, (_, index) => <li key={index} data-moving={currentManualValues[index] === 6 || currentManualValues[index] === 9} aria-label={`${locale === "zh" ? "爻" : "Line"} ${index + 1}: ${currentManualValues[index] || (locale === "zh" ? "未起" : "uncast")}`}>{currentManualValues[index] || "·"}</li>)}</ol>
            <p className="autumn-footnote">{isCoinMethod && lastCoinToss ? `${lastCoinToss.join(" + ")} = ${lastCoinToss.reduce((sum, value) => sum + value, 0)} · ` : ""}{locale === "zh" ? "金色为动爻，示其变化。" : "Gold marks a changing line."}</p>
          </div>}
          <div className="autumn-method-row">
            <span className="autumn-link">{methodName} · {activeReadingMode.title}</span>
            <Sheet>
              <SheetTrigger asChild><button type="button" className="autumn-link inline-flex items-center gap-1.5"><Settings2 size={15} aria-hidden="true" />{locale === "zh" ? "解读设置" : "Reading settings"}</button></SheetTrigger>
              <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
                <SheetHeader><SheetTitle>{locale === "zh" ? "解读设置" : "Reading settings"}</SheetTitle><SheetDescription>{locale === "zh" ? "选择主题，调整解读深度。" : "Choose a topic and how deeply you would like to explore."}</SheetDescription></SheetHeader>
                <div className="mt-6 space-y-6">
                  <div className="space-y-2"><label id="reading-topic-label" className="text-sm font-medium">{messages.workspace.cast.topicLabel}</label>
                <Select
                  value={form.topic}
                  onValueChange={(value) => {
                    if (!value || !config.topics.some((topic) => topic.label === value)) return
                    updateForm("topic", value)
                  }}
                >
                  <SelectTrigger aria-labelledby="reading-topic-label" className="h-11 w-full rounded-md bg-surface-elevated px-3 text-base">
                    <SelectValue placeholder={messages.workspace.cast.topicLabel} />
                  </SelectTrigger>
                  <SelectContent>
                    {config.topics.map((topic) => (
                      <SelectItem value={topic.label} key={topic.key}>
                        {locale === "zh" ? topic.label : ({ "事业": "Career", "感情": "Relationships", "财运": "Finances", "身体健康": "Wellbeing", "整体运势": "The present moment", "其他/跳过": "Something else" }[topic.label] ?? topic.label)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                  </div>
        <aside data-cast-step="interpret" className="space-y-4 border-t border-border/60 pt-6">
            <div className="space-y-3">
              <p className="text-sm font-semibold text-foreground">{locale === "zh" ? "解读方式" : "Interpretation"}</p>
              <div className="grid gap-2 sm:grid-cols-3">
                {readingModes.map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={mode.apply}
                    className={cn(
                      "min-h-11 rounded-md border px-3 py-2 text-center transition",
                      mode.active
                        ? "border-primary/60 bg-primary/10 text-foreground"
                        : "border-border/60 bg-surface/70 hover:border-primary/40",
                    )}
                    aria-pressed={mode.active}
                  >
                    <span className="text-sm font-semibold">{mode.title}</span>
                  </button>
                ))}
              </div>
              <p className="text-xs leading-5 text-muted-foreground">{activeReadingMode.body}</p>
            </div>

            {showAiControls && (
            <div className="imperial-highlight-panel rounded-lg border p-4">
              <div>
                <div>
                  <p className="text-sm font-semibold text-foreground">{copy.aiSettingsTitle}</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {copy.aiSettingsBody}
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
              </div>

              {form.enableAi && (
                <div className="mt-4 space-y-4">
                  <div className="grid gap-2 sm:grid-cols-[12rem_minmax(0,1fr)] sm:items-center">
                    <p className="text-sm font-medium text-foreground">{messages.workspace.cast.accessPasswordLabel}</p>
                    <Input
                      type="password"
                      value={form.accessPassword}
                      onChange={(event) => updateForm("accessPassword", event.target.value)}
                      placeholder={messages.workspace.cast.accessPasswordPlaceholder}
                    />
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
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
                  </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {activeToneOption?.description ?? messages.workspace.cast.toneDescriptionDefault}
                  </p>
                </div>
              )}
            </div>
            )}
          </aside>
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

                {!isMeihuaMethod && <div className="surface-soft space-y-3 rounded-lg p-4">
                  <p className="text-sm font-medium text-foreground">{messages.workspace.cast.timeLabel}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{messages.workspace.cast.useCurrentTime}</span>
                    <Switch
                      checked={form.useCurrentTime}
                      disabled={isTossing || mutation.isPending}
                      onCheckedChange={(checked) => changeCastingTime({ useCurrentTime: checked })}
                    />
                  </div>
                  <Input
                    type="datetime-local"
                    value={form.customTimestamp}
                    disabled={form.useCurrentTime || isTossing || mutation.isPending}
                    onChange={(event) => changeCastingTime({ customTimestamp: event.target.value })}
                  />
                </div>}
              </div>
            </SheetContent>
          </Sheet>
                </div>
              </SheetContent>
            </Sheet>
          </div>
          </div>
        </fieldset>
      </AutumnFrame>
    </form>
  )
}
