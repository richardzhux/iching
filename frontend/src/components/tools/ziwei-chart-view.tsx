"use client"

import { useId, useState } from "react"
import { ChartExportButton } from "@/components/tools/chart-export-button"
import { buildZiweiMarkdown } from "@/lib/chart-markdown"
import type { IFunctionalAstrolabe } from "iztro/lib/astro/FunctionalAstrolabe"
import type { IFunctionalHoroscope } from "iztro/lib/astro/FunctionalHoroscope"
import type { IFunctionalPalace } from "iztro/lib/astro/FunctionalPalace"

type Locale = "en" | "zh"

const PALACE_POSITIONS = [[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3], [2, 3], [1, 3], [0, 3], [0, 2], [0, 1]] as const

export type ZiweiProvenance = {
  algorithm: "default" | "zhongzhou"
  astroType: "heaven" | "earth" | "human"
  yearDivide: "normal" | "exact"
  dayBoundary: "current" | "forward"
  calendar: "solar" | "lunar"
  fixLeap: boolean
  isLeapMonth: boolean
}

function getProvenanceLabels(provenance: ZiweiProvenance, locale: Locale) {
  if (locale === "zh") {
    return {
      algorithm: provenance.algorithm === "zhongzhou" ? "中州派" : "通行法",
      astroType: provenance.astroType === "earth" ? "地盘" : provenance.astroType === "human" ? "人盘" : "天盘",
      yearDivide: provenance.yearDivide === "exact" ? "立春" : "农历正月初一",
      dayBoundary: provenance.dayBoundary === "forward" ? "晚子时换日" : "晚子时不换日",
      calendar: provenance.calendar === "lunar" ? "农历" : "公历",
      fixLeap: provenance.fixLeap ? "修正闰月" : "不修正闰月",
      leapMonth: provenance.isLeapMonth ? "闰月" : "非闰月",
      notApplicable: "不适用",
    }
  }
  return {
    algorithm: provenance.algorithm === "zhongzhou" ? "Zhongzhou" : "Standard",
    astroType: provenance.astroType === "earth" ? "Earth chart" : provenance.astroType === "human" ? "Human chart" : "Heaven chart",
    yearDivide: provenance.yearDivide === "exact" ? "Start of Spring" : "Lunar New Year",
    dayBoundary: provenance.dayBoundary === "forward" ? "Late Zi advances the day" : "Late Zi stays on the current day",
    calendar: provenance.calendar === "lunar" ? "Lunar calendar" : "Solar calendar",
    fixLeap: provenance.fixLeap ? "Adjust leap month" : "Do not adjust leap month",
    leapMonth: provenance.isLeapMonth ? "Leap month" : "Non-leap month",
    notApplicable: "Not applicable",
  }
}

function formatTransformations(horoscope: IFunctionalHoroscope, locale: Locale) {
  const labels = locale === "zh" ? ["禄", "权", "科", "忌"] : ["Prosperity", "Power", "Merit", "Obstacle"]
  return horoscope.yearly.mutagen.map((star, index) => `${labels[index]} ${star || "—"}`).join(" · ")
}

