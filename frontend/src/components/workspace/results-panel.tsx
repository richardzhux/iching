"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { MarkdownContent } from "@/components/ui/markdown-content"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { useWorkspaceStore, type JournalStatus, type ReadingJournalEntry } from "@/lib/store"
import type {
  BaziPillar,
  HexSection,
  ReadingBrief,
  ReadingBriefKeyPassage,
  ReadingBriefSourcePassage,
  SessionPayload,
} from "@/types/api"

import { ChatPanel } from "./chat-panel"
import { HexagramHeader } from "./hexagram-visual"
import { NajiaTableView } from "./najia-table"

export function ResultsPanel() {
  const { messages, locale } = useI18n()
  const result = useWorkspaceStore((state) => state.result)
  const resetSession = useWorkspaceStore((state) => state.resetSession)
  const setView = useWorkspaceStore((state) => state.setView)
  const resultsTab = useWorkspaceStore((state) => state.resultsTab)
  const setResultsTab = useWorkspaceStore((state) => state.setResultsTab)
  const setPendingChatPrompt = useWorkspaceStore((state) => state.setPendingChatPrompt)
  const journal = useWorkspaceStore((state) => state.journal)
  const updateJournal = useWorkspaceStore((state) => state.updateJournal)
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null)
  const brief = result ? resolveReadingBrief(result, locale) : null

  const openSourceReader = (sourceId: string) => {
    if (sourceId) {
      setActiveSourceId(sourceId)
    }
  }

  if (!result || !brief) {
    return (
      <Card className="surface-card border-border/40 text-foreground">
        <CardHeader>
          <CardTitle className="text-lg">{messages.workspace.results.waitingTitle}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          {messages.workspace.results.waitingBody}
        </CardContent>
      </Card>
    )
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="surface-card rounded-lg border-border/40 text-foreground">
        <CardHeader className="flex flex-col gap-3 border-b border-border/50 pb-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle className="text-lg">{messages.workspace.results.title}</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {locale === "zh" ? "先看判断简报，再展开证据与追问。" : "Start with the brief, then inspect evidence or continue the thread."}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setView("form")}>
              {messages.workspace.results.backToSetup}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => resetSession()}>
              {messages.workspace.results.startNew}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs
            value={resultsTab}
            onValueChange={(value) => {
              if (value === "summary" || value === "hex" || value === "ai") {
                setResultsTab(value)
              }
            }}
          >
            <TabsList className="grid w-full grid-cols-3 rounded-md bg-surface-elevated text-foreground">
              <TabsTrigger value="summary">{locale === "zh" ? "导引" : "Guidance"}</TabsTrigger>
              <TabsTrigger value="hex">{locale === "zh" ? "机理" : "Mechanics"}</TabsTrigger>
              <TabsTrigger value="ai">{locale === "zh" ? "追问" : "Follow-up"}</TabsTrigger>
            </TabsList>
            <TabsContent value="summary">
              <ReadingBriefPanel
                brief={brief}
                sessionId={result.session_id}
                journalEntry={journal[result.session_id]}
                onJournalChange={(patch) => updateJournal(result.session_id, patch)}
                onSourceSelect={openSourceReader}
                onPrompt={(prompt) => {
                  setPendingChatPrompt(prompt)
                  setResultsTab("ai")
                }}
              />
            </TabsContent>
            <TabsContent value="hex">
              <HexResultBlock result={result} brief={brief} onSourceSelect={openSourceReader} />
            </TabsContent>
            <TabsContent value="ai">
              <ChatPanel session={result} />
            </TabsContent>
          </Tabs>
          <SourceReaderSheet
            brief={brief}
            activeSourceId={activeSourceId}
            open={Boolean(activeSourceId)}
            onOpenChange={(open) => {
              if (!open) {
                setActiveSourceId(null)
              }
            }}
            onSourceSelect={setActiveSourceId}
          />
        </CardContent>
      </Card>
    </motion.div>
  )
}

function resolveReadingBrief(result: SessionPayload, locale: "en" | "zh"): ReadingBrief {
  const fallbackSourcePassages = sourcePassagesFromSections(result.hex_sections || [])
  if (result.reading_brief?.headline) {
    const sourcePassages = result.reading_brief.source_passages?.length
      ? withResolvedSourceIds(result.reading_brief.source_passages)
      : fallbackSourcePassages
    const keyPassages = result.reading_brief.key_passages?.length
      ? withResolvedSourceIds(result.reading_brief.key_passages)
      : keyPassagesFromResult(result, locale)
    return {
      ...result.reading_brief,
      key_passages: keyPassages,
      source_passages: sourcePassages,
      archive_sources: result.reading_brief.archive_sources ?? archiveCoverageFromPassages(sourcePassages),
    }
  }
  const mainName = result.hex_overview?.main_hexagram?.name || (locale === "zh" ? "本卦" : "Primary hexagram")
  const changedName = result.hex_overview?.changed_hexagram?.name
  const topic = (result.session_dict?.["topic"] as string | undefined) || (locale === "zh" ? "本次问题" : "This reading")
  const question = result.session_dict?.["user_question"] as string | undefined
  return {
    headline: `${topic}｜${mainName}${changedName ? ` → ${changedName}` : ""}`,
    stance: result.hex_overview?.changed_hexagram ? "changing" : "stable",
    plain_language:
      locale === "zh"
        ? `${question ? `围绕“${question}”，` : ""}先看本卦格局，再用动爻、纳甲和经典段落校验。`
        : `${question ? `For "${question}", ` : ""}start with the primary hexagram, then validate through moving lines, Najia, and source passages.`,
    evidence: [
      {
        conclusion: locale === "zh" ? "概要" : "Summary",
        basis: locale === "zh" ? "旧会话兼容简报" : "Legacy session fallback",
        plain: result.summary_text || result.hex_text,
      },
    ],
    timing: [
      {
        window: locale === "zh" ? "近期" : "Near term",
        condition: locale === "zh" ? "出现新事实后回到同一会话追问。" : "Return to this same session when new facts emerge.",
        confidence: 50,
      },
    ],
    actions: [
      {
        action: locale === "zh" ? "先做低成本验证。" : "Run a low-cost validation first.",
        cadence: locale === "zh" ? "下一步" : "Next step",
        signal: locale === "zh" ? "阻力是否下降。" : "Whether resistance decreases.",
      },
    ],
    risks: [
      locale === "zh"
        ? "这是旧会话回退简报，完整结构会在新起卦后生成。"
        : "This is a fallback brief for an older session; new readings include the full structure.",
    ],
    followup_prompts:
      locale === "zh"
        ? ["这卦最关键的风险是什么？", "下一步应该怎么做？", "请展开经典依据。"]
        : ["What is the key risk in this reading?", "What should I do next?", "Expand the classical evidence."],
    key_passages: keyPassagesFromResult(result, locale),
    source_passages: fallbackSourcePassages,
    archive_sources: archiveCoverageFromPassages(fallbackSourcePassages),
    personal_context: {
      status: "reserved",
      current_scope: "casting_time_bazi_only",
      note: locale === "zh"
        ? "本阶段只使用起卦时间八字；出生资料与大运流年会作为后续独立个人画像层接入。"
        : "This phase only uses casting-time BaZi; natal profile and fortune-cycle data are reserved for a future personal lens.",
    },
  }
}

