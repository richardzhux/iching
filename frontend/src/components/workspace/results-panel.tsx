"use client"

import { useMemo, useState } from "react"
import { useRouter } from "next/navigation"
import { motion, useReducedMotion } from "framer-motion"
import { useI18n } from "@/components/providers/i18n-provider"
import { ArrowDown, ArrowRight, MessageSquare } from "lucide-react"
import { AutumnFrame } from "@/components/autumn/autumn-frame"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { MarkdownContent } from "@/components/ui/markdown-content"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { useWorkspaceStore, type JournalStatus, type ReadingJournalEntry } from "@/lib/store"
import { trackProductEvent } from "@/lib/analytics"
import { HEXAGRAM_LIBRARY } from "@/lib/hexagram-library"
import { localizedHexagramMeaning } from "@/lib/hexagram-copy"
import { chapterTitle } from "@/lib/classical-text"
import { sourceDisplayLabel } from "@/lib/source-labels"
import type {
  BaziPillar,
  HexSection,
  ReadingBrief,
  ReadingBriefKeyPassage,
  ReadingBriefSourcePassage,
  SessionPayload,
} from "@/types/api"

import { ReadingFollowup } from "./reading-followup"
import { HexagramHeader } from "./hexagram-visual"
import { NajiaTableView } from "./najia-table"
import { ReadingClassics } from "./reading-classics"
import { HexagramRelations } from "@/components/hexagram/hexagram-relations"