export function ZiweiChartView({ chart, horoscope, horoscopeDate, generatedAt, locale, provenance, subjectName }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; horoscopeDate: string; generatedAt: string; locale: Locale; provenance: ZiweiProvenance; subjectName: string }) {
  const exportTargetId = `ziwei-export-${useId().replaceAll(":", "")}`
  const [selectedPalaceIndex, setSelectedPalaceIndex] = useState(() => chart.palaces[0]?.index ?? 0)
  const selectedPalace = chart.palaces.find((palace) => palace.index === selectedPalaceIndex) ?? chart.palaces[0]
  const provenanceLabels = getProvenanceLabels(provenance, locale)
  const markdown = buildZiweiMarkdown(chart, horoscope, subjectName, locale)
  const trustNote = locale === "zh"
    ? "确定性星盘事实；不自动生成性格、吉凶、运势或命运断语。"
    : "Deterministic chart facts; no personality, auspiciousness, forecast, or fate claim is generated."

  return (
    <section className="chart-report min-w-0 space-y-8" aria-label={locale === "zh" ? "紫微斗数星盘结果" : "Zi Wei Dou Shu chart result"}>
      <div data-export-exclude className="flex justify-end">
        <ChartExportButton targetId={exportTargetId} markdown={markdown} label={locale === "zh" ? "导出命盘" : "Export chart"} loadingLabel={locale === "zh" ? "正在生成…" : "Generating…"} errorLabel={locale === "zh" ? "命盘图片生成失败，请重试。" : "Chart image could not be generated. Try again."} safeBaseFilename={`ziwei-${horoscopeDate}`} copyLabel={locale === "zh" ? "复制 Markdown" : "Copy Markdown"} copySuccess={locale === "zh" ? "Markdown 已复制" : "Markdown copied"} copyError={locale === "zh" ? "复制失败，请改用下载。" : "Copy failed. Use the download instead."} />
      </div>

      <ZiweiIdentitySummary chart={chart} horoscope={horoscope} horoscopeDate={horoscopeDate} generatedAt={generatedAt} locale={locale} trustNote={trustNote} subjectName={subjectName} />

      <section className="chart-report-chapter border-t border-border/60 pt-6">
        <h2 className="text-xl font-semibold">{locale === "zh" ? "星盘结构" : "Chart structure"}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "以下只统计星曜落点、亮度与四化，不换算为吉凶分数。" : "Star positions, brightness, and transformations only—no fortune score."}</p>
        <div className="mt-5"><ZiweiStatistics chart={chart} horoscope={horoscope} locale={locale} /></div>
      </section>

      <section className="chart-report-chapter min-w-0 border-t border-border/60 pt-6">
        <h2 className="text-xl font-semibold">{locale === "zh" ? "十二宫星盘" : "Twelve-palace chart"}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{locale === "zh" ? "选择任一宫位查看完整星曜与亮度数据。" : "Select any palace to inspect its complete stars and brightness data."}</p>
        <div className="mt-5 max-w-full overflow-x-auto pb-2" tabIndex={0} aria-label={locale === "zh" ? "十二宫星盘，可横向滚动" : "Twelve-palace chart, horizontally scrollable"}>
          <ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive selectedPalaceIndex={selectedPalace?.index} onSelect={setSelectedPalaceIndex} />
        </div>
      </section>

      {selectedPalace ? <SelectedPalaceDetail selectedPalace={selectedPalace} locale={locale} /> : null}

      <details data-export-exclude className="border-t border-border/60 pt-5">
        <summary className="cursor-pointer text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">{locale === "zh" ? "专业排盘数据与来源" : "Professional chart data and provenance"}</summary>
        <div className="mt-4 space-y-2 text-xs leading-5 text-muted-foreground">
          <p><strong className="text-foreground">{locale === "zh" ? "排盘引擎" : "Engine"}:</strong> iztro 2.5.8 · MIT</p>
          <p><strong className="text-foreground">{locale === "zh" ? "安星算法" : "Algorithm / school"}:</strong> {provenanceLabels.algorithm}{provenance.algorithm === "zhongzhou" ? ` · ${provenanceLabels.astroType}` : ""}</p>
          <p><strong className="text-foreground">{locale === "zh" ? "规则" : "Rules"}:</strong> {provenanceLabels.calendar} · {provenanceLabels.yearDivide} · {provenanceLabels.dayBoundary}</p>
          <p><strong className="text-foreground">{locale === "zh" ? "闰月" : "Leap month"}:</strong> {provenance.calendar === "lunar" ? `${provenanceLabels.fixLeap} · ${provenanceLabels.leapMonth}` : provenanceLabels.notApplicable}</p>
          <p>{locale === "zh" ? "星曜、四化与运限为确定性排盘数据；解释层不混入排盘事实，也不自动生成预测断语。" : "Stars, transformations, and periods are deterministic chart data. Interpretation remains separate from chart facts, and no predictive prose is generated."}</p>
        </div>
      </details>

      <ZiweiExportCanvas exportTargetId={exportTargetId} chart={chart} horoscope={horoscope} horoscopeDate={horoscopeDate} generatedAt={generatedAt} locale={locale} trustNote={trustNote} subjectName={subjectName} />
    </section>
  )
}

