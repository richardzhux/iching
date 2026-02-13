"use client"

import { useMemo, useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MarkdownContent } from "@/components/ui/markdown-content"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { useWorkspaceStore } from "@/lib/store"

export function HistoryDrawer() {
  const history = useWorkspaceStore((state) => state.history)
  const [expanded, setExpanded] = useState<string | null>(null)
  const formattedHistory = useMemo(() => history ?? [], [history])

  function toggleEntry(id: string) {
    setExpanded((current) => (current === id ? null : id))
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" className="w-full rounded-full border-white/30 bg-white/10 text-foreground backdrop-blur hover:bg-white/20 dark:text-white">
          查看会话历史 ({history.length})
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>最近 10 次起卦</SheetTitle>
          <SheetDescription>
            仅保留当前浏览器内存，刷新后将清空。登录后可前往个人中心查看完整历史。
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          {formattedHistory.length === 0 && <p className="text-sm text-muted-foreground">暂无历史记录。</p>}
          {formattedHistory.map((item, index) => {
            const key = `${item.session_id}-${index}`
            const isOpen = expanded === key
            const topic = (item.session_dict?.["topic"] as string) || "（未填写主题）"
            const method = (item.session_dict?.["method"] as string) || "未知方法"
            const timestamp = (item.session_dict?.["current_time_str"] as string) || "未知时间"
            return (
              <div
                key={key}
                className="rounded-2xl border border-border/70 bg-card/70 p-4 text-sm shadow-glass"
              >
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 text-left"
                  onClick={() => toggleEntry(key)}
                >
                  <div>
                    <p className="text-xs uppercase tracking-[0.3rem] text-muted-foreground">{method}</p>
                    <p className="mt-1 font-semibold text-foreground">{topic}</p>
                    <p className="text-xs text-muted-foreground">{timestamp}</p>
                  </div>
                  {isOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                </button>
                {isOpen && (
                  <div className="mt-4 space-y-4 text-foreground">
                    <section>
                      <p className="text-xs uppercase tracking-[0.3rem] text-muted-foreground">概要</p>
                      <div className="mt-2 rounded-xl border border-border/40 bg-background/70 p-3">
                        <MarkdownContent content={item.summary_text || "（暂无概要）"} />
                      </div>
                    </section>
                    {item.hex_text && (
                      <section>
                        <p className="text-xs uppercase tracking-[0.3rem] text-muted-foreground">卦辞</p>
                        <div className="mt-2 rounded-xl border border-border/40 bg-background/70 p-3">
                          <MarkdownContent content={item.hex_text} />
                        </div>
                      </section>
                    )}
                    {item.ai_text && (
                      <section>
                        <p className="text-xs uppercase tracking-[0.3rem] text-muted-foreground">AI 解读</p>
                        <div className="mt-2 rounded-xl border border-border/40 bg-background/70 p-3">
                          <MarkdownContent content={item.ai_text} />
                        </div>
                      </section>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </SheetContent>
    </Sheet>
  )
}