export function ResultsPanel() {
  const { messages, locale, toLocalePath } = useI18n()
  const router = useRouter()
  const reduceMotion = useReducedMotion()
  const storedResult = useWorkspaceStore((state) => state.result)
  const result = useMemo(() => storedResult ? readingForLocale(storedResult, locale) : null, [storedResult, locale])
  const resetSession = useWorkspaceStore((state) => state.resetSession)
  const journal = useWorkspaceStore((state) => state.journal)
  const updateJournal = useWorkspaceStore((state) => state.updateJournal)
  const [chatOpen, setChatOpen] = useState(true)
  const [mobileChatOpen, setMobileChatOpen] = useState(false)
  const [showChanged, setShowChanged] = useState(false)
  const [selectedLine, setSelectedLine] = useState<number | null>(null)
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null)
  const brief = result ? resolveReadingBrief(result, locale) : null

  const openSourceReader = (sourceId: string) => {
    if (sourceId) {
      trackProductEvent("source_drawer_opened", { source_id_present: true })
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
    <motion.div initial={reduceMotion ? false : { opacity: 0, y: 8 }} animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}>
      <AutumnFrame className="autumn-reading" values={[...result.hex_overview.lines].sort((a, b) => a.position - b.position).map((line) => line.value)} changed={showChanged} showCoins={false} selectedLine={selectedLine} onLineSelect={setSelectedLine}>
        <p className="autumn-eyebrow">{locale === "zh" ? "静观其变" : "Your reading unfolds"}</p>
        <h1 className="autumn-reading-title">{showChanged ? result.hex_overview.changed_hexagram?.name : result.hex_overview.main_hexagram.name}</h1>
        <p className="autumn-intro !mb-0">{showChanged ? result.hex_overview.changed_hexagram?.explanation : result.hex_overview.main_hexagram.explanation}</p>
        {result.hex_overview.changed_hexagram ? <div className="autumn-reading-toggle"><button type="button" aria-pressed={!showChanged} onClick={() => setShowChanged(false)}>{locale === "zh" ? "本卦" : "Present"}</button><ArrowRight size={13} className="mt-1 text-muted-foreground" aria-hidden="true" /><button type="button" aria-pressed={showChanged} onClick={() => setShowChanged(true)}>{locale === "zh" ? "之卦" : "Becoming"}</button></div> : null}
        <div className="autumn-reading-question"><p className="autumn-eyebrow mb-2">{locale === "zh" ? "你问" : "You asked"}</p>{String(result.session_dict?.user_question || result.session_dict?.topic || "")}</div>
        <div className="autumn-hero-conclusion"><p className="autumn-eyebrow">{locale === "zh" ? "一句话结论" : "Conclusion"}</p><p className="mt-2 text-sm leading-7">{brief.headline}</p></div>
        <a href="#reading-meaning" className="autumn-primary mt-6">{locale === "zh" ? "展开解读" : "Explore the meaning"}<ArrowDown size={14} aria-hidden="true" /></a>
        <div className="autumn-reading-line-buttons" aria-label={locale === "zh" ? "选择一爻" : "Explore a line"}>{[...result.hex_overview.lines].sort((a, b) => a.position - b.position).map((line) => <button type="button" key={line.position} aria-label={`${locale === "zh" ? "爻" : "Line"} ${line.position}: ${line.value}${line.is_moving ? (locale === "zh" ? "，动爻" : ", changing") : ""}`} aria-pressed={selectedLine === line.position} onClick={() => setSelectedLine(line.position)}>{line.position}</button>)}</div>
        <p className="autumn-footnote" aria-live="polite">{selectedLine ? `${locale === "zh" ? "所选爻" : "Selected line"} ${selectedLine} · ${result.hex_overview.lines.find((line) => line.position === selectedLine)?.value}` : (locale === "zh" ? "轻触石爻，观其位置。金色为动爻。" : "Touch a stone line to explore. Gold marks change.")}</p>
      </AutumnFrame>
      <div className="reading-workbench" data-chat-open={chatOpen}>
      <Card id="reading-meaning" className="autumn-reading-document text-foreground">
        <CardHeader className="flex flex-col gap-3 border-b border-border/50 pb-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle className="text-lg">{locale === "zh" ? "解卦" : "Reading"}</CardTitle>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => { setChatOpen(true); setMobileChatOpen(true) }}><MessageSquare className="size-4" />{locale === "zh" ? "追问" : "Ask"}</Button>
            <Button variant="outline" size="sm" onClick={() => router.push(toLocalePath("/app"))}>
              {messages.workspace.results.backToSetup}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => { resetSession(); router.push(toLocalePath("/app")) }}>
              {messages.workspace.results.startNew}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <nav className="reading-section-links" aria-label={locale === "zh" ? "解卦章节" : "Reading sections"}>
            <a href="#reading-bottom-line">{locale === "zh" ? "结论与建议" : "Conclusion"}</a>
            <a href="#reading-relations">{locale === "zh" ? "卦象关系" : "Related forms"}</a>
            <a href="#reading-classics">{locale === "zh" ? "经文对读" : "Source texts"}</a>
            <a href="#reading-rationale">{locale === "zh" ? "取用与结构" : "Reading method"}</a>

          </nav>
          <div className="space-y-9 pb-2">
            <HexResultBlock result={result} brief={brief} onSourceSelect={openSourceReader} />

          </div>
          <details className="mt-4 rounded-lg border border-border/50 bg-surface px-4 py-3">
            <summary className="cursor-pointer text-sm font-semibold text-foreground">
              {locale === "zh" ? "应验记录" : "Outcome record"}
            </summary>
            <ReadingJournalPanel
              sessionId={result.session_id}
              entry={journal[result.session_id]}
              onChange={(patch) => updateJournal(result.session_id, patch)}
            />
          </details>
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
      <ReadingFollowup session={result} prompts={brief.followup_prompts} desktopOpen={chatOpen} onDesktopOpenChange={setChatOpen} mobileOpen={mobileChatOpen} onMobileOpenChange={setMobileChatOpen} />
      </div>
      <button type="button" className="reading-chat-launcher" onClick={() => { setChatOpen(true); setMobileChatOpen(true); document.getElementById("reading-meaning")?.scrollIntoView({ block: "start", behavior: "smooth" }) }}><MessageSquare size={17} />{locale === "zh" ? "追问" : "Ask"}</button>
    </motion.div>
  )
}

