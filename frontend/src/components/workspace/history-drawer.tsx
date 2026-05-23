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
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { useWorkspaceStore, type JournalStatus } from "@/lib/store"

export function HistoryDrawer() {
  const { locale, messages } = useI18n()
  const history = useWorkspaceStore((state) => state.history)
  const journal = useWorkspaceStore((state) => state.journal)
  const updateJournal = useWorkspaceStore((state) => state.updateJournal)
  const [expanded, setExpanded] = useState<string | null>(null)
  const formattedHistory = useMemo(
    () =>
      [...(history ?? [])].sort((a, b) => {
        const aPinned = journal[a.session_id]?.pinned ? 1 : 0
        const bPinned = journal[b.session_id]?.pinned ? 1 : 0
        return bPinned - aPinned
      }),
    [history, journal],
  )

  function toggleEntry(id: string) {
    setExpanded((current) => (current === id ? null : id))
  }

  const journalLabels =
    locale === "zh"
      ? {
          pinned: "已置顶",
          pin: "置顶",
          statuses: {
            open: "进行中",
            watching: "观察中",
            resolved: "已结束",
          },
          title: "阅读复盘",
          revisitAt: "重访日期",
          outcome: "实际发生了什么？",
          outcomePlaceholder: "记录局势如何变化、发生了什么，或你正在等待什么信号。",
        }
      : {
          pinned: "Pinned",
          pin: "Pin",
          statuses: {
            open: "Open",
            watching: "Watching",
            resolved: "Resolved",
          },
          title: "Reading journal",
          revisitAt: "Revisit date",
          outcome: "What actually happened?",
          outcomePlaceholder: "What changed, what happened, or what signal are you waiting for?",
        }

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" className="w-full rounded-md">
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
              <div key={key} className="surface-soft rounded-lg p-4 text-sm">
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 text-left"
                  onClick={() => toggleEntry(key)}
                  aria-expanded={isOpen}
                  aria-controls={`history-entry-${key}`}
                >
                  <div>
                    <p className="kicker">{method}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-foreground">{topic}</p>
                      {journal[item.session_id]?.pinned && (
                        <span className="rounded-md border border-primary/40 bg-primary/10 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-primary">
                          {journalLabels.pinned}
                        </span>
                      )}
                      <span className="rounded-md border border-border/60 bg-surface px-2 py-0.5 text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                        {journalLabels.statuses[journal[item.session_id]?.status ?? "open"]}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">{timestamp}</p>
                  </div>
                  {isOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                </button>
                {isOpen && (
                  <div id={`history-entry-${key}`} className="mt-4 space-y-4 text-foreground">
                    <section className="rounded-md border border-border/40 bg-surface/90 p-3">
                      <p className="kicker">{journalLabels.title}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(["open", "watching", "resolved"] as JournalStatus[]).map((status) => (
                          <Button
                            key={status}
                            type="button"
                            size="sm"
                            variant={(journal[item.session_id]?.status ?? "open") === status ? "default" : "outline"}
                            className="rounded-md"
                          onClick={() => updateJournal(item.session_id, { status })}
                        >
                          {journalLabels.statuses[status]}
                        </Button>
                      ))}
                        <Button
                          type="button"
                          size="sm"
                          variant={journal[item.session_id]?.pinned ? "default" : "outline"}
                          className="rounded-md"
                          onClick={() => updateJournal(item.session_id, { pinned: !journal[item.session_id]?.pinned })}
                        >
                          {journal[item.session_id]?.pinned ? journalLabels.pinned : journalLabels.pin}
                        </Button>
                      </div>
                      <div className="mt-3 grid gap-3 sm:grid-cols-[12rem_1fr]">
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-muted-foreground">{journalLabels.revisitAt}</p>
                          <Input
                            type="date"
                            value={journal[item.session_id]?.revisitAt ?? ""}
                            onChange={(event) => updateJournal(item.session_id, { revisitAt: event.target.value })}
                          />
                        </div>
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-muted-foreground">{journalLabels.outcome}</p>
                          <Textarea
                            value={journal[item.session_id]?.outcomeNote ?? ""}
                            onChange={(event) => updateJournal(item.session_id, { outcomeNote: event.target.value })}
                            rows={2}
                            placeholder={journalLabels.outcomePlaceholder}
                          />
                        </div>
                      </div>
                    </section>
                    <section>
                      <p className="kicker">{messages.workspace.history.summaryLabel}</p>
                      <div className="mt-2 rounded-md border border-border/40 bg-surface/90 p-3">
                        <MarkdownContent content={item.summary_text || messages.profile.noSummary} />
                      </div>
                    </section>
                    {item.hex_text && (
                      <section>
                        <p className="kicker">{messages.workspace.history.hexLabel}</p>
                        <div className="mt-2 rounded-md border border-border/40 bg-surface/90 p-3">
                          <MarkdownContent content={item.hex_text} />
                        </div>
                      </section>
                    )}
                    {item.ai_text && (
                      <section>
                        <p className="kicker">{messages.workspace.history.aiLabel}</p>
                        <div className="mt-2 rounded-md border border-border/40 bg-surface/90 p-3">
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