function compactText(value: string | undefined, limit: number) {
  const text = (value || "").replace(/\s+/g, " ").trim()
  if (text.length <= limit) {
    return text
  }
  return `${text.slice(0, limit - 1).trim()}…`
}

function sourceIdForPassage(passage: Pick<ReadingBriefSourcePassage, "source_id" | "slot_key" | "source" | "title">) {
  if (passage.source_id) {
    return passage.source_id
  }
  return `${passage.slot_key || passage.title}::${passage.source || "unknown"}`
}

function withResolvedSourceIds<T extends ReadingBriefSourcePassage>(passages: T[]): T[] {
  return passages.map((passage) => ({
    ...passage,
    source_id: sourceIdForPassage(passage),
  }))
}

function sectionSourceIdForDrawer(section: HexSection) {
  if (section.source_id) {
    return section.source_id
  }
  return `${section.slot_key || section.title}::${section.source || "unknown"}`
}

function sourcePassagesFromSections(sections: HexSection[]): ReadingBriefSourcePassage[] {
  return sections
    .filter((section) => section.content)
    .map((section) => {
      const source = section.source || "unknown"
      const slotKey = section.slot_key || `${section.hexagram_name}:${section.section_kind}`
      const sourceLabel =
        section.source_label ||
        (source === "takashima"
          ? "高岛易断"
          : source === "english_commentary"
            ? "English Commentary"
            : source === "symbolic"
              ? "卦象"
              : "卦辞库")
      return {
        source_id: section.source_id || `${slotKey}::${source}`,
        slot_key: slotKey,
        source,
        source_label: sourceLabel,
        hexagram_name: section.hexagram_name,
        section_kind: section.section_kind,
        line_key: section.line_key,
        title: section.title,
        content: section.content,
        citation: [sourceLabel, section.hexagram_name, section.title].filter(Boolean).join("｜"),
        visible_by_default: section.visible_by_default,
        importance: section.importance,
      }
    })
}

function decisiveSectionsFromResult(result: SessionPayload): HexSection[] {
  const sections = (result.hex_sections || []).filter((section) => section.content)
  const overviewLines = result.hex_overview?.lines || []
  const movingCount = overviewLines.filter((line) => line.is_moving).length
  const mainName = result.hex_overview?.main_hexagram?.name || ""
  const allValues = overviewLines.map((line) => line.value)

  let candidates: HexSection[] = []
  if (movingCount === 0) {
    candidates = sections.filter(
      (section) =>
        section.hexagram_type === "main" &&
        section.section_kind === "top" &&
        section.visible_by_default,
    )
  } else if (
    movingCount === 6 &&
    ((allValues.every((value) => value === 9) && mainName.includes("乾")) ||
      (allValues.every((value) => value === 6) && mainName.includes("坤")))
  ) {
    candidates = sections.filter(
      (section) =>
        section.hexagram_type === "main" &&
        section.section_kind === "line" &&
        section.line_key === "all" &&
        section.visible_by_default,
    )
  } else if (movingCount === 6) {
    candidates = sections.filter(
      (section) =>
        section.hexagram_type === "changed" &&
        section.section_kind === "top" &&
        section.visible_by_default,
    )
  } else {
    candidates = sections.filter(
      (section) =>
        section.hexagram_type === "main" &&
        section.section_kind === "line" &&
        section.visible_by_default,
    )
  }

  if (!candidates.length) {
    candidates = sections.filter((section) => section.visible_by_default)
  }
  if (!candidates.length && sections.length) {
    candidates = [sections[0]]
  }

  return candidates
}

function keyPassagesFromResult(result: SessionPayload, locale: "en" | "zh"): ReadingBriefKeyPassage[] {
  return sourcePassagesFromSections(decisiveSectionsFromResult(result))
    .slice(0, 4)
    .map((passage) => {
      const excerpt = compactText(passage.content, 360)
      return {
        ...passage,
        content: excerpt,
        quote: excerpt,
        excerpt,
        role: passage.title.includes("变卦") ? "secondary_context" : "primary",
        plain_language: fallbackKeyPlainLanguage(passage, locale),
        why_it_matters: fallbackKeyReason(passage, result, locale),
      }
    })
}

