"use client"

import { useEffect, useMemo, useRef } from "react"
import { CircleHelp } from "lucide-react"
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
import { useSessionMutation } from "@/lib/queries"
import { parseManualLines } from "@/lib/api"
import { useWorkspaceStore } from "@/lib/store"
import type { ConfigResponse, ModelInfo, SessionRequest } from "@/types/api"
import { toast } from "sonner"

type Props = {
  config: ConfigResponse
}

const pad = (value: number) => value.toString().padStart(2, "0")
const toneOptions = [
  { value: "normal", label: "标准", description: "沉稳专业、贴近现代书面语。" },
  { value: "wenyan", label: "文言（庄子风）", description: "仿先秦典籍的文言文语气。" },
  { value: "modern", label: "暧昧现代", description: "俏皮亲昵，可少量 emoji。" },
  { value: "academic", label: "学术期刊", description: "如 Nature / Harvard Law Review 式严谨论述。" },
]
const infoButtonClass =
  "flex size-8 items-center justify-center rounded-full border border-border/80 bg-background/60 text-foreground shadow-glass transition hover:bg-foreground/10 dark:border-white/30 dark:bg-white/10 dark:text-white"

const modelSpeedLines = [
  "GPT-4.1 nano · fastest response (~5s) for quick sanity checks.",
  "GPT-5 nano · ~15s baseline, balanced cost/performance.",
  "GPT-5 · premium chain-of-thought, starts around 40-45s.",
  "O3 · most capable, expect ≥60s even for short prompts.",
]
const modelQualityLine =
  "GPT-5 and O3 are most faithful—set reasoning ≥Medium and allow ~1 minute when accuracy matters."

function getReasoningLines(modelName?: string) {
  const name = modelName?.toLowerCase() ?? ""
  if (name.includes("gpt-5-nano")) {
    return [
      "Minimal ≈10s",
      "Low ≈30s",
      "Medium ≈90s",
      "High ≥2 min — reserve for deep dives.",
    ]
  }
  if (name.includes("gpt-5")) {
    return [
      "Minimal ≈45s",
      "Low ≈70s",
      "Medium/High ≥2 min; best accuracy when you can wait.",
    ]
  }
  if (name.includes("o3")) {
    return [
      "No Minimal tier.",
      "Low ≈1 min.",
      "Medium/High ≥2 min; launch only when you have ample time.",
    ]
  }
  return ["This model does not expose reasoning-depth controls."]
}

const verbosityLines = [
  "Higher output adds only ~5–10s to latency.",
  "Use when you need richer narrative, more citations, or export-ready text.",
]

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

