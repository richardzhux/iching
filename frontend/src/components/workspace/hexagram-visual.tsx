"use client"

import { useMemo, useState } from "react"
import { ArrowRight } from "lucide-react"

import { useI18n } from "@/components/providers/i18n-provider"
import { Card, CardContent } from "@/components/ui/card"
import { sourceDisplayLabel } from "@/lib/source-labels"
import { cn } from "@/lib/utils"
import type { BaziPillar, HexLineInfo, HexOverview, HexSection } from "@/types/api"

import type { NajiaTable } from "@/types/api"

type HexagramHeaderProps = {
  overview?: HexOverview
  najiaMeta?: NajiaTable["meta"]
  sections?: HexSection[]
  baziText?: string
  elementsText?: string
  baziDetail?: BaziPillar[]
}

const POLARITY_COLORS: Record<string, string> = {
  阳: "#FF5C5C",
  阴: "#87CEEB",
}

function getPolarityColor(polarity?: string) {
  if (!polarity) return undefined
  return POLARITY_COLORS[polarity] || undefined
}

function PillarInlineList({ detail }: { detail: BaziPillar[] }) {
  return (
    <span className="text-lg font-semibold text-foreground">
      {detail.map((pillar, index) => {
        const stemElement = pillar.stem.element || pillar.stem.value
        const branchElement = pillar.branch.element || pillar.branch.value
        const stemColor = getPolarityColor(pillar.stem.polarity)
        const branchColor = getPolarityColor(pillar.branch.polarity)
        return (
          <span key={`${pillar.label}-${pillar.stem.value}-${pillar.branch.value}`} className="inline-flex">
            <span style={{ color: stemColor }}>{stemElement}</span>
            <span style={{ color: branchColor }}>{branchElement}</span>
            <span>{pillar.label}</span>
            {index < detail.length - 1 && <span>&nbsp;</span>}
          </span>
        )
      })}
    </span>
  )
}

function InfoRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
      <span className="text-sm font-medium text-muted-foreground sm:w-24">{label}</span>
      <div className="text-lg font-semibold text-foreground">{children}</div>
    </div>
  )
}