function ZiweiExportCanvas({ exportTargetId, chart, horoscope, horoscopeDate, generatedAt, locale, trustNote, subjectName }: { exportTargetId: string; chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; horoscopeDate: string; generatedAt: string; locale: Locale; trustNote: string; subjectName: string }) {
  return (
    <div aria-hidden="true" className="chart-export-stage">
      <article id={exportTargetId} aria-hidden="true" data-chart-export-root className="chart-share-canvas chart-export-canvas">
        <ZiweiIdentitySummary chart={chart} horoscope={horoscope} horoscopeDate={horoscopeDate} generatedAt={generatedAt} locale={locale} trustNote={trustNote} subjectName={subjectName} />
        <div className="mt-8"><ZiweiStatistics chart={chart} horoscope={horoscope} locale={locale} /></div>
        <div className="mt-8">
          <ZiweiPalaceChart chart={chart} horoscope={horoscope} locale={locale} interactive={false} />
        </div>
      </article>
    </div>
  )
}

type ChartStar = { name: string; brightness?: string; mutagen?: string }

function ZiweiStatistics({ chart, horoscope, locale }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale }) {
  const allStarsByPalace = chart.palaces.map((palace) => ({ palace, stars: [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars] as ChartStar[] }))
  const majorPlacements = chart.palaces.flatMap((palace) => palace.majorStars.map((star) => `${star.name}→${palace.name}`))
  const emptyPalaces = chart.palaces.filter((palace) => palace.majorStars.length === 0)
  const brightnessCounts = new Map<string, number>()
  chart.palaces.flatMap((palace) => palace.majorStars).forEach((star) => {
    const key = star.brightness || (locale === "zh" ? "未标" : "Unmarked")
    brightnessCounts.set(key, (brightnessCounts.get(key) ?? 0) + 1)
  })
  const natalTransformations = allStarsByPalace.flatMap(({ palace, stars }) => stars.filter((star) => star.mutagen).map((star) => `${star.mutagen} ${star.name}→${palace.name}`))
  const annualTransformations = horoscope.yearly.mutagen.map((starName, index) => {
    const palace = allStarsByPalace.find((entry) => entry.stars.some((star) => star.name === starName))?.palace
    const label = locale === "zh" ? ["禄", "权", "科", "忌"][index] : ["Prosperity", "Power", "Merit", "Obstacle"][index]
    return `${label} ${starName || "—"}${palace ? `→${palace.name}` : ""}`
  })
  const auspiciousNames = new Set(locale === "zh" ? ["左辅", "右弼", "文昌", "文曲", "天魁", "天钺"] : ["officer", "helper", "scholar", "artist", "assistant", "aide"])
  const challengingNames = new Set(locale === "zh" ? ["擎羊", "陀罗", "火星", "铃星", "地空", "地劫"] : ["driven", "tangled", "impulsive", "spark", "ideologue", "fickle"])
  const importantPlacements = (names: Set<string>) => allStarsByPalace.flatMap(({ palace, stars }) => stars.filter((star) => names.has(star.name)).map((star) => `${star.name}→${palace.name}`))
  const auspiciousPlacements = importantPlacements(auspiciousNames)
  const challengingPlacements = importantPlacements(challengingNames)
  return (
    <div className="grid border-y border-border/60 md:grid-cols-2 xl:grid-cols-5 xl:divide-x xl:divide-border/50">
      <ZiweiStatisticBlock title={locale === "zh" ? "十四主星落宫" : "Major-star positions"} value={`${majorPlacements.length}`}>
        <p>{majorPlacements.join(" · ") || "—"}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "宫位星曜密度" : "Palace density"} value={`${emptyPalaces.length} ${locale === "zh" ? "空宫" : "empty"}`}>
        <p>{chart.palaces.map((palace) => `${palace.name} ${palace.majorStars.length + palace.minorStars.length + palace.adjectiveStars.length}`).join(" · ")}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "主星亮度" : "Major-star brightness"} value={`${chart.palaces.flatMap((palace) => palace.majorStars).length}`}>
        <p>{Array.from(brightnessCounts.entries()).map(([name, count]) => `${name} ${count}`).join(" · ") || "—"}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "四化落宫" : "Transformations"} value={`${natalTransformations.length} / ${annualTransformations.length}`}>
        <p><strong>{locale === "zh" ? "生年" : "Natal"}：</strong>{natalTransformations.join(" · ") || "—"}</p><p className="mt-2"><strong>{locale === "zh" ? "流年" : "Annual"}：</strong>{annualTransformations.join(" · ")}</p>
      </ZiweiStatisticBlock>
      <ZiweiStatisticBlock title={locale === "zh" ? "六吉与六煞" : "Six auspicious / challenging"} value={`${auspiciousPlacements.length} / ${challengingPlacements.length}`}>
        <p><strong>{locale === "zh" ? "六吉" : "Auspicious"}：</strong>{auspiciousPlacements.join(" · ") || "—"}</p><p className="mt-2"><strong>{locale === "zh" ? "六煞" : "Challenging"}：</strong>{challengingPlacements.join(" · ") || "—"}</p>
      </ZiweiStatisticBlock>
    </div>
  )
}