function readingForLocale(result: SessionPayload, locale: "zh" | "en"): SessionPayload {
  const matches = (source?: string) => locale === "en" ? source === "english_commentary" : source !== "english_commentary"
  const sections = (result.hex_sections ?? []).filter((section) => matches(section.source))
  const savedBrief = result.reading_brief
  const brief = savedBrief ? { ...savedBrief,
    source_passages: savedBrief.source_passages?.filter((passage) => matches(passage.source)),
    key_passages: savedBrief.key_passages?.filter((passage) => matches(passage.source)),
  } : undefined
  const ordered = [...result.hex_overview.lines].sort((a, b) => a.position - b.position)
  const findEntry = (changed: boolean) => HEXAGRAM_LIBRARY.find((entry) => entry.binary === ordered.map((line) => (changed ? line.changed_value : line.value) % 2 ? "1" : "0").join(""))
  const main = findEntry(false)
  const changed = result.hex_overview.changed_hexagram ? findEntry(true) : undefined
  const localHex = (entry: typeof main) => ({ name: (locale === "zh" ? entry?.nameZh : entry?.titleEn) ?? (locale === "zh" ? "卦象" : "Hexagram"), explanation: entry ? localizedHexagramMeaning(entry, locale) : "" })
  const overview = { ...result.hex_overview, main_hexagram: localHex(main), changed_hexagram: changed ? localHex(changed) : null }
  if (locale === "zh") return { ...result, hex_overview: overview, hex_sections: sections, reading_brief: brief }
  const title = (section: { line_key?: string | null }) => chapterTitle(section.line_key && section.line_key !== "all" ? Number(section.line_key) : null, section.line_key === "all" ? (main?.number === 1 ? "yong_jiu" : "yong_liu") : null, locale)
  const englishName = (name?: string) => HEXAGRAM_LIBRARY.find((entry) => entry.nameZh === name || entry.shortNameZh === name)?.titleEn ?? name ?? "Hexagram"
  const hasChinese = (text?: string) => /[\u3400-\u9fff]/.test(text ?? "")
  const moving = ordered.filter((line) => line.is_moving).map((line) => line.position)
  const plain = moving.length ? `Changing lines: ${moving.join(", ")}. Read these lines alongside the primary judgment.` : "No moving lines. Read the primary judgment for the situation as it stands."
  const englishBrief = brief ? { ...brief,
    headline: hasChinese(brief.headline) ? `${main?.titleEn ?? "Primary hexagram"}${changed ? ` → ${changed.titleEn}` : ""}` : brief.headline,
    plain_language: hasChinese(brief.plain_language) ? plain : brief.plain_language,
    direction: brief.direction && !hasChinese(brief.direction.summary) ? brief.direction : undefined,
    timing: brief.timing.filter((item) => !hasChinese(`${item.window} ${item.condition}`)),
    actions: brief.actions.filter((item) => !hasChinese(`${item.action} ${item.cadence} ${item.signal}`)),
    followup_prompts: brief.followup_prompts.filter((prompt) => !hasChinese(prompt)),
    source_passages: brief.source_passages?.map((passage) => ({ ...passage, title: title(passage), hexagram_name: englishName(passage.hexagram_name), citation: `${sourceDisplayLabel(passage.source, locale)} · ${title(passage)}` })),
    key_passages: brief.key_passages?.map((passage) => ({ ...passage, title: title(passage), hexagram_name: englishName(passage.hexagram_name), citation: `${sourceDisplayLabel(passage.source, locale)} · ${title(passage)}` })),
  } : undefined
  return { ...result, hex_overview: overview,
    hex_sections: sections.map((section) => ({ ...section, title: title(section), hexagram_name: (section.hexagram_type === "main" ? main : changed)?.titleEn ?? "Hexagram" })), reading_brief: englishBrief }
}

