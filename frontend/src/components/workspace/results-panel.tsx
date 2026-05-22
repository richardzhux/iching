"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MarkdownContent } from "@/components/ui/markdown-content"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useWorkspaceStore } from "@/lib/store"
import type { BaziPillar, HexSection, ReadingBrief, ReadingBriefSourcePassage, SessionPayload } from "@/types/api"

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

  if (!result) {
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
              <TabsTrigger value="summary">{locale === "zh" ? "判断简报" : "Brief"}</TabsTrigger>
              <TabsTrigger value="hex">{messages.workspace.results.tabHex}</TabsTrigger>
              <TabsTrigger value="ai">{messages.workspace.results.tabAi}</TabsTrigger>
            </TabsList>
            <TabsContent value="summary">
              <ReadingBriefPanel
                brief={resolveReadingBrief(result, locale)}
                onPrompt={(prompt) => {
                  setPendingChatPrompt(prompt)
                  setResultsTab("ai")
                }}
              />
            </TabsContent>
            <TabsContent value="hex">
              <HexResultBlock result={result} />
            </TabsContent>
            <TabsContent value="ai">
              <ChatPanel session={result} />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function resolveReadingBrief(result: SessionPayload, locale: "en" | "zh"): ReadingBrief {
  if (result.reading_brief?.headline) {
    return result.reading_brief
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
    source_passages: sourcePassagesFromSections(result.hex_sections || []),
    archive_sources: archiveCoverageFromPassages(sourcePassagesFromSections(result.hex_sections || [])),
    personal_context: {
      status: "reserved",
      current_scope: "casting_time_bazi_only",
      note: locale === "zh"
        ? "本阶段只使用起卦时间八字；出生资料与大运流年会作为后续独立个人画像层接入。"
        : "This phase only uses casting-time BaZi; natal profile and fortune-cycle data are reserved for a future personal lens.",
    },
  }
}

function sourcePassagesFromSections(sections: HexSection[]): ReadingBriefSourcePassage[] {
  return sections
    .filter((section) => section.content)
    .map((section) => {
      const source = section.source || "unknown"
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
        slot_key: section.slot_key || `${section.hexagram_name}:${section.section_kind}`,
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
  onPrompt,
}: {
  brief: ReadingBrief
  onPrompt: (prompt: string) => void
}) {
  const { locale } = useI18n()
  const labels =
    locale === "zh"
      ? {
          stance: "判断状态",
          evidence: "证据短链",
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
          timing: "Timing and conditions",
          actions: "Actions",
          risks: "Risk signals",
          followups: "Continue with",
          confidence: "Confidence",
          condition: "Condition",
          cadence: "Cadence",
          signal: "Signal",
        }

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

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg border border-border/50 bg-surface p-5">
          <h3 className="text-sm font-semibold text-foreground">{labels.evidence}</h3>
          <div className="mt-4 space-y-3">
            {brief.evidence.map((item, index) => (
              <article key={`${item.basis}-${index}`} className="rounded-md border border-border/50 bg-surface-elevated/80 p-4">
                <p className="text-sm font-semibold text-foreground">{item.conclusion}</p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">{item.basis}</p>
                <p className="mt-2 text-sm leading-6 text-foreground">{item.plain}</p>
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
    </div>
  )
}

function HexResultBlock({ result }: { result: SessionPayload }) {
  const { messages, locale } = useI18n()
  const [showFull, setShowFull] = useState(false)

  const { primarySections, secondarySections } = useMemo(() => {
    const sections = result.hex_sections || []
    const defaultPrimary = sections.filter((section) => section.visible_by_default)
    const defaultSecondary = sections.filter((section) => !section.visible_by_default)
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
  }, [locale, result.hex_sections])

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

  return (
    <div className="mt-4 space-y-5">
      <HexagramHeader
        overview={result.hex_overview}
        najiaMeta={result.najia_table?.meta}
        baziText={baziText}
        elementsText={elementsText}
        baziDetail={baziDetail}
      />
      {result.najia_table?.rows?.length ? (
        <div className="space-y-2">
          <p className="kicker">{messages.workspace.results.sixGodLabel}</p>
          <NajiaTableView table={result.najia_table} />
        </div>
      ) : null}
      <ArchiveComparisonPanel result={result} />
      <div className="surface-soft rounded-lg p-4 text-sm leading-relaxed text-foreground">
        <div className="mb-2 flex items-center justify-between">
          <p className="kicker">{messages.workspace.results.hexLabel}</p>
          {hasHiddenSections && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs font-semibold tracking-wide text-foreground hover:text-foreground"
              onClick={() => setShowFull((value) => !value)}
              aria-expanded={showFull}
            >
              {showFull ? messages.workspace.results.hideMore : messages.workspace.results.showMore}
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
        {showFull && hasHiddenSections && (
          <div className="mt-6">
            <HexSectionGroup
              title={messages.workspace.results.secondarySectionTitle}
              sections={secondarySections}
              variant="secondary"
            />
          </div>
        )}
      </div>
    </div>
  )
}

function ArchiveComparisonPanel({ result }: { result: SessionPayload }) {
  const { locale } = useI18n()
  const [sourceFilter, setSourceFilter] = useState("all")
  const brief = resolveReadingBrief(result, locale)
  const passages = brief.source_passages?.length
    ? brief.source_passages
    : sourcePassagesFromSections(result.hex_sections || [])
  const sources = Array.from(
    passages.reduce<Map<string, string>>((map, passage) => {
      map.set(passage.source, passage.source_label || passage.source)
      return map
    }, new Map<string, string>()),
  )
  const visiblePassages =
    sourceFilter === "all" ? passages : passages.filter((passage) => passage.source === sourceFilter)
  const grouped = visiblePassages.reduce<Record<string, ReadingBriefSourcePassage[]>>((acc, passage) => {
    const key = passage.slot_key || passage.title
    acc[key] = [...(acc[key] ?? []), passage]
    return acc
  }, {})
  const labels =
    locale === "zh"
      ? {
          title: "经典档案对照",
          body: "按卦辞、动爻与来源比较本次阅读的证据，避免只看 AI 概要。",
          all: "全部来源",
          passages: "段落",
          slots: "槽位",
          primary: "主证据",
          citation: "引用",
          future: "个人运势画像预留",
        }
      : {
          title: "Classical Archive",
          body: "Compare this reading by slot and source so the evidence is inspectable beyond the AI summary.",
          all: "All sources",
          passages: "passages",
          slots: "slots",
          primary: "Core evidence",
          citation: "Citation",
          future: "Personal fortune lens reserved",
        }

  return (
    <section className="rounded-lg border border-border/50 bg-surface p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{labels.title}</h3>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{labels.body}</p>
        </div>
        <div className="text-xs text-muted-foreground">
          {passages.length} {labels.passages} · {Object.keys(grouped).length} {labels.slots}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Button
          type="button"
          variant={sourceFilter === "all" ? "default" : "outline"}
          size="sm"
          className="rounded-md"
          onClick={() => setSourceFilter("all")}
        >
          {labels.all}
        </Button>
        {sources.map(([source, label]) => (
          <Button
            key={source}
            type="button"
            variant={sourceFilter === source ? "default" : "outline"}
            size="sm"
            className="rounded-md"
            onClick={() => setSourceFilter(source)}
          >
            {label}
          </Button>
        ))}
      </div>

      <div className="mt-4 space-y-4">
        {Object.entries(grouped).map(([slotKey, slotPassages]) => (
          <div key={slotKey} className="rounded-md border border-border/50 bg-surface-elevated/70 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{slotKey}</p>
              {slotPassages.some((passage) => passage.visible_by_default) && (
                <span className="rounded-md border border-primary/40 bg-primary/10 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-wider text-primary">
                  {labels.primary}
                </span>
              )}
            </div>
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {slotPassages.map((passage, index) => (
                <article key={`${passage.source}-${passage.title}-${index}`} className="rounded-md border border-border/50 bg-surface p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">{passage.title}</p>
                    <span className="text-xs text-muted-foreground">{passage.source_label}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-foreground">{passage.content}</p>
                  <p className="mt-3 text-xs text-muted-foreground">
                    {labels.citation}: {passage.citation}
                  </p>
                </article>
              ))}
            </div>
          </div>
        ))}
      </div>

      {brief.personal_context?.status === "reserved" && (
        <div className="mt-4 rounded-md border border-dashed border-border/70 bg-surface-elevated/60 p-3 text-xs leading-5 text-muted-foreground">
          <span className="font-semibold text-foreground">{labels.future}: </span>
          {brief.personal_context.note}
        </div>
      )}
    </section>
  )
}

function ResultBlock({ text, label }: { text: string; label: string }) {
  const [expanded, setExpanded] = useState(true)
  return (
    <div className="surface-soft mt-4 rounded-lg p-4 text-sm leading-relaxed text-foreground">
      <div className="mb-2 flex items-center justify-between">
        <p className="kicker">{label}</p>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs font-semibold tracking-wide text-foreground hover:text-foreground"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
        >
          {expanded ? "−" : "+"}
        </Button>
      </div>
      {expanded && <MarkdownContent content={text} />}
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