function ZiweiStatisticBlock({ title, value, children }: { title: string; value: string; children: React.ReactNode }) {
  return <section className="min-w-0 px-4 py-4"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-2 text-2xl font-semibold text-primary">{value}</p><div className="mt-3 text-xs leading-5 text-muted-foreground">{children}</div></section>
}

function ZiweiIdentitySummary({ chart, horoscope, horoscopeDate, generatedAt, locale, trustNote, subjectName }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; horoscopeDate: string; generatedAt: string; locale: Locale; trustNote: string; subjectName: string }) {
  return (
    <section className="border-b border-border/60 pb-6" aria-label={locale === "zh" ? "命盘身份摘要" : "Chart identity summary"}>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div><p className="kicker">State of I Ching · 易经决策</p><h3 className="mt-3 text-3xl font-semibold">{subjectName || (locale === "zh" ? "匿名命主 · 紫微斗数" : "Anonymous · Zi Wei")}</h3><p className="mt-2 text-sm text-muted-foreground">{chart.chineseDate}</p></div>
        <div className="text-right"><p className="text-xs text-muted-foreground">{locale === "zh" ? "五行局" : "Five-element class"}</p><p className="mt-1 text-2xl font-semibold text-primary">{chart.fiveElementsClass}</p></div>
      </header>
      <div className="mt-6 grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
        <ShareFact label={locale === "zh" ? "农历出生" : "Lunar birth date"} value={chart.lunarDate || chart.chineseDate || "—"} />
        <ShareFact label={locale === "zh" ? "出生时辰" : "Birth time"} value={`${chart.time || "—"}${chart.timeRange ? ` · ${chart.timeRange}` : ""}`} />
        <ShareFact label={locale === "zh" ? "性别" : "Gender"} value={chart.gender || "—"} />
        <ShareFact label={locale === "zh" ? "命主 / 身主" : "Soul / Body rulers"} value={`${chart.soul} / ${chart.body}`} />
        <ShareFact label={locale === "zh" ? "运限日期" : "Horoscope date"} value={`${horoscopeDate} · ${horoscope.lunarDate}`} />
        <ShareFact label={locale === "zh" ? "所选日期大限" : "Selected-date decadal period"} value={`${horoscope.decadal.name} · ${horoscope.decadal.heavenlyStem}${horoscope.decadal.earthlyBranch}`} />
        <ShareFact label={locale === "zh" ? "所选日期流年" : "Selected-date annual period"} value={`${horoscope.yearly.name} · ${horoscope.yearly.heavenlyStem}${horoscope.yearly.earthlyBranch}`} />
        <ShareFact label={locale === "zh" ? "流年四化" : "Annual four transformations"} value={formatTransformations(horoscope, locale)} />
      </div>
      <footer className="mt-6 text-xs leading-5 text-muted-foreground"><p>{locale === "zh" ? "生成于" : "Generated"}: {new Date(generatedAt).toLocaleString(locale === "zh" ? "zh-CN" : "en-US")}</p><p className="mt-1">{trustNote}</p></footer>
    </section>
  )
}

