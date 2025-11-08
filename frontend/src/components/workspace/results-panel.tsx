"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useWorkspaceStore } from "@/lib/store"

export function ResultsPanel() {
  const result = useWorkspaceStore((state) => state.result)

  if (!result) {
    return (
      <Card className="glass-panel border-transparent bg-white/5 text-white">
        <CardHeader>
          <CardTitle className="text-lg">等待首次起卦</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-white/80">
          在左侧填写主题、问题与时间，点击「开始起卦」即可在此处查看概要、卦辞、纳甲与 AI 分析。
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="glass-panel border-transparent bg-white/5 text-white">
      <CardHeader>
        <CardTitle className="text-lg">会话结果</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="summary">
          <TabsList className="grid w-full grid-cols-4 rounded-full bg-white/10 text-white">
            <TabsTrigger value="summary">概要</TabsTrigger>
            <TabsTrigger value="hex">卦辞</TabsTrigger>
            <TabsTrigger value="najia">纳甲</TabsTrigger>
            <TabsTrigger value="ai">AI</TabsTrigger>
          </TabsList>
          <TabsContent value="summary">
            <ResultBlock text={result.summary_text} label="概要" />
          </TabsContent>
          <TabsContent value="hex">
            <ResultBlock text={result.hex_text} label="卦辞" />
          </TabsContent>
          <TabsContent value="najia">
            <ResultBlock text={result.najia_text} label="纳甲" />
          </TabsContent>
          <TabsContent value="ai">
            <ResultBlock text={result.ai_text || "AI 未启用"} label="AI 分析" />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

function ResultBlock({ text, label }: { text: string; label: string }) {
  return (
    <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4 text-sm leading-relaxed text-white/90">
      <p className="mb-2 text-xs uppercase tracking-[0.35rem] text-white/60">{label}</p>
      <pre className="whitespace-pre-wrap font-sans text-sm">{text}</pre>
    </div>
  )
}
