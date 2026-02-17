"use client"

import { useMemo, useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import { useI18n } from "@/components/providers/i18n-provider"
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
  const { messages } = useI18n()
  const history = useWorkspaceStore((state) => state.history)
  const [expanded, setExpanded] = useState<string | null>(null)
  const formattedHistory = useMemo(() => history ?? [], [history])

  function toggleEntry(id: string) {
    setExpanded((current) => (current === id ? null : id))
  }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" className="w-full rounded-full">
          {messages.workspace.history.trigger} ({history.length})
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle>{messages.workspace.history.title}</SheetTitle>
          <SheetDescription>{messages.workspace.history.description}</SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-3">
          {formattedHistory.length === 0 && <p className="text-sm text-muted-foreground">{messages.workspace.history.empty}</p>}
          {formattedHistory.map((item, index) => {
            const key = `${item.session_id}-${index}`
            const isOpen = expanded === key
            const topic = (item.session_dict?.["topic"] as string) || messages.workspace.history.noTopic
            const method = (item.session_dict?.["method"] as string) || messages.workspace.history.noMethod
            const timestamp = (item.session_dict?.["current_time_str"] as string) || messages.workspace.history.noTime
            return (
              <div key={key} className="surface-soft rounded-2xl p-4 text-sm">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 text-left"
                  onClick={() => toggleEntry(key)}
                >
                  <div>
                    <p className="kicker">{method}</p>
                    <p className="mt-1 font-semibold text-foreground">{topic}</p>
                    <p className="text-xs text-muted-foreground">{timestamp}</p>
                  </div>
                  {isOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                </button>
                {isOpen && (
                  <div className="mt-4 space-y-4 text-foreground">
                    <section>
                      <p className="kicker">{messages.workspace.history.summaryLabel}</p>
                      <div className="mt-2 rounded-xl border border-border/40 bg-surface/75 p-3">
                        <MarkdownContent content={item.summary_text || messages.profile.noSummary} />
                      </div>
                    </section>
                    {item.hex_text && (
                      <section>
                        <p className="kicker">{messages.workspace.history.hexLabel}</p>
                        <div className="mt-2 rounded-xl border border-border/40 bg-surface/75 p-3">
                          <MarkdownContent content={item.hex_text} />
                        </div>
                      </section>
                    )}
                    {item.ai_text && (
                      <section>
                        <p className="kicker">{messages.workspace.history.aiLabel}</p>
                        <div className="mt-2 rounded-xl border border-border/40 bg-surface/75 p-3">
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