function ZiweiPalaceChart({ chart, horoscope, locale, interactive, selectedPalaceIndex, onSelect }: { chart: IFunctionalAstrolabe; horoscope: IFunctionalHoroscope; locale: Locale; interactive: boolean; selectedPalaceIndex?: number; onSelect?: (index: number) => void }) {
  return (
    <div className={`grid grid-cols-4 grid-rows-4 gap-px overflow-hidden border border-border/60 bg-border/60 ${interactive ? "min-h-[46rem] min-w-[58rem]" : "h-[760px] w-full"}`}>
      {chart.palaces.slice(0, 12).map((palace, index) => {
        const isSelected = selectedPalaceIndex === palace.index
        const isDecadal = horoscope?.decadal.index === palace.index
        const isYearly = horoscope?.yearly.index === palace.index
        if (interactive) {
          return <PalaceButton key={`${palace.name}-${palace.earthlyBranch}`} palace={palace} position={PALACE_POSITIONS[index]} locale={locale} isSelected={isSelected} isDecadal={isDecadal} isYearly={isYearly} onSelect={() => onSelect?.(palace.index)} />
        }
        return (
          <section key={`${palace.name}-${palace.earthlyBranch}`} style={{ gridColumnStart: PALACE_POSITIONS[index][0] + 1, gridRowStart: PALACE_POSITIONS[index][1] + 1 }} className="bg-surface p-3.5">
            <div className="flex items-start justify-between gap-2"><strong className="text-base">{palace.name}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-sm text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></div>
            <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-sm leading-5">{palace.majorStars.length ? palace.majorStars.map((star, starIndex) => <span key={`${star.name}-${starIndex}`} className="font-semibold text-primary">{star.name}{star.brightness ? `(${star.brightness})` : ""}{star.mutagen ? ` · ${star.mutagen}` : ""}</span>) : <span className="text-muted-foreground">{locale === "zh" ? "空宫" : "Empty palace"}</span>}</div>
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{[...palace.minorStars, ...palace.adjectiveStars].map((star) => star.name).join(" · ") || "—"}</p>
            <p className="mt-2 text-xs text-muted-foreground">{isDecadal ? `${locale === "zh" ? "大限" : "Decadal"} · ` : ""}{isYearly ? `${locale === "zh" ? "流年" : "Annual"} · ` : ""}{palace.changsheng12} · {palace.decadal.range[0]}–{palace.decadal.range[1]}</p>
          </section>
        )
      })}
      <div className="col-start-2 col-end-4 row-start-2 row-end-4 flex flex-col items-center justify-center bg-primary/[0.07] p-6 text-center">
        <p className="text-2xl font-semibold">{locale === "zh" ? "十二宫命盘" : "Twelve-palace chart"}</p>
        <p className="mt-4 text-base font-medium">{horoscope.solarDate}</p>
        <p className="mt-1 text-sm text-muted-foreground">{horoscope.lunarDate}</p>
        <p className="mt-5 text-sm text-muted-foreground">{locale === "zh" ? "宫位 · 干支 · 主星 · 四化" : "Palace · stems/branches · major stars · transformations"}</p>
      </div>
    </div>
  )
}

function PalaceButton({ palace, position, locale, isSelected, isDecadal, isYearly, onSelect }: { palace: IFunctionalPalace; position: readonly [number, number]; locale: Locale; isSelected: boolean; isDecadal: boolean; isYearly: boolean; onSelect: () => void }) {
  const palaceLabel = `${palace.name} ${palace.heavenlyStem}${palace.earthlyBranch}${isDecadal ? `, ${locale === "zh" ? "大限" : "Decadal period"}` : ""}${isYearly ? `, ${locale === "zh" ? "流年" : "Annual period"}` : ""}`
  return (
    <button
      type="button"
      style={{ gridColumnStart: position[0] + 1, gridRowStart: position[1] + 1 }}
      aria-label={palaceLabel}
      aria-pressed={isSelected}
      onClick={onSelect}
      className={`min-w-0 p-3.5 text-left transition focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${isSelected ? "bg-primary/12 shadow-[inset_0_0_0_2px_var(--primary)]" : "bg-surface hover:bg-primary/[0.055]"}`}
    >
      <span className="flex items-start justify-between gap-2"><strong className="text-base">{palace.name}{palace.isBodyPalace ? ` · ${locale === "zh" ? "身" : "Body"}` : ""}</strong><span className="text-sm text-muted-foreground">{palace.heavenlyStem}{palace.earthlyBranch}</span></span>
      <span className="mt-2 flex flex-wrap gap-1">
        {isDecadal ? <span className="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-semibold">{locale === "zh" ? "大限" : "Decadal"}</span> : null}
        {isYearly ? <span className="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5 text-[0.65rem] font-semibold">{locale === "zh" ? "流年" : "Annual"}</span> : null}
      </span>
      <span className="mt-2 flex flex-wrap gap-x-2 gap-y-1">{palace.majorStars.length ? palace.majorStars.map((star, index) => <span key={`${star.name}-${index}`} className="text-sm font-semibold text-primary">{star.name}{star.brightness ? `(${star.brightness})` : ""}{star.mutagen ? ` · ${star.mutagen}` : ""}</span>) : <span className="text-sm text-muted-foreground">{locale === "zh" ? "空宫" : "Empty palace"}</span>}</span>
      <span className="mt-2 line-clamp-2 block text-xs leading-5 text-muted-foreground">{[...palace.minorStars, ...palace.adjectiveStars].map((star) => star.name).join(" · ") || "—"}</span>
      <span className="mt-2 block text-xs text-muted-foreground">{palace.changsheng12} · {palace.decadal.range[0]}–{palace.decadal.range[1]}</span>
    </button>
  )
}