function fallbackKeyPlainLanguage(passage: ReadingBriefSourcePassage, locale: "en" | "zh") {
  if (locale !== "zh") {
    if (passage.title.includes("Changed")) {
      return "This is the secondary outcome context, not the primary decision evidence."
    }
    if (passage.line_key === "all") {
      return "All lines are moving, so this passage governs the whole transformation."
    }
    if (passage.section_kind === "line") {
      return "This line marks the active point of change in the question."
    }
    return "This passage frames the overall situation before any line-level evidence."
  }
  if (passage.title.includes("变卦")) {
    return "这段只作为变化后的场景参照，帮助确认趋势落点。"
  }
  if (passage.line_key === "all") {
    return "全爻动时用这一段统摄整卦变化，不把六爻平均展开。"
  }
  if (passage.section_kind === "line") {
    return "这段对应本次取用的爻位，说明变化发生在哪里。"
  }
  return "这段说明本卦当前局面的底色、边界和主方向。"
}

function fallbackKeyReason(passage: ReadingBriefSourcePassage, result: SessionPayload, locale: "en" | "zh") {
  const lines = result.hex_overview?.lines || []
  const movingCount = lines.filter((line) => line.is_moving).length
  const values = lines.map((line) => line.value)
  const mainName = result.hex_overview?.main_hexagram?.name || ""

  if (locale !== "zh") {
    if (passage.title.includes("Changed")) {
      return "The changed hexagram stays secondary: it shows the next state, not the first judgment."
    }
    if (passage.line_key === "all" && values.every((value) => value === 9) && mainName.includes("乾")) {
      return "Qian with all six moving lines uses Yong Jiu as the decisive rule."
    }
    if (passage.line_key === "all" && values.every((value) => value === 6) && mainName.includes("坤")) {
      return "Kun with all six moving lines uses Yong Liu as the decisive rule."
    }
    if (movingCount === 0) {
      return "No moving lines means the primary hexagram judgment is the core evidence."
    }
    return "This is the selected moving-line evidence, the point where the situation changes."
  }
  if (passage.title.includes("变卦")) {
    return "变卦只放在第二层，说明变化后的背景，不抢主证据位置。"
  }
  if (passage.line_key === "all" && values.every((value) => value === 9) && mainName.includes("乾")) {
    return "乾卦六爻全动，传统以用九为总断。"
  }
  if (passage.line_key === "all" && values.every((value) => value === 6) && mainName.includes("坤")) {
    return "坤卦六爻全动，传统以用六为总断。"
  }
  if (movingCount === 0) {
    return "本卦无动爻，卦辞就是本次判断的核心依据。"
  }
  return "这是本次取用的动爻，代表问题真正发生变化的关键位置。"
}

function passageDisplayText(passage: ReadingBriefSourcePassage | ReadingBriefKeyPassage) {
  return "excerpt" in passage && passage.excerpt ? passage.excerpt : passage.content
}

function archiveCoverageFromPassages(passages: ReadingBriefSourcePassage[]) {
  return {
    total_passages: passages.length,
    sources: passages.reduce<Record<string, number>>((acc, passage) => {
      acc[passage.source] = (acc[passage.source] ?? 0) + 1
      return acc
    }, {}),
    slot_keys: Array.from(new Set(passages.map((passage) => passage.slot_key))),
    primary_slot_keys: Array.from(new Set(passages.filter((passage) => passage.visible_by_default).map((passage) => passage.slot_key))),
  }
}

function stanceCopy(stance: string, locale: "en" | "zh") {
  const zh: Record<string, string> = {
    stable: "格局稳定",
    changing: "变化中",
    transforming: "强变化",
  }
  const en: Record<string, string> = {
    stable: "Stable pattern",
    changing: "Changing pattern",
    transforming: "Full transformation",
  }
  return (locale === "zh" ? zh : en)[stance] ?? stance
}

