"use client"

import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useWorkspaceStore } from "@/lib/store"
import type { HexSection, SessionPayload } from "@/types/api"

import { HexagramHeader } from "./hexagram-visual"
import { NajiaTableView } from "./najia-table"

export function ResultsPanel() {
  const result = useWorkspaceStore((state) => state.result)

  if (!result) {
    return (
      <Card className="glass-panel border-transparent text-foreground">
        <CardHeader>
          <CardTitle className="text-lg">等待首次起卦</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          在左侧填写主题、问题与时间，点击「开始起卦」即可在此处查看概要、卦辞、纳甲与 AI 分析。
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="glass-panel border-transparent text-foreground">
      <CardHeader>
        <CardTitle className="text-lg">会话结果</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="summary">
          <TabsList className="grid w-full grid-cols-3 rounded-full bg-foreground/10 text-foreground dark:bg-white/10 dark:text-white">
            <TabsTrigger value="summary">概要</TabsTrigger>
            <TabsTrigger value="hex">卦辞纳甲</TabsTrigger>
            <TabsTrigger value="ai">AI</TabsTrigger>
          </TabsList>
          <TabsContent value="summary">
            <ResultBlock text={result.summary_text} label="概要" />
          </TabsContent>
          <TabsContent value="hex">
            <HexResultBlock result={result} />
          </TabsContent>
          <TabsContent value="ai">
            <ResultBlock text={result.ai_text || "AI 未启用"} label="AI 分析" />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

function HexResultBlock({ result }: { result: SessionPayload }) {
  const [showFull, setShowFull] = useState(false)
  const sections = result.hex_sections || []

  const { primarySections, secondarySections } = useMemo(() => {
    const primary = sections.filter((section) => section.visible_by_default)
    const secondary = sections.filter((section) => !section.visible_by_default)
    return { primarySections: primary, secondarySections: secondary }
  }, [sections])

  const hasHiddenSections = secondarySections.length > 0
  const hasPrimary = primarySections.length > 0

  return (
    <div className="mt-4 space-y-5">
      <HexagramHeader overview={result.hex_overview} najiaMeta={result.najia_table?.meta} />
      {result.najia_table?.rows?.length ? (
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">六神纳甲</p>
          <NajiaTableView table={result.najia_table} />
        </div>
      ) : null}
      <div className="rounded-2xl border border-border/40 bg-foreground/[0.04] p-4 text-sm leading-relaxed text-foreground dark:border-white/10 dark:bg-white/5">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">卦辞解析</p>
          {hasHiddenSections && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs font-semibold tracking-wide text-foreground hover:text-foreground"
              onClick={() => setShowFull((value) => !value)}
              aria-expanded={showFull}
            >
              {showFull ? "隐藏补充" : "显示补充"}
            </Button>
          )}
        </div>
        {hasPrimary ? (
          <HexSectionGroup title="重点段落" sections={primarySections} variant="primary" />
        ) : (
          <pre className="whitespace-pre-wrap font-sans text-sm">{result.hex_text}</pre>
        )}
        {showFull && hasHiddenSections && (
          <div className="mt-6">
            <HexSectionGroup title="补充段落" sections={secondarySections} variant="secondary" />
          </div>
        )}
      </div>
    </div>
  )
}

function ResultBlock({ text, label }: { text: string; label: string }) {
  return (
    <div className="mt-4 rounded-2xl border border-border/40 bg-foreground/[0.04] p-4 text-sm leading-relaxed text-foreground dark:border-white/10 dark:bg-white/5">
      <p className="mb-2 text-xs uppercase tracking-[0.35rem] text-muted-foreground">{label}</p>
      <pre className="whitespace-pre-wrap font-sans text-sm">{text}</pre>
    </div>
  )
}

function HexSectionGroup({
  title,
  sections,
  variant,
}: {
  title: string
  sections: HexSection[]
  variant: "primary" | "secondary"
}) {
  if (!sections.length) {
    return null
  }

  const accentClasses =
    variant === "primary"
      ? "border-amber-400/50 bg-amber-300/10 dark:border-amber-200/30 dark:bg-amber-200/5"
      : "border-border/60 bg-foreground/5 dark:border-white/10 dark:bg-white/5"

  return (
    <div className={`rounded-2xl border ${accentClasses} p-4`}>
      <p className="mb-3 text-xs uppercase tracking-[0.35rem] text-muted-foreground">{title}</p>
      <div className="space-y-3">
        {sections.map((section) => (
          <div
            key={section.id}
            className="rounded-xl border border-border/40 bg-background/70 p-3 text-foreground shadow-sm dark:border-white/10 dark:bg-white/5"
          >
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-muted-foreground">
              <span>{section.title}</span>
              <span className="text-[0.65rem] uppercase tracking-widest">
                {section.hexagram_name} · {section.hexagram_type === "main" ? "本卦" : "变卦"}
              </span>
            </div>
            <div className="mt-1 text-[0.65rem] uppercase tracking-widest text-muted-foreground/80">
              {section.importance === "primary" ? "默认重点" : "扩展参考"}
            </div>
            <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">{section.content}</pre>
          </div>
        ))}
      </div>
    </div>
  )
}
