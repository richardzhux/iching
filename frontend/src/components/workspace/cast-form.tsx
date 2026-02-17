"use client"

import Link from "next/link"
import { useEffect, useMemo, useRef } from "react"
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
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useAuthContext } from "@/components/providers/auth-provider"
import { useSessionMutation } from "@/lib/queries"
import { parseManualLines } from "@/lib/api"
import { useWorkspaceStore } from "@/lib/store"
import type { ConfigResponse, ModelInfo, SessionRequest } from "@/types/api"
import { toast } from "sonner"

type Props = {
  config: ConfigResponse
}

const QUESTION_LIMIT = 2000

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
  if (name.includes("gpt-5.2")) {
    return locale === "zh"
      ? ["关闭 ≈30s", "极简 ≈40s", "低 ≈50s", "中 ≈65s", "高 ≥90s"]
      : ["None ≈30s", "Minimal ≈40s", "Low ≈50s", "Medium ≈65s", "High ≥90s"]
  }
  if (name.includes("gpt-5-mini")) {
    return locale === "zh"
      ? ["极简 ≈15s", "低 ≈20s", "中 ≈30s", "高 ≥60s"]
      : ["Minimal ≈15s", "Low ≈20s", "Medium ≈30s", "High ≥60s"]
  }
  return locale === "zh"
    ? ["该模型不支持推理力度控制。"]
    : ["This model does not expose reasoning-depth controls."]
}

export function CastForm({ config }: Props) {
  const auth = useAuthContext()
  const { messages, locale, toLocalePath } = useI18n()
  const defaultsHydrated = useRef(false)
  const form = useWorkspaceStore((state) => state.form)
  const updateForm = useWorkspaceStore((state) => state.updateForm)
  const setForm = useWorkspaceStore((state) => state.setForm)
  const setResult = useWorkspaceStore((state) => state.setResult)
  const activeToneOption = messages.workspace.tones.find((option) => option.value === form.aiTone)
  const questionLength = form.userQuestion?.length ?? 0
  const canUseAi = Boolean(auth.user)

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
      aiModel: current.aiModel || config.ai_models[0]?.name || "gpt-5.2",
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
      if (form.methodKey === "x") {
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

    mutation.mutate(payload)
  }

  const reasoningLines = getReasoningLines(activeModel?.name, locale)

  return (
    <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
      <section className="surface-card space-y-5 rounded-3xl p-6 sm:p-7">
        <p className="kicker">{messages.workspace.cast.topicSection}</p>

        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">{messages.workspace.cast.topicLabel}</p>
          <Select value={form.topic} onValueChange={(value) => updateForm("topic", value)}>
            <SelectTrigger>
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

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">{messages.workspace.cast.questionLabel}</p>
            <span className="text-xs text-muted-foreground">
              {questionLength}/{QUESTION_LIMIT}
            </span>
          </div>
          <Textarea
            placeholder={messages.workspace.cast.questionPlaceholder}
            value={form.userQuestion}
            onChange={(event) => updateForm("userQuestion", event.target.value)}
            rows={4}
            maxLength={QUESTION_LIMIT}
          />
        </div>

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

        {form.methodKey === "x" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-foreground">{messages.workspace.cast.manualLinesLabel}</p>
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
              value={form.manualLines}
              onChange={(event) => updateForm("manualLines", event.target.value)}
              placeholder={messages.workspace.cast.manualLinesPlaceholder}
            />
          </div>
        )}

        <div className="surface-soft space-y-3 rounded-2xl p-4">
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
      </section>

      <section className="surface-card space-y-5 rounded-3xl p-6 sm:p-7">
        <p className="kicker">{messages.workspace.cast.aiSection}</p>

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

        <Button
          type="submit"
          size="lg"
          disabled={mutation.isPending}
          className="mt-2 h-11 w-full rounded-2xl text-sm font-semibold"
        >
          {mutation.isPending ? messages.workspace.cast.submitLoading : messages.workspace.cast.submitIdle}
        </Button>
      </section>
    </form>
  )
}
