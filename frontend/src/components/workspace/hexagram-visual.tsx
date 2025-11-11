"use client"

import { ArrowRight } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { BaziPillar, HexOverview } from "@/types/api"

import type { NajiaTable } from "@/types/api"

type HexagramHeaderProps = {
  overview?: HexOverview
  najiaMeta?: NajiaTable["meta"]
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
    <span className="text-lg font-semibold text-foreground dark:text-white">
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
      <div className="text-lg font-semibold text-foreground dark:text-white">{children}</div>
    </div>
  )
}

export function HexagramHeader({
  overview,
  najiaMeta,
  baziText,
  elementsText,
  baziDetail = [],
}: HexagramHeaderProps) {
  if (!overview) {
    return null
  }

  return (
    <Card className="border-border/50 bg-white/70 shadow-glass dark:border-white/10 dark:bg-white/5">
      <CardContent className="p-5">
        <p className="text-xs uppercase tracking-[0.35rem] text-muted-foreground">卦象总览</p>
        {(baziText || elementsText || baziDetail.length) && (
          <div className="mt-3 grid gap-4 rounded-2xl border border-border/30 bg-foreground/[0.02] p-4 dark:border-white/10 dark:bg-white/5">
            {baziText && (
              <InfoRow label="起卦时间">
                <span>{baziText}</span>
              </InfoRow>
            )}
            {baziDetail.length ? (
              <InfoRow label="阴阳五行">
                <PillarInlineList detail={baziDetail} />
              </InfoRow>
            ) : (
              elementsText && (
                <InfoRow label="阴阳五行">
                  <span>{elementsText}</span>
                </InfoRow>
              )
            )}
          </div>
        )}
        <div className="mt-4 flex flex-col gap-4 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:items-center">
          <HexagramCard
            label="本卦"
            name={overview.main_hexagram?.name}
            explanation={overview.main_hexagram?.explanation}
            tag={najiaMeta?.main?.type}
          />
          {overview.changed_hexagram && (
            <>
              <div className="hidden lg:flex items-center justify-center">
                <ArrowRight className="h-7 w-7 text-amber-500" />
              </div>
              <HexagramCard
                label="变卦"
                name={overview.changed_hexagram.name}
                explanation={overview.changed_hexagram.explanation}
                tag={najiaMeta?.changed?.type}
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
  accent?: boolean
}

function HexagramCard({ label, name, explanation, tag, accent = false }: HexagramCardProps) {
  return (
    <div
      className={cn(
        "flex-1 rounded-2xl border p-4",
        accent
          ? "border-amber-400/60 bg-amber-200/20 dark:border-amber-200/40 dark:bg-amber-200/10"
          : "border-border/30 bg-foreground/[0.03] dark:border-white/10 dark:bg-white/5"
      )}
    >
      <p className="text-[0.65rem] uppercase tracking-[0.4rem] text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground dark:text-white">{name || "—"}</p>
      {tag && (
        <span className="mt-1 inline-flex rounded-full border border-amber-400/60 px-3 py-0.5 text-xs font-semibold text-amber-600 dark:border-amber-200/50 dark:text-amber-200">
          {tag}
        </span>
      )}
      {explanation && <p className="mt-1 text-sm text-muted-foreground">{explanation}</p>}
    </div>
  )
}