function SelectedPalaceDetail({ selectedPalace, locale }: { selectedPalace: IFunctionalPalace; locale: Locale }) {
  return (
    <section aria-labelledby="selected-palace-title" className="border-t border-border/60 pt-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{locale === "zh" ? "所选宫位" : "Selected palace"}</p><h2 id="selected-palace-title" className="mt-1 text-xl font-semibold">{selectedPalace.name}{selectedPalace.isBodyPalace ? ` · ${locale === "zh" ? "身宫" : "Body palace"}` : ""}</h2></div>
        <p className="text-sm font-semibold">{selectedPalace.heavenlyStem}{selectedPalace.earthlyBranch}</p>
      </div>
      <div className="mt-4 grid divide-y divide-border/60 md:grid-cols-3 md:divide-x md:divide-y-0">
        <StarGroup title={locale === "zh" ? "主星" : "Major stars"} stars={selectedPalace.majorStars} locale={locale} emptyLabel={locale === "zh" ? "空宫（无主星）" : "Empty palace (no major stars)"} />
        <StarGroup title={locale === "zh" ? "辅星" : "Minor stars"} stars={selectedPalace.minorStars} locale={locale} />
        <StarGroup title={locale === "zh" ? "杂耀" : "Adjective stars"} stars={selectedPalace.adjectiveStars} locale={locale} />
      </div>
      <div className="mt-2 grid gap-2 border-t border-border/60 pt-4 text-xs text-muted-foreground sm:grid-cols-2">
        <p>{locale === "zh" ? "长生" : "Changsheng"}: {selectedPalace.changsheng12}</p>
        <p>{locale === "zh" ? "大限年龄" : "Decadal ages"}: {selectedPalace.decadal.range[0]}–{selectedPalace.decadal.range[1]}</p>
      </div>
    </section>
  )
}

function StarGroup({ title, stars, locale, emptyLabel }: { title: string; stars: IFunctionalPalace["majorStars"]; locale: Locale; emptyLabel?: string }) {
  return (
    <section className="py-4 md:px-4 md:first:pl-0 md:last:pr-0">
      <h3 className="text-sm font-semibold">{title}</h3>
      {stars.length ? <ul className="mt-2 divide-y divide-border/50">{stars.map((star, index) => <li key={`${star.name}-${index}`} className="py-2 text-sm"><span className="font-medium">{star.name}</span><span className="ml-2 text-xs text-muted-foreground">{star.mutagen ? `${locale === "zh" ? "化" : "Transformation"} ${star.mutagen}` : ""}{star.mutagen && star.brightness ? " · " : ""}{star.brightness ? `${locale === "zh" ? "亮度" : "Brightness"} ${star.brightness}` : ""}</span></li>)}</ul> : <p className="mt-2 text-xs text-muted-foreground">{emptyLabel || (locale === "zh" ? "无" : "None")}</p>}
    </section>
  )
}

function ShareFact({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium">{value}</p></div>
}