function ReadingBriefPanel({
  brief,
  sessionId,
  journalEntry,
  onJournalChange,
  onSourceSelect,
  onPrompt,
}: {
  brief: ReadingBrief
  sessionId: string
  journalEntry?: ReadingJournalEntry
  onJournalChange: (patch: Partial<ReadingJournalEntry>) => void
  onSourceSelect: (sourceId: string) => void
  onPrompt: (prompt: string) => void
}) {
  const { locale } = useI18n()
  const labels =
    locale === "zh"
      ? {
          stance: "判断状态",
          evidence: "证据短链",
          keyPassages: "重点段落解析",
          keyPassageBody: "只保留本次断法真正取用的卦辞、动爻或用九/用六。",
          excerpt: "原文摘录",
          meaning: "白话",
          matters: "为什么重要",
          source: "来源",
          openSource: "打开原文",
          timing: "应期与条件",
          actions: "行动建议",
          risks: "风险信号",
          followups: "继续追问",
          confidence: "置信度",
          condition: "条件",
          cadence: "节奏",
          signal: "观察指标",
        }
      : {
          stance: "Reading state",
          evidence: "Evidence chain",
          keyPassages: "Key Passage Analysis",
          keyPassageBody: "Only the judgment text, moving line, or Yong Jiu/Yong Liu passage this reading actually uses.",
          excerpt: "Excerpt",
          meaning: "Plain meaning",
          matters: "Why it matters",
          source: "Source",
          openSource: "Open source",
          timing: "Timing and conditions",
          actions: "Actions",
          risks: "Risk signals",
          followups: "Continue with",
          confidence: "Confidence",
          condition: "Condition",
          cadence: "Cadence",
          signal: "Signal",
        }
  const keyPassageHighlightSection =
    "rounded-lg border border-amber-400/50 bg-amber-100/25 p-5 shadow-sm dark:border-amber-200/35 dark:bg-amber-200/10"

  return (
    <div className="mt-4 space-y-5">
      <section className="rounded-lg border border-border/50 bg-surface p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.stance}</p>
            <h2 className="mt-2 text-2xl font-semibold leading-tight text-foreground">{brief.headline}</h2>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{brief.plain_language}</p>
          </div>
          <span className="w-fit rounded-md border border-primary/40 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            {stanceCopy(brief.stance, locale)}
          </span>
        </div>
      </section>

      {brief.key_passages?.length ? (
        <section className={keyPassageHighlightSection}>
          <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-amber-700 dark:text-amber-200">
                {locale === "zh" ? "卦辞解析" : "Decisive passage analysis"}
              </p>
              <h3 className="mt-1 text-base font-semibold text-foreground">{labels.keyPassages}</h3>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{labels.keyPassageBody}</p>
            </div>
            <span className="w-fit rounded-md border border-amber-400/60 bg-amber-200/35 px-2 py-1 text-xs font-semibold text-amber-800 dark:border-amber-200/50 dark:bg-amber-200/15 dark:text-amber-100">
              {brief.key_passages.length}
            </span>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {brief.key_passages.map((passage, index) => (
              <article
                key={`${passage.slot_key}-${passage.source}-${index}`}
                className="rounded-md border border-amber-300/45 bg-surface/95 p-4 shadow-sm dark:border-amber-200/20"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold leading-6 text-foreground">{passage.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {labels.source}: {passage.source_label}
                    </p>
                  </div>
                  {passage.role === "secondary_context" ? (
                    <span className="rounded-md border border-border/60 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">
                      {locale === "zh" ? "次要参照" : "Context"}
                    </span>
                  ) : null}
                </div>
                <div className="mt-3 rounded-md border border-border/40 bg-surface p-3">
                  <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">
                    {labels.excerpt}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-foreground">{passage.excerpt || passage.quote || passage.content}</p>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">
                      {labels.meaning}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-foreground">{passage.plain_language}</p>
                  </div>
                  <div>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">
                      {labels.matters}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-foreground">{passage.why_it_matters}</p>
                  </div>
                </div>
                {passage.source_id ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-3 rounded-md"
                    onClick={() => onSourceSelect(sourceIdForPassage(passage))}
                  >
                    {labels.openSource}
                  </Button>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <ParallelSourcePanel brief={brief} onSourceSelect={onSourceSelect} />

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg border border-border/50 bg-surface p-5">
          <h3 className="text-sm font-semibold text-foreground">{labels.evidence}</h3>
          <div className="mt-4 space-y-3">
            {brief.evidence.map((item, index) => (
              <article key={`${item.basis}-${index}`} className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
                <p className="text-sm font-semibold text-foreground">{item.conclusion}</p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">{item.basis}</p>
                <p className="mt-2 text-sm leading-6 text-foreground">{item.plain}</p>
                {(item.source_id || item.source_ids?.[0]) && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-2 h-auto rounded-md px-0 text-xs font-semibold text-primary hover:bg-transparent hover:text-primary"
                    onClick={() => onSourceSelect(item.source_id || item.source_ids?.[0] || "")}
                  >
                    {labels.openSource}
                  </Button>
                )}
              </article>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <section className="rounded-lg border border-border/50 bg-surface p-5">
            <h3 className="text-sm font-semibold text-foreground">{labels.timing}</h3>
            <div className="mt-4 space-y-3">
              {brief.timing.map((item, index) => (
                <div key={`${item.window}-${index}`} className="rounded-md bg-surface-elevated/90 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-foreground">{item.window}</p>
                    <span className="text-xs text-muted-foreground">
                      {labels.confidence} {item.confidence}%
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {labels.condition}: {item.condition}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-border/50 bg-surface p-5">
            <h3 className="text-sm font-semibold text-foreground">{labels.risks}</h3>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
              {brief.risks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
          </section>
        </div>
      </section>

      <section className="rounded-lg border border-border/50 bg-surface p-5">
        <h3 className="text-sm font-semibold text-foreground">{labels.actions}</h3>
        <div className="mt-4 grid gap-3 lg:grid-cols-3">
          {brief.actions.map((item, index) => (
            <article key={`${item.action}-${index}`} className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
              <p className="text-sm font-semibold leading-6 text-foreground">{item.action}</p>
              <p className="mt-3 text-xs text-muted-foreground">{labels.cadence}: {item.cadence}</p>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{labels.signal}: {item.signal}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border/50 bg-surface p-5">
        <h3 className="text-sm font-semibold text-foreground">{labels.followups}</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {brief.followup_prompts.map((prompt) => (
            <Button key={prompt} type="button" variant="outline" size="sm" className="rounded-md" onClick={() => onPrompt(prompt)}>
              {prompt}
            </Button>
          ))}
        </div>
      </section>

      <ReadingJournalPanel
        sessionId={sessionId}
        entry={journalEntry}
        onChange={onJournalChange}
      />
    </div>
  )
}

function ReadingJournalPanel({
  sessionId,
  entry,
  onChange,
}: {
  sessionId: string
  entry?: ReadingJournalEntry
  onChange: (patch: Partial<ReadingJournalEntry>) => void
}) {
  const { locale } = useI18n()
  const labels =
    locale === "zh"
      ? {
          title: "阅读复盘",
          body: "把这次起卦变成可回看的记录，而不是一次性的回答。",
          status: "状态",
          pin: "固定",
          pinned: "已固定",
          revisit: "重访日期",
          outcome: "实际发生了什么？",
          placeholder: "记录后来发生的事、哪个爻最准确、当时误读了什么，或还在等待什么信号。",
          session: "会话",
        }
      : {
          title: "Reading journal",
          body: "Turn this reading into a record you can revisit instead of a one-off answer.",
          status: "Status",
          pin: "Pin",
          pinned: "Pinned",
          revisit: "Revisit date",
          outcome: "What actually happened?",
          placeholder: "Note what changed, which line proved relevant, what you misread, or which signal is still pending.",
          session: "Session",
        }
  const currentStatus = entry?.status ?? "open"
  const statuses: JournalStatus[] = ["open", "watching", "resolved"]

  return (
    <section className="rounded-lg border border-border/50 bg-surface p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{labels.title}</h3>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{labels.body}</p>
        </div>
        <span className="w-fit rounded-md border border-border/60 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">
          {labels.session} {sessionId.slice(0, 8)}
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_12rem]">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {statuses.map((status) => (
              <Button
                key={status}
                type="button"
                size="sm"
                variant={currentStatus === status ? "default" : "outline"}
                className="rounded-md"
                onClick={() => onChange({ status })}
              >
                {status}
              </Button>
            ))}
            <Button
              type="button"
              size="sm"
              variant={entry?.pinned ? "default" : "outline"}
              className="rounded-md"
              onClick={() => onChange({ pinned: !entry?.pinned })}
            >
              {entry?.pinned ? labels.pinned : labels.pin}
            </Button>
          </div>
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">{labels.outcome}</p>
            <Textarea
              value={entry?.outcomeNote ?? ""}
              onChange={(event) => onChange({ outcomeNote: event.target.value })}
              rows={3}
              placeholder={labels.placeholder}
            />
          </div>
        </div>

        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">{labels.revisit}</p>
          <Input
            type="date"
            value={entry?.revisitAt ?? ""}
            onChange={(event) => onChange({ revisitAt: event.target.value })}
          />
        </div>
      </div>
    </section>
  )
}

function ParallelSourcePanel({
  brief,
  onSourceSelect,
}: {
  brief: ReadingBrief
  onSourceSelect: (sourceId: string) => void
}) {
  const { locale } = useI18n()
  const [lens, setLens] = useState<"all" | "chinese" | "english" | "ai">("all")
  const sourcePassages = brief.source_passages || []
  const decisiveSlotKeys = new Set(
    [
      ...(brief.key_passages || []).map((passage) => passage.slot_key),
      ...(brief.archive_sources?.primary_slot_keys || []),
    ].filter(Boolean),
  )
  const scopedPassages = sourcePassages.filter((passage) =>
    decisiveSlotKeys.size ? decisiveSlotKeys.has(passage.slot_key) : passage.visible_by_default,
  )
  const passages = scopedPassages.length ? scopedPassages : sourcePassages.slice(0, 6)
  const evidenceSourceId = brief.evidence.flatMap((item) => item.source_ids || (item.source_id ? [item.source_id] : []))[0]
  const labels =
    locale === "zh"
      ? {
          title: "平行阅读",
          body: "把中文原典、英文解释和 AI 综合分开看，避免把翻译、出处和判断混成一段。",
          all: "全部",
          chinese: "中文来源",
          english: "English",
          ai: "AI 综合",
          open: "打开原文",
          empty: "当前暂无可对照来源。",
          synthesis: "AI 综合",
        }
      : {
          title: "Parallel Reading",
          body: "Keep Chinese source text, English commentary, and AI synthesis as separate layers.",
          all: "All",
          chinese: "Chinese",
          english: "English",
          ai: "AI synthesis",
          open: "Open source",
          empty: "No comparable sources are available yet.",
          synthesis: "AI synthesis",
        }

  const chinesePassages = passages.filter((passage) => passage.source !== "english_commentary")
  const englishPassages = passages.filter((passage) => passage.source === "english_commentary")
  const showChinese = lens === "all" || lens === "chinese"
  const showEnglish = lens === "all" || lens === "english"
  const showAi = lens === "all" || lens === "ai"
  const hasContent = passages.length || brief.plain_language || brief.evidence.length

  if (!hasContent) {
    return null
  }

  return (
    <section className="rounded-lg border border-border/50 bg-surface p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{labels.title}</h3>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{labels.body}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {(["all", "chinese", "english", "ai"] as const).map((value) => (
            <Button
              key={value}
              type="button"
              variant={lens === value ? "default" : "outline"}
              size="sm"
              className="rounded-md"
              onClick={() => setLens(value)}
            >
              {labels[value]}
            </Button>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        {showChinese &&
          chinesePassages.map((passage) => (
            <SourceLensCard
              key={sourceIdForPassage(passage)}
              passage={passage}
              buttonLabel={labels.open}
              onSourceSelect={onSourceSelect}
            />
          ))}
        {showEnglish &&
          englishPassages.map((passage) => (
            <SourceLensCard
              key={sourceIdForPassage(passage)}
              passage={passage}
              buttonLabel={labels.open}
              onSourceSelect={onSourceSelect}
            />
          ))}
        {showAi && (
          <article className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.synthesis}</p>
            <p className="mt-2 text-sm leading-6 text-foreground">{brief.plain_language}</p>
            {brief.evidence[0]?.plain ? (
              <p className="mt-3 border-t border-border/50 pt-3 text-xs leading-5 text-muted-foreground">
                {brief.evidence[0].plain}
              </p>
            ) : null}
            {evidenceSourceId ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="mt-2 h-auto rounded-md px-0 text-xs font-semibold text-primary hover:bg-transparent hover:text-primary"
                onClick={() => onSourceSelect(evidenceSourceId)}
              >
                {labels.open}
              </Button>
            ) : null}
          </article>
        )}
      </div>
      {!passages.length && (
        <div className="mt-4 rounded-md border border-border/50 bg-surface-elevated/80 p-4 text-sm text-muted-foreground">
          {labels.empty}
        </div>
      )}
    </section>
  )
}

function SourceLensCard({
  passage,
  buttonLabel,
  onSourceSelect,
}: {
  passage: ReadingBriefSourcePassage
  buttonLabel: string
  onSourceSelect: (sourceId: string) => void
}) {
  const sourceId = sourceIdForPassage(passage)
  return (
    <article className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-semibold leading-6 text-foreground">{passage.title}</p>
        <span className="rounded-md border border-border/60 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">
          {passage.source_label || passage.source}
        </span>
      </div>
      <p className="mt-2 text-sm leading-6 text-foreground">{compactText(passage.content, 260)}</p>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="mt-2 h-auto rounded-md px-0 text-xs font-semibold text-primary hover:bg-transparent hover:text-primary"
        onClick={() => onSourceSelect(sourceId)}
      >
        {buttonLabel}
      </Button>
    </article>
  )
}

function SourceReaderSheet({
  brief,
  activeSourceId,
  open,
  onOpenChange,
  onSourceSelect,
}: {
  brief: ReadingBrief
  activeSourceId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSourceSelect: (sourceId: string) => void
}) {
  const { locale } = useI18n()
  const sourcePassages = withResolvedSourceIds(
    brief.source_passages?.length
      ? brief.source_passages
      : ((brief.key_passages || []) as ReadingBriefSourcePassage[]),
  )
  const selected = sourcePassages.find((passage) => sourceIdForPassage(passage) === activeSourceId) || sourcePassages[0]
  const selectedSlot = selected?.slot_key
  const relatedPassages = selectedSlot
    ? sourcePassages.filter((passage) => passage.slot_key === selectedSlot)
    : sourcePassages.slice(0, 6)
  const otherPassages = sourcePassages
    .filter((passage) => (selectedSlot ? passage.slot_key !== selectedSlot : true))
    .slice(0, 8)
  const labels =
    locale === "zh"
      ? {
          title: "原文笔记",
          body: "在右侧查看本次取用的具体来源块，不把导引页撑成长篇档案。",
          sameSlot: "同一槽位",
          otherSlots: "其他相关",
          citation: "引用",
          empty: "当前没有可打开的来源段落。",
        }
      : {
          title: "Source notebook",
          body: "Review the exact source chunks for this reading without expanding the whole result page.",
          sameSlot: "Same slot",
          otherSlots: "Other relevant",
          citation: "Citation",
          empty: "No source passage is available for this reading.",
        }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="!w-full border-border bg-background p-0 sm:!max-w-2xl lg:!max-w-3xl"
      >
        <SheetHeader className="border-b border-border/50 p-5 pr-12">
          <SheetTitle>{labels.title}</SheetTitle>
          <SheetDescription>{selected?.citation || labels.body}</SheetDescription>
        </SheetHeader>

        {selected ? (
          <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[16rem_1fr]">
            <aside className="min-h-0 overflow-y-auto border-b border-border/50 p-3 lg:border-b-0 lg:border-r">
              <SourceChunkList
                title={labels.sameSlot}
                passages={relatedPassages}
                activeSourceId={sourceIdForPassage(selected)}
                onSourceSelect={onSourceSelect}
              />
              {otherPassages.length ? (
                <div className="mt-4">
                  <SourceChunkList
                    title={labels.otherSlots}
                    passages={otherPassages}
                    activeSourceId={sourceIdForPassage(selected)}
                    onSourceSelect={onSourceSelect}
                  />
                </div>
              ) : null}
            </aside>

            <main className="min-h-0 overflow-y-auto p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">
                    {selected.source_label || selected.source}
                  </p>
                  <h3 className="mt-2 text-xl font-semibold leading-8 text-foreground">{selected.title}</h3>
                </div>
                <span className="rounded-md border border-border/60 px-2 py-1 text-xs text-muted-foreground">
                  {selected.slot_key}
                </span>
              </div>
              <div className="mt-4 rounded-md border border-border/50 bg-surface p-4">
                <MarkdownContent content={passageDisplayText(selected)} />
              </div>
              <p className="mt-4 text-xs leading-5 text-muted-foreground">
                {labels.citation}: {selected.citation}
              </p>
            </main>
          </div>
        ) : (
          <div className="p-5 text-sm text-muted-foreground">{labels.empty}</div>
        )}
      </SheetContent>
    </Sheet>
  )
}

function SourceChunkList({
  title,
  passages,
  activeSourceId,
  onSourceSelect,
}: {
  title: string
  passages: ReadingBriefSourcePassage[]
  activeSourceId: string
  onSourceSelect: (sourceId: string) => void
}) {
  return (
    <div>
      <p className="px-2 text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{title}</p>
      <div className="mt-2 space-y-2">
        {passages.map((passage) => {
          const sourceId = sourceIdForPassage(passage)
          const active = sourceId === activeSourceId
          return (
            <button
              key={sourceId}
              type="button"
              className={`w-full rounded-md border p-3 text-left transition-colors ${
                active
                  ? "border-primary/50 bg-primary/10 text-foreground"
                  : "border-border/50 bg-surface text-muted-foreground hover:border-border hover:bg-surface-elevated"
              }`}
              onClick={() => onSourceSelect(sourceId)}
            >
              <span className="block text-xs font-semibold leading-5">{passage.source_label || passage.source}</span>
              <span className="mt-1 block text-xs leading-5">{compactText(passage.title, 72)}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function MechanicsInsightPanel({
  result,
  brief,
  primarySections,
  secondarySections,
  onSourceSelect,
}: {
  result: SessionPayload
  brief: ReadingBrief
  primarySections: HexSection[]
  secondarySections: HexSection[]
  onSourceSelect: (sourceId: string) => void
}) {
  const { locale } = useI18n()
  const lines = result.hex_overview?.lines || []
  const movingLines = lines.filter((line) => line.is_moving).sort((a, b) => a.position - b.position)
  const mainName = result.hex_overview?.main_hexagram?.name || (locale === "zh" ? "本卦" : "Primary")
  const changedName = result.hex_overview?.changed_hexagram?.name
  const allMoving = movingLines.length === 6
  const keyPassages = brief.key_passages || []
  const sourceCounts = Object.entries(brief.archive_sources?.sources || {})
  const supplementSection = secondarySections[0] || primarySections[0]
  const labels =
    locale === "zh"
      ? {
          title: "断法结构",
          body: "把起卦结果拆成卦象、动爻、变卦与来源层级，先说明为什么这样断，再进入原文。",
          pattern: "卦象格局",
          movement: "爻变诊断",
          sourceDepth: "来源覆盖",
          keyPassages: "重点段落解析",
          keyBody: "这里不是再铺档案，而是标出本次机理真正生效的文本节点。",
          noMoving: "无动爻，以本卦卦辞为主断。",
          moving: "动爻优先，变卦只作后续背景。",
          allMovingQian: "乾卦六爻全动，以用九统摄。",
          allMovingKun: "坤卦六爻全动，以用六统摄。",
          changed: "变卦",
          stable: "无变卦",
          lines: "动爻",
          noLines: "无",
          sources: "来源",
          showSupplement: "显示补充",
          openSource: "打开原文",
        }
      : {
          title: "Cast logic",
          body: "Separate the cast into pattern, moving lines, changed hexagram, and source layers before reading the original text.",
          pattern: "Pattern",
          movement: "Line movement",
          sourceDepth: "Source coverage",
          keyPassages: "Key passage analysis",
          keyBody: "This is not another archive dump; it marks the text nodes that actually drive the mechanics of this reading.",
          noMoving: "No moving lines: the primary hexagram judgment carries the reading.",
          moving: "Moving lines lead; the changed hexagram is secondary context.",
          allMovingQian: "All six Qian lines move: Yong Jiu governs the reading.",
          allMovingKun: "All six Kun lines move: Yong Liu governs the reading.",
          changed: "Changed",
          stable: "No changed hexagram",
          lines: "Moving",
          noLines: "None",
          sources: "Sources",
          showSupplement: "Show supplement",
          openSource: "Open source",
        }
  const decisionRule =
    allMoving && mainName.includes("乾")
      ? labels.allMovingQian
      : allMoving && mainName.includes("坤")
        ? labels.allMovingKun
        : movingLines.length
          ? labels.moving
          : labels.noMoving
  const movingLabel = movingLines.length
    ? movingLines.map((line) => `${line.position}${line.moving_symbol ? ` ${line.moving_symbol}` : ""}`).join(" · ")
    : labels.noLines

  return (
    <section className="rounded-lg border border-border/50 bg-surface p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{labels.title}</h3>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">{labels.body}</p>
        </div>
        {supplementSection ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-fit rounded-md"
            onClick={() => onSourceSelect(sectionSourceIdForDrawer(supplementSection))}
          >
            {labels.showSupplement}
          </Button>
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.pattern}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-foreground">
            {mainName}
            {changedName ? ` → ${changedName}` : ""}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {changedName ? `${labels.changed}: ${changedName}` : labels.stable}
          </p>
        </div>
        <div className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.movement}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-foreground">
            {labels.lines}: {movingLabel}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{decisionRule}</p>
        </div>
        <div className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.sourceDepth}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-foreground">
            {brief.archive_sources?.total_passages ?? brief.source_passages?.length ?? 0} {labels.sources}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {sourceCounts.length
              ? sourceCounts.map(([source, count]) => `${source}: ${count}`).join(" · ")
              : keyPassages.map((passage) => passage.source_label).filter(Boolean).join(" · ")}
          </p>
        </div>
      </div>

      {keyPassages.length ? (
        <div className="mt-4 rounded-md border border-amber-300/45 bg-amber-100/20 p-4 dark:border-amber-200/25 dark:bg-amber-200/10">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-amber-700 dark:text-amber-200">
                {locale === "zh" ? "卦辞解析" : "Textual mechanics"}
              </p>
              <h4 className="mt-1 text-sm font-semibold text-foreground">{labels.keyPassages}</h4>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{labels.keyBody}</p>
            </div>
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-2">
            {keyPassages.map((passage) => (
              <article key={sourceIdForPassage(passage)} className="rounded-md border border-border/50 bg-surface/90 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">{passage.title}</p>
                  <span className="text-xs text-muted-foreground">{passage.source_label || passage.source}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-foreground">{passage.plain_language || compactText(passage.excerpt, 180)}</p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{passage.why_it_matters}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="mt-2 h-auto rounded-md px-0 text-xs font-semibold text-primary hover:bg-transparent hover:text-primary"
                  onClick={() => onSourceSelect(sourceIdForPassage(passage))}
                >
                  {labels.openSource}
                </Button>
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}

function HexResultBlock({ result, brief, onSourceSelect }: { result: SessionPayload; brief: ReadingBrief; onSourceSelect: (sourceId: string) => void }) {
  const { messages, locale } = useI18n()

  const { primarySections, secondarySections } = useMemo(() => {
    const sections = result.hex_sections || []
    const defaultPrimary = decisiveSectionsFromResult(result)
    const defaultPrimaryIds = new Set(defaultPrimary.map((section) => section.id))
    const defaultSecondary = sections.filter((section) => !defaultPrimaryIds.has(section.id))
    const englishSections = sections.filter((section) => section.source === "english_commentary")
    if (!englishSections.length) {
      return { primarySections: defaultPrimary, secondarySections: defaultSecondary }
    }

    const highlightedSlotKeys = new Set(
      defaultPrimary
        .filter((section) => section.source !== "english_commentary")
        .map((section) => section.slot_key)
        .filter((slotKey): slotKey is string => Boolean(slotKey)),
    )

    let englishPrimary = englishSections.filter((section) => {
      if (!section.slot_key) {
        return false
      }
      return highlightedSlotKeys.has(section.slot_key)
    })

    if (!englishPrimary.length) {
      englishPrimary = englishSections.filter((section) => section.section_kind === "top")
    }
    if (!englishPrimary.length) {
      englishPrimary = [englishSections[0]]
    }

    if (locale === "en") {
      const primaryIds = new Set(englishPrimary.map((section) => section.id))
      const secondary = sections.filter((section) => !primaryIds.has(section.id))
      return { primarySections: englishPrimary, secondarySections: secondary }
    }

    const primaryIds = new Set([...defaultPrimary, ...englishPrimary].map((section) => section.id))
    const primary = sections.filter((section) => primaryIds.has(section.id))
    const secondary = sections.filter((section) => !primaryIds.has(section.id))
    return { primarySections: primary, secondarySections: secondary }
  }, [locale, result])

  const hasHiddenSections = secondarySections.length > 0
  const hasPrimary = primarySections.length > 0
  const sessionDetails = result.session_dict as Record<string, unknown> | undefined
  const rawBazi = sessionDetails?.["bazi_output"]
  const rawElements = sessionDetails?.["elements_output"]
  const baziText = typeof rawBazi === "string" ? rawBazi : ""
  const elementsText = typeof rawElements === "string" ? rawElements : ""
  const detailFromPayload = result.bazi_detail as BaziPillar[] | undefined
  const detailFromSession = sessionDetails?.["bazi_detail"] as BaziPillar[] | undefined
  const baziDetail = detailFromPayload ?? detailFromSession ?? []
  const drawerSourceSection = secondarySections[0] || primarySections[0]
  const sourceButtonLabel = locale === "zh" ? "查看原文笔记" : "Review source notebook"

  return (
    <div className="mt-4 space-y-5">
      <HexagramHeader
        overview={result.hex_overview}
        najiaMeta={result.najia_table?.meta}
        sections={result.hex_sections}
        baziText={baziText}
        elementsText={elementsText}
        baziDetail={baziDetail}
      />
      <MechanicsInsightPanel
        result={result}
        brief={brief}
        primarySections={primarySections}
        secondarySections={secondarySections}
        onSourceSelect={onSourceSelect}
      />
      {result.najia_table?.rows?.length ? (
        <div className="space-y-2">
          <p className="kicker">{messages.workspace.results.sixGodLabel}</p>
          <NajiaTableView table={result.najia_table} />
        </div>
      ) : null}
      <div className="surface-soft rounded-lg p-4 text-sm leading-relaxed text-foreground">
        <div className="mb-2 flex items-center justify-between">
          <p className="kicker">{messages.workspace.results.hexLabel}</p>
          {(hasHiddenSections || drawerSourceSection) && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs font-semibold tracking-wide text-foreground hover:text-foreground"
              onClick={() => {
                if (drawerSourceSection) {
                  onSourceSelect(sectionSourceIdForDrawer(drawerSourceSection))
                }
              }}
            >
              {sourceButtonLabel}
            </Button>
          )}
        </div>
        {hasPrimary ? (
          <HexSectionGroup
            title={messages.workspace.results.primarySectionTitle}
            sections={primarySections}
            variant="primary"
          />
        ) : (
          <MarkdownContent content={result.hex_text} />
        )}
      </div>
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
  const { messages } = useI18n()

  if (!sections.length) {
    return null
  }

  const accentClasses =
    variant === "primary"
      ? "border-primary/35 bg-primary/10"
      : "border-border/60 bg-surface-elevated/70"

  return (
    <div className={`rounded-lg border ${accentClasses} p-4`}>
      <p className="mb-3 text-xs uppercase tracking-[0.28rem] text-muted-foreground">{title}</p>
      <div className="space-y-3">
        {sections.map((section) => (
          <div key={section.id} className="rounded-md border border-border/40 bg-surface/90 p-3 text-foreground shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-muted-foreground">
              <span>{section.title}</span>
              <span className="text-[0.65rem] uppercase tracking-widest">
                {section.hexagram_name} ·{" "}
                {section.hexagram_type === "main"
                  ? messages.workspace.results.lineMetaMain
                  : messages.workspace.results.lineMetaChanged}{" "}
                ·{" "}
                {section.source_label ??
                  (section.source === "takashima"
                    ? "高岛易断"
                    : section.source === "english_commentary"
                      ? "English Commentary"
                      : "卦辞库")}
              </span>
            </div>
            <div className="mt-1 text-[0.65rem] uppercase tracking-widest text-muted-foreground/80">
              {section.importance === "primary"
                ? messages.workspace.results.importancePrimary
                : messages.workspace.results.importanceSecondary}
            </div>
            <MarkdownContent content={section.content} className="mt-3" />
          </div>
        ))}
      </div>
    </div>
  )
}