function resolveReadingBrief(result: SessionPayload, locale: "en" | "zh"): ReadingBrief {
  const fallbackSourcePassages = sourcePassagesFromSections(result.hex_sections || [], locale)
  if (result.reading_brief?.headline) {
    const sourcePassages = result.reading_brief.source_passages?.length
      ? withResolvedSourceIds(result.reading_brief.source_passages, locale)
      : fallbackSourcePassages
    const keyPassages = result.reading_brief.key_passages?.length
      ? withResolvedSourceIds(result.reading_brief.key_passages, locale)
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

function withResolvedSourceIds<T extends ReadingBriefSourcePassage>(passages: T[], locale: "en" | "zh"): T[] {
  return passages.map((passage) => {
    const sourceLabel = sourceDisplayLabel(passage.source, locale)
    const unverified = sourceLabel === "来源待核" || sourceLabel === "Source unverified"
    return {
      ...passage,
      source_id: sourceIdForPassage(passage),
      source_label: sourceLabel,
      citation: unverified
        ? [sourceLabel, passage.hexagram_name, passage.title].filter(Boolean).join("｜")
        : passage.citation,
    }
  })
}

function sectionSourceIdForDrawer(section: HexSection) {
  if (section.source_id) {
    return section.source_id
  }
  return `${section.slot_key || section.title}::${section.source || "unknown"}`
}

function sourcePassagesFromSections(sections: HexSection[], locale: "en" | "zh"): ReadingBriefSourcePassage[] {
  return sections
    .filter((section) => section.content)
    .map((section) => {
      const source = section.source || "unknown"
      const slotKey = section.slot_key || `${section.hexagram_name}:${section.section_kind}`
      const sourceLabel = sourceDisplayLabel(source, locale)
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
    ((allValues.every((value) => value === 9) && (mainName.includes("乾") || mainName === "The Creative")) ||
      (allValues.every((value) => value === 6) && (mainName.includes("坤") || mainName === "The Receptive")))
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
  return sourcePassagesFromSections(decisiveSectionsFromResult(result), locale)
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

function sourceLayerLabel(passage: ReadingBriefSourcePassage, locale: "en" | "zh") {
  const source = passage.source?.toLowerCase() ?? ""
  if (source.includes("takashima")) return locale === "zh" ? "注释层" : "Commentarial layer"
  if (source.includes("english")) return locale === "zh" ? "英文评注层" : "English commentary layer"
  if (source.includes("symbolic")) return locale === "zh" ? "卦象结构层" : "Structural inference layer"
  if (source.includes("guaci")) return locale === "zh" ? "经典原文层" : "Classical text layer"
  return locale === "zh" ? "来源待核" : "Source unverified"
}

function whySelectedForSource(passage: ReadingBriefSourcePassage, locale: "en" | "zh") {
  if (passage.importance === "primary" || passage.visible_by_default) {
    return locale === "zh"
      ? "这段属于本次阅读默认取用的关键证据，因此优先展示。"
      : "This passage is selected as default evidence for this reading, so it is shown first."
  }
  if (passage.section_kind === "line") {
    return locale === "zh"
      ? "这段对应爻位资料，用来检查动爻或相关爻位的解释边界。"
      : "This passage belongs to line material and helps inspect the active or related line."
  }
  if (passage.section_kind === "top") {
    return locale === "zh"
      ? "这段对应整卦资料，用来说明本卦或变卦的总体语境。"
      : "This passage belongs to whole-hexagram material and frames the primary or changed context."
  }
  return locale === "zh"
    ? "这段补充了当前判断，可与关键原文交叉核对。"
    : "This passage supports the current judgment and can be checked against the decisive text."
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
          title: "应验记录",
          body: "记录后来发生了什么，以及这次断卦哪些地方真正应验。",
          status: "状态",
          pin: "固定",
          pinned: "已固定",
          revisit: "重访日期",
          outcome: "实际发生了什么？",
          placeholder: "记录后来发生的事、哪个爻最准确、当时误读了什么，或仍在等待什么信号。",
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
                {locale === "zh" ? ({ open: "待观察", watching: "应验中", resolved: "已结束" } as const)[status] : status}
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
    locale,
  )
  const selected = activeSourceId
    ? sourcePassages.find((passage) => sourceIdForPassage(passage) === activeSourceId)
    : undefined
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
          body: "在右侧查看本次取用的具体来源块，保持断卦页简洁。",
	          sameSlot: "同一爻位依据",
	          otherSlots: "其他相关依据",
	          citation: "引用",
	          layer: "来源分类",
	          why: "为什么选它",
	          content: "来源内容",
	          empty: "未找到请求的来源段落；请返回依据列表重新选择。",
	        }
	      : {
          title: "Source notebook",
          body: "Review the exact source chunks for this reading without expanding the whole result page.",
	          sameSlot: "Same-line evidence",
	          otherSlots: "Other relevant evidence",
	          citation: "Citation",
	          layer: "Source class",
	          why: "Why selected",
	          content: "Source content",
	          empty: "The requested source passage was not found. Return to the evidence list and choose another source.",
	        }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="h-[100dvh] !w-full gap-0 border-border bg-background p-0 sm:!max-w-2xl lg:!max-w-3xl"
      >
        <SheetHeader className="border-b border-border/50 p-5 pr-12">
          <SheetTitle>{labels.title}</SheetTitle>
          <SheetDescription>{selected?.citation || labels.body}</SheetDescription>
        </SheetHeader>

        {selected ? (
          <div className="grid min-h-0 flex-1 overflow-y-auto lg:grid-cols-[16rem_1fr] lg:overflow-hidden">
            <aside className="max-h-56 overflow-y-auto border-b border-border/50 p-3 lg:max-h-none lg:border-b-0 lg:border-r">
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

            <main className="min-h-0 p-5 lg:overflow-y-auto">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">
                    {selected.source_label || selected.source}
                  </p>
                  <h3 className="mt-2 text-xl font-semibold leading-8 text-foreground">{selected.title}</h3>
                </div>
	              </div>
	              <dl className="mt-4 grid divide-y divide-border/50 border-y border-border/50 text-xs sm:grid-cols-2 sm:divide-x sm:divide-y-0">
	                <div className="py-3 sm:px-3 sm:first:pl-0">
	                  <dt className="text-muted-foreground">{labels.layer}</dt>
	                  <dd className="mt-1 font-semibold text-foreground">{sourceLayerLabel(selected, locale)}</dd>
	                </div>
	                <div className="py-3 sm:px-3">
	                  <dt className="text-muted-foreground">{labels.citation}</dt>
	                  <dd className="mt-1 font-semibold text-foreground">{selected.citation || selected.source_label}</dd>
	                </div>
	              </dl>
	              <div className="imperial-highlight-card mt-4 rounded-md p-4">
	                <p className="imperial-text text-xs font-semibold uppercase tracking-[0.18rem]">
	                  {labels.why}
	                </p>
	                <p className="mt-2 text-sm leading-6 text-foreground">{whySelectedForSource(selected, locale)}</p>
	              </div>
	              <div className="mt-4 border-t border-border/50 pt-4">
	                <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18rem] text-muted-foreground">
	                  {labels.content}
	                </p>
	                <MarkdownContent content={passageDisplayText(selected)} />
	              </div>
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
  const sourceLabels = Array.from(new Set(
    [...(brief.source_passages || []), ...keyPassages]
      .map((passage) => passage.source_label)
      .filter(Boolean),
  ))
  const supplementSection = secondarySections[0] || primarySections[0]
  const labels =
    locale === "zh"
      ? {
          title: "断法结构",
          body: "把起卦结果拆成卦象、动爻、变卦与来源层级，先说明为什么这样断，再进入原文。",
          pattern: "卦象格局",
          movement: "爻变诊断",
	          sourceDepth: "本次依据",
	          sourceNote: "可打开原文逐段核对来源与取用理由。",
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
	          sourceDepth: "Evidence used",
	          sourceNote: "Open the source notes to verify each passage and why it was selected.",
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
    allMoving && (mainName.includes("乾") || mainName === "The Creative")
      ? labels.allMovingQian
      : allMoving && (mainName.includes("坤") || mainName === "The Receptive")
        ? labels.allMovingKun
        : movingLines.length
          ? labels.moving
          : labels.noMoving
  const movingLabel = movingLines.length
    ? movingLines.map((line) => `${line.position}${line.moving_symbol ? ` ${line.moving_symbol}` : ""}`).join(" · ")
    : labels.noLines

  return (
    <section className="border-y border-border/60 py-5">
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

	      <div className="mt-4 grid divide-y divide-border/50 border-y border-border/50 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
	        <div className="py-4 lg:px-4 lg:first:pl-0">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.pattern}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-foreground">
            {mainName}
            {changedName ? ` → ${changedName}` : ""}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {changedName ? `${labels.changed}: ${changedName}` : labels.stable}
          </p>
        </div>
	        <div className="py-4 lg:px-4">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.movement}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-foreground">
            {labels.lines}: {movingLabel}
          </p>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">{decisionRule}</p>
        </div>
	        <div className="py-4 lg:px-4 lg:last:pr-0">
          <p className="text-[0.65rem] font-semibold uppercase tracking-[0.18rem] text-muted-foreground">{labels.sourceDepth}</p>
          <p className="mt-2 text-sm font-semibold leading-6 text-foreground">
	            {sourceLabels.join(" · ") || labels.sources}
	          </p>
	          <p className="mt-2 text-xs leading-5 text-muted-foreground">{labels.sourceNote}</p>
        </div>
      </div>

    </section>
  )
}

function readingDirectionLabel(brief: ReadingBrief, locale: "en" | "zh") {
  const kind = brief.direction?.kind ?? (brief.stance === "stable" ? "observe" : "adjust")
  const labels = locale === "zh"
    ? { advance: "推进", wait: "等待", adjust: "调整", stop: "止步", observe: "观察" }
    : { advance: "Advance", wait: "Wait", adjust: "Adjust", stop: "Stop", observe: "Observe" }
  return labels[kind]
}

function ReadingDecisionSummary({ brief }: { brief: ReadingBrief }) {
  const { locale } = useI18n()
  const timing = brief.timing[0]
  const action = brief.actions[0]
  const directionSummary = brief.direction?.summary || brief.plain_language
  const rows = [
    {
      label: locale === "zh" ? "方向" : "Direction",
      value: `${readingDirectionLabel(brief, locale)}${directionSummary ? ` · ${directionSummary}` : ""}`,
    },
    timing ? {
      label: locale === "zh" ? "时机" : "Timing",
      value: `${timing.window}${timing.condition ? ` · ${timing.condition}` : ""}`,
    } : null,
    action ? {
      label: locale === "zh" ? "下一步" : "Next step",
      value: action.action,
    } : null,
  ].filter((row): row is { label: string; value: string } => Boolean(row?.value))

  return (
    <section className="border-y border-border/60 py-6" aria-labelledby="reading-bottom-line">
      <p className="text-sm font-semibold text-primary">{locale === "zh" ? "一句话结论" : "Bottom line"}</p>
      <h2 id="reading-bottom-line" className="mt-3 max-w-4xl text-balance text-2xl font-semibold leading-9 text-foreground sm:text-3xl">
        {brief.headline}
      </h2>
      {brief.plain_language && brief.plain_language !== directionSummary ? (
        <p className="mt-3 max-w-4xl text-base leading-7 text-foreground/75">{brief.plain_language}</p>
      ) : null}
      <dl className="mt-6 divide-y divide-border/55 border-y border-border/55">
        {rows.map((row) => (
          <div key={row.label} className="grid gap-1 py-4 sm:grid-cols-[7rem_1fr] sm:gap-5">
            <dt className="font-semibold text-primary">{row.label}</dt>
            <dd className="text-sm leading-6 text-foreground/85 sm:text-base">{row.value}</dd>
          </div>
        ))}
      </dl>
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

  const sessionDetails = result.session_dict as Record<string, unknown> | undefined
  const castingMode = (sessionDetails?.casting as { meihua_mode?: string } | undefined)?.meihua_mode
  const rawBazi = sessionDetails?.["bazi_output"]
  const rawElements = sessionDetails?.["elements_output"]
  const baziText = typeof rawBazi === "string" ? rawBazi : ""
  const elementsText = typeof rawElements === "string" ? rawElements : ""
  const detailFromPayload = result.bazi_detail as BaziPillar[] | undefined
  const detailFromSession = sessionDetails?.["bazi_detail"] as BaziPillar[] | undefined
  const baziDetail = detailFromPayload ?? detailFromSession ?? []

  return (
    <div className="mt-4 space-y-5">
      <ReadingDecisionSummary brief={brief} />
      <HexagramHeader
        overview={result.hex_overview}
        najiaMeta={locale === "zh" ? result.najia_table?.meta : undefined}
        sections={result.hex_sections}
        baziText={baziText}
        elementsText={elementsText}
        baziDetail={baziDetail}
        compact
      />
      {castingMode && <p className="text-xs text-muted-foreground">{locale === "zh" ? "梅花取数：" : "Plum blossom formula: "}{castingMode === "original" ? (locale === "zh" ? "项目原始分钟法" : "Original project minute formula") : (locale === "zh" ? "传统农历时辰法" : "Traditional lunar / hour branch")}</p>}
      <div id="reading-relations" className="scroll-mt-24"><HexagramRelations values={[...result.hex_overview.lines].sort((a, b) => a.position - b.position).map((line) => line.value)} locale={locale} /></div>
      <ReadingClassics result={result} locale={locale} />
      <details id="reading-rationale" className="group scroll-mt-24 border-b border-border/60 pb-5">
        <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-4 py-3 text-base font-semibold text-foreground marker:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span>{locale === "zh" ? "为什么这样断" : "Why this reading"}</span>
          <span className="ml-auto text-sm text-primary group-open:hidden">{locale === "zh" ? "展开" : "Open"}</span>
          <span className="ml-auto hidden text-sm text-primary group-open:inline">{locale === "zh" ? "收起" : "Close"}</span>
        </summary>
        <div className="space-y-6 pt-2">
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

        </div>
      </details>
    </div>
  )
}
