"use client"

import { useEffect, useMemo } from "react"
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
import { useSessionMutation } from "@/lib/queries"
import { parseManualLines } from "@/lib/api"
import { useWorkspaceStore } from "@/lib/store"
import type { ConfigResponse, ModelInfo, SessionRequest } from "@/types/api"
import { toast } from "sonner"

type Props = {
  config: ConfigResponse
}

export function CastForm({ config }: Props) {
  const { form, updateForm, setForm, setResult } = useWorkspaceStore((state) => ({
    form: state.form,
    updateForm: state.updateForm,
    setForm: state.setForm,
    setResult: state.setResult,
  }))

  const activeModel = useMemo<ModelInfo | undefined>(
    () => config.ai_models.find((model) => model.name === form.aiModel),
    [config.ai_models, form.aiModel],
  )

  useEffect(() => {
    if (!config.topics.length || !config.methods.length) return

    setForm({
      topic: form.topic || config.topics[0].label,
      methodKey: form.methodKey || config.methods[0].key,
      aiModel: form.aiModel || config.ai_models[0]?.name || "gpt-5-nano",
    })
  }, [config, form.aiModel, form.methodKey, form.topic, setForm])

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
      toast.error(error.message || "请求失败")
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

    const payload: SessionRequest = {
      topic: form.topic,
      user_question: form.userQuestion || undefined,
      method_key: form.methodKey,
      manual_lines: manualLines,
      use_current_time: form.useCurrentTime,
      timestamp: form.useCurrentTime ? null : form.customTimestamp || null,
      enable_ai: form.enableAi,
      access_password: form.enableAi ? form.accessPassword || null : null,
      ai_model: form.aiModel,
      ai_reasoning: form.aiReasoning || null,
      ai_verbosity: form.aiVerbosity || null,
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
            <p className="panel-heading">手动输入六爻（自下而上）</p>
            <Input
              value={form.manualLines}
              onChange={(event) => updateForm("manualLines", event.target.value)}
              placeholder="898789 或 8,9,8,7,8,9"
            />
          </div>
        )}

        <div className="space-y-4 rounded-2xl border border-white/15 bg-white/5 p-4">
          <div className="panel-heading">时间设置</div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-white/80">使用当前时间</span>
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
            <p className="text-sm text-white/75">需要在 Render 设置访问密码（OPENAI_PW）。</p>
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
              <p className="panel-heading">模型</p>
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
                <p className="panel-heading">推理力度</p>
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
                <p className="panel-heading">输出篇幅</p>
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
