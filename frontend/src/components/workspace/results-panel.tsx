"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { useI18n } from "@/components/providers/i18n-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { MarkdownContent } from "@/components/ui/markdown-content"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useWorkspaceStore } from "@/lib/store"
import type { BaziPillar, HexSection, SessionPayload } from "@/types/api"

import { ChatPanel } from "./chat-panel"
import { HexagramHeader } from "./hexagram-visual"
import { NajiaTableView } from "./najia-table"

export function ResultsPanel() {
  const { messages } = useI18n()
  const result = useWorkspaceStore((state) => state.result)
  const resetSession = useWorkspaceStore((state) => state.resetSession)
  const setView = useWorkspaceStore((state) => state.setView)

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
      <Card className="surface-card border-border/40 text-foreground">
        <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <CardTitle className="text-lg">{messages.workspace.results.title}</CardTitle>
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
          <Tabs defaultValue="summary">
            <TabsList className="grid w-full grid-cols-3 rounded-full bg-surface-elevated text-foreground">
              <TabsTrigger value="summary">{messages.workspace.results.tabSummary}</TabsTrigger>
              <TabsTrigger value="hex">{messages.workspace.results.tabHex}</TabsTrigger>
              <TabsTrigger value="ai">{messages.workspace.results.tabAi}</TabsTrigger>
            </TabsList>
            <TabsContent value="summary">
              <ResultBlock text={result.summary_text} label={messages.workspace.results.summaryLabel} />
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

function HexResultBlock({ result }: { result: SessionPayload }) {
  const { messages } = useI18n()
  const [showFull, setShowFull] = useState(false)

  const { primarySections, secondarySections } = useMemo(() => {
    const sections = result.hex_sections || []
    const primary = sections.filter((section) => section.visible_by_default)
    const secondary = sections.filter((section) => !section.visible_by_default)
    return { primarySections: primary, secondarySections: secondary }
  }, [result.hex_sections])

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
      <div className="surface-soft rounded-2xl p-4 text-sm leading-relaxed text-foreground">
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

function ResultBlock({ text, label }: { text: string; label: string }) {
  const [expanded, setExpanded] = useState(true)
  return (
    <div className="surface-soft mt-4 rounded-2xl p-4 text-sm leading-relaxed text-foreground">
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
    <div className={`rounded-2xl border ${accentClasses} p-4`}>
      <p className="mb-3 text-xs uppercase tracking-[0.28rem] text-muted-foreground">{title}</p>
      <div className="space-y-3">
        {sections.map((section) => (
          <div key={section.id} className="rounded-xl border border-border/40 bg-surface/80 p-3 text-foreground shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold text-muted-foreground">
              <span>{section.title}</span>
              <span className="text-[0.65rem] uppercase tracking-widest">
                {section.hexagram_name} ·{" "}
                {section.hexagram_type === "main"
                  ? messages.workspace.results.lineMetaMain
                  : messages.workspace.results.lineMetaChanged}{" "}
                · {section.source_label ?? (section.source === "takashima" ? "高岛易断" : "卦辞库")}
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