export function HexagramHeader({
  overview,
  najiaMeta,
  sections = [],
  baziText,
  elementsText,
  baziDetail = [],
}: HexagramHeaderProps) {
  const { messages } = useI18n()
  if (!overview) {
    return null
  }

  const lineSignature = overview.lines.map((line) => `${line.position}:${line.value}:${line.is_moving}`).join("|")

  return (
    <Card className="surface-card border-border/40">
      <CardContent className="p-5">
        <p className="kicker">{messages.workspace.results.overviewLabel}</p>
        {(baziText || elementsText || baziDetail.length) && (
          <div className="surface-soft mt-3 grid gap-4 rounded-lg p-4">
            {baziText && (
              <InfoRow label={messages.workspace.results.baziTimeLabel}>
                <span>{baziText}</span>
              </InfoRow>
            )}
            {baziDetail.length ? (
              <InfoRow label={messages.workspace.results.elementLabel}>
                <PillarInlineList detail={baziDetail} />
              </InfoRow>
            ) : (
              elementsText && (
                <InfoRow label={messages.workspace.results.elementLabel}>
                  <span>{elementsText}</span>
                </InfoRow>
              )
            )}
          </div>
        )}
        <div className={cn("mt-4 flex flex-col gap-4 lg:grid lg:items-center", overview.changed_hexagram ? "lg:grid-cols-[1fr_auto_1fr]" : "lg:grid-cols-1")}>
          <HexagramCard
            key={`main-${overview.main_hexagram?.name || "unknown"}-${lineSignature}`}
            label={messages.workspace.results.mainHexLabel}
            name={overview.main_hexagram?.name}
            explanation={overview.main_hexagram?.explanation}
            tag={najiaMeta?.main?.type}
            lines={overview.lines}
            sections={sections}
            hexagramType="main"
          />
          {overview.changed_hexagram && (
            <>
              <div className="hidden lg:flex items-center justify-center">
                <ArrowRight className="h-7 w-7 text-primary" />
              </div>
              <HexagramCard
                key={`changed-${overview.changed_hexagram.name || "unknown"}-${lineSignature}`}
                label={messages.workspace.results.changedHexLabel}
                name={overview.changed_hexagram.name}
                explanation={overview.changed_hexagram.explanation}
                tag={najiaMeta?.changed?.type}
                lines={overview.lines}
                sections={sections}
                hexagramType="changed"
                accent
              />
            </>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

type HexagramCardProps = {
  label: string
  name?: string
  explanation?: string
  tag?: string | null
  lines?: HexLineInfo[]
  sections?: HexSection[]
  hexagramType: "main" | "changed"
  accent?: boolean
}

function HexagramCard({
  label,
  name,
  explanation,
  tag,
  lines = [],
  sections = [],
  hexagramType,
  accent = false,
}: HexagramCardProps) {
  const orderedLines = useMemo(
    () => [...lines].sort((a, b) => b.position - a.position),
    [lines],
  )
  const defaultActive = orderedLines.find((line) => line.is_moving)?.position ?? orderedLines[0]?.position ?? null
  const [activePosition, setActivePosition] = useState<number | null>(defaultActive)
  const activeLine = orderedLines.find((line) => line.position === activePosition) || orderedLines[0]
  const activeSection = activeLine ? findLineSection(sections, hexagramType, activeLine, name) : undefined

  return (
    <div
      className={cn(
        "flex-1 rounded-lg border p-4",
        accent
          ? "imperial-highlight-panel"
          : "border-border/30 bg-foreground/[0.03] dark:border-primary/15 dark:bg-primary/5"
      )}
    >
      <p className="text-[0.65rem] uppercase tracking-[0.4rem] text-muted-foreground">{label}</p>
      <div className="mt-3 grid gap-4 sm:grid-cols-[minmax(7rem,9rem)_1fr] sm:items-start">
        <InteractiveHexagramLines
          orderedLines={orderedLines}
          activePosition={activeLine?.position ?? null}
          onActivePositionChange={setActivePosition}
          hexagramType={hexagramType}
          accent={accent}
        />
        <div>
          <p className="text-lg font-semibold text-foreground">{name || "—"}</p>
          {tag && (
            <span className="imperial-chip mt-1 inline-flex rounded-md px-3 py-0.5 text-xs font-semibold">
              {tag}
            </span>
          )}
          {explanation && <p className="mt-2 text-sm leading-6 text-muted-foreground">{explanation}</p>}
        </div>
      </div>
      <HexagramSourcePreview section={activeSection} />
    </div>
  )
}

function InteractiveHexagramLines({
  orderedLines,
  activePosition,
  onActivePositionChange,
  hexagramType,
  accent,
}: {
  orderedLines: HexLineInfo[]
  activePosition: number | null
  onActivePositionChange: (position: number) => void
  hexagramType: "main" | "changed"
  accent: boolean
}) {
  const { locale } = useI18n()
  const activeLine = orderedLines.find((line) => line.position === activePosition) || orderedLines[0]

  if (!orderedLines.length) {
    return <div className="h-32 rounded-md border border-border/40 bg-surface/60" />
  }

  return (
    <div className="min-w-28">
      <div className="grid gap-1.5" aria-label={locale === "zh" ? "六爻图" : "Hexagram lines"}>
        {orderedLines.map((line) => {
          const active = line.position === activeLine?.position
          const lineType = hexagramType === "changed" ? line.changed_line_type || line.changed_type : line.line_type
          return (
            <button
              key={`${hexagramType}-${line.position}`}
              type="button"
              className={cn(
                "group grid h-7 grid-cols-[1fr_auto] items-center gap-2 rounded-md border px-1.5 transition-colors",
                active
                  ? "border-primary/50 bg-primary/10"
                  : "border-transparent bg-transparent hover:border-border/60 hover:bg-surface/70",
              )}
              onMouseEnter={() => onActivePositionChange(line.position)}
              onFocus={() => onActivePositionChange(line.position)}
              aria-label={
                locale === "zh"
                  ? `第${line.position}爻，${lineType === "yang" ? "阳爻" : "阴爻"}`
                  : `Line ${line.position}, ${lineType}`
              }
            >
              <LineSvg type={lineType} moving={line.is_moving} active={active} accent={accent} />
              {line.is_moving ? (
                <span className="imperial-text w-4 text-center text-xs font-semibold">
                  {line.moving_symbol || (hexagramType === "changed" ? "↻" : "•")}
                </span>
              ) : (
                <span className="w-4 text-center text-[0.6rem] text-muted-foreground">{line.position}</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function HexagramSourcePreview({ section }: { section?: HexSection }) {
  const { locale } = useI18n()
  const sourcePreviewSection = "mt-4 rounded-md border border-border/40 bg-surface/80 p-4"

  if (!section) {
    return null
  }

  return (
    <div className={sourcePreviewSection}>
      <p className="text-[0.65rem] font-semibold uppercase tracking-[0.16rem] text-muted-foreground">
        {sourceDisplayLabel(section.source, locale)}
      </p>
      <p className="mt-1 text-sm font-semibold leading-6 text-foreground">{section.title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{compactSnippet(section.content, 220)}</p>
    </div>
  )
}

function LineSvg({
  type,
  moving,
  active,
  accent,
}: {
  type: "yang" | "yin"
  moving: boolean
  active: boolean
  accent: boolean
}) {
  const fillClass = moving
    ? "imperial-fill"
    : active || accent
      ? "fill-foreground"
      : "fill-muted-foreground"
  const opacityClass = active || moving ? "opacity-100" : "opacity-70 group-hover:opacity-90"

  return (
    <svg viewBox="0 0 120 18" className={cn("h-5 w-full transition-opacity duration-300", opacityClass)} role="presentation">
      {type === "yang" ? (
        <rect x="6" y="6" width="108" height="6" rx="2" className={cn("transition-all duration-500", fillClass)} />
      ) : (
        <>
          <rect x="6" y="6" width="43" height="6" rx="2" className={cn("transition-all duration-500", fillClass)} />
          <rect x="71" y="6" width="43" height="6" rx="2" className={cn("transition-all duration-500", fillClass)} />
        </>
      )}
      {moving ? (
        <rect
          x="2"
          y="2"
          width="116"
          height="14"
          rx="4"
          className="imperial-stroke fill-transparent"
          strokeWidth="1"
        />
      ) : null}
    </svg>
  )
}

function findLineSection(
  sections: HexSection[],
  hexagramType: "main" | "changed",
  line: HexLineInfo,
  hexagramName?: string,
) {
  const scoped = sections.filter(
    (section) =>
      section.hexagram_type === hexagramType &&
      (!hexagramName || section.hexagram_name === hexagramName),
  )
  const matchingLine = scoped.find(
    (section) =>
      section.section_kind === "line" &&
      section.line_key === String(line.position) &&
      (line.is_moving || hexagramType === "changed"),
  )
  if (matchingLine) {
    return matchingLine
  }
  const allMoving = line.is_moving && scoped.find((section) => section.section_kind === "line" && section.line_key === "all")
  if (allMoving) {
    return allMoving
  }
  return (
    scoped.find((section) => section.section_kind === "top" && section.visible_by_default) ||
    scoped.find((section) => section.visible_by_default) ||
    scoped[0]
  )
}

function compactSnippet(value: string | undefined, limit: number) {
  const text = (value || "").replace(/\s+/g, " ").trim()
  if (text.length <= limit) {
    return text
  }
  return `${text.slice(0, limit - 1).trim()}…`
}