export function CastForm({ config }: Props) {
  const defaultsHydrated = useRef(false)
  const form = useWorkspaceStore((state) => state.form)
  const updateForm = useWorkspaceStore((state) => state.updateForm)
  const setForm = useWorkspaceStore((state) => state.setForm)
  const setResult = useWorkspaceStore((state) => state.setResult)
  const activeToneOption = toneOptions.find((option) => option.value === form.aiTone)

  const activeModel = useMemo<ModelInfo | undefined>(
    () => config.ai_models.find((model) => model.name === form.aiModel),
    [config.ai_models, form.aiModel],
  )

  useEffect(() => {
    if (defaultsHydrated.current) return
    if (!config.topics.length || !config.methods.length) return

    const current = useWorkspaceStore.getState().form
    setForm({
      topic: current.topic || config.topics[0]?.label || "",
      methodKey: current.methodKey || config.methods[0]?.key || "",
      aiModel: current.aiModel || config.ai_models[0]?.name || "gpt-5-nano",
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
    onSuccess: (payload) => {
      setResult(payload)
      toast.success("起卦完成，结果已生成。")
    },
    onError: (error) => {
      const detail = error.message?.trim()
      const friendly =
        detail === "未知的占卜方法: "
          ? "请选择占卜方法后再起卦。"
          : detail || "请求失败，请稍后再试。"
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
        toast.error((error as Error).message)
        return
      }
    }

    let timestamp: string | null = null

    if (form.useCurrentTime) {
      timestamp = formatOffsetISOString(new Date())
    } else {
      if (!form.customTimestamp) {
        toast.error("请输入自定义时间。")
        return
      }
      const customDate = new Date(form.customTimestamp)
      if (Number.isNaN(customDate.getTime())) {
        toast.error("时间格式无效，请重新输入。")
        return
      }
      timestamp = formatOffsetISOString(customDate)
    }

    if (!timestamp) {
      toast.error("无法解析时间，请稍后再试。")
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

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="glass-panel space-y-6 rounded-3xl p-6">
        <div className="space-y-2">
          <p className="panel-heading">占卜主题</p>
          <Select value={form.topic} onValueChange={(value) => updateForm("topic", value)}>
            <SelectTrigger>
              <SelectValue placeholder="选择主题" />
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
          <p className="panel-heading">具体问题</p>
          <Textarea
            placeholder="例如：今年是否适合换工作？"
            value={form.userQuestion}
            onChange={(event) => updateForm("userQuestion", event.target.value)}
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <p className="panel-heading">占卜方法</p>
          <Select value={form.methodKey} onValueChange={(value) => updateForm("methodKey", value)}>
            <SelectTrigger>
              <SelectValue placeholder="选择方法" />
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
              <p className="panel-heading">手动输入六爻（自下而上）</p>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className={`${infoButtonClass} size-9`}
                  >
                    <CircleHelp className="size-5" aria-hidden="true" />
                    <span className="sr-only">六爻输入说明</span>
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs space-y-1 text-left leading-relaxed">
                  <p>6 · 老阴，例如三枚铜钱全为正面</p>
                  <p>7 · 少阳，例如两枚为正、一枚为反</p>
                  <p>8 · 少阴，例如两枚为反、一枚为正</p>
                  <p>9 · 老阳，例如三枚铜钱全为反面</p>
                </TooltipContent>
              </Tooltip>
            </div>
            <Input
              value={form.manualLines}
              onChange={(event) => updateForm("manualLines", event.target.value)}
              placeholder="898789 或 8,9,8,7,8,9"
            />
          </div>
        )}

        <div className="space-y-4 rounded-2xl border border-border/50 bg-foreground/[0.04] p-4 dark:border-white/15 dark:bg-white/5">
          <div className="panel-heading">时间设置</div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">使用当前时间</span>
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

      <div className="glass-panel space-y-4 rounded-3xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="panel-heading">AI 分析</p>
          </div>
          <Switch checked={form.enableAi} onCheckedChange={(checked) => updateForm("enableAi", checked)} />
        </div>

        {form.enableAi && (
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="panel-heading">访问密码</p>
              <Input
                type="password"
                value={form.accessPassword}
                onChange={(event) => updateForm("accessPassword", event.target.value)}
                placeholder="输入访问密码"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <p className="panel-heading">模型</p>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button type="button" className={`${infoButtonClass} size-9`}>
                      <CircleHelp className="size-5" aria-hidden="true" />
                      <span className="sr-only">Model speed info</span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-sm space-y-1 text-left leading-relaxed">
                    {modelSpeedLines.map((line) => (
                      <p key={line}>{line}</p>
                    ))}
                    <p className="pt-1 opacity-80">{modelQualityLine}</p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <Select value={form.aiModel} onValueChange={(value) => updateForm("aiModel", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择模型" />
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
                  <p className="panel-heading">推理力度</p>
                  <Tooltip>
                    <TooltipTrigger asChild>
                    <button type="button" className={`${infoButtonClass} size-9`}>
                      <CircleHelp className="size-5" aria-hidden="true" />
                        <span className="sr-only">Reasoning latency info</span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-sm space-y-1 text-left leading-relaxed">
                      {getReasoningLines(activeModel?.name).map((line) => (
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
                    <SelectValue placeholder="选择推理力度" />
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
                  <p className="panel-heading">输出篇幅</p>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button type="button" className={`${infoButtonClass} size-9`}>
                        <CircleHelp className="size-5" aria-hidden="true" />
                        <span className="sr-only">Verbosity info</span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs space-y-1 text-left leading-relaxed">
                      {verbosityLines.map((line) => (
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
                    <SelectValue placeholder="选择篇幅" />
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
              <p className="panel-heading">语气风格</p>
              <Select value={form.aiTone} onValueChange={(value) => updateForm("aiTone", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择语气" />
                </SelectTrigger>
                <SelectContent>
                  {toneOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {activeToneOption?.description ?? "请选择偏好的语气与写作声线。"}
              </p>
            </div>
          </div>
        )}
      </div>

      <Button
        type="submit"
        size="lg"
        disabled={mutation.isPending}
        className="h-12 w-full rounded-full text-base font-semibold"
      >
        {mutation.isPending ? "起卦中..." : "开始起卦"}
      </Button>
    </form>
  )
}
